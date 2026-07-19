"""Scikit-learn trainer for tabular match-assessment models."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier)
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    log_loss)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from models.pipeline.core import artifacts
from models.pipeline.core.config import (
    EvaluationReport,
    ModelRunConfig,
    TrainingConfig,
    TrainingReport)
from models.pipeline.core.registry import (
    get_feature_builder,
    get_labeler,
    register_trainer,
    resolve_model_id,
    get_trainer)
from models.pipeline.data.match_stats_repository import fetch_training_matches
from models.pipeline.features.football_match_stats import resolve_feature_columns
from models.pipeline.labels.football_played_better import (
    CLASS_AWAY,
    CLASS_DRAW,
    CLASS_HOME)
from models.pipeline.training.trainer import Trainer

logger = logging.getLogger(__name__)

# soft target -> waga próbki jako pewność hard labela
_SOFT_WEIGHT_BY_LABEL = {
    CLASS_HOME: "home_prob",
    CLASS_DRAW: "draw_prob",
    CLASS_AWAY: "away_prob"
}


def _build_estimator(algorithm: str, random_state: int) -> Any:
    if algorithm == "RandomForestClassifier":
        return RandomForestClassifier(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced")
    return HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.08,
        max_iter=200,
        random_state=random_state)


def _build_pipeline(
        algorithm: str,
        random_state: int,
        calibration_method: str) -> Pipeline:
    base = _build_estimator(algorithm, random_state)
    calibrated = CalibratedClassifierCV(
        estimator=base,
        method=calibration_method if calibration_method in {
            "isotonic", "sigmoid"} else "isotonic",
        cv=3)
    return Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", calibrated)
    ])


def _soft_sample_weights(merged: pd.DataFrame) -> pd.Series:
    """Map soft class probabilities onto hard-label sample weights."""
    weights = pd.Series(1.0, index=merged.index, dtype=float)
    for label, column in _SOFT_WEIGHT_BY_LABEL.items():
        if column not in merged.columns:
            continue
        mask = merged["label"].astype(str) == label
        weights = weights.mask(mask, merged.loc[mask, column].astype(float))
    return weights.clip(lower=1e-6)


def _prepare_xy(
        config: ModelRunConfig
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, int]:
    raw = fetch_training_matches(config)
    feature_builder = get_feature_builder(config.feature_builder)
    labeler = get_labeler(config.labeler, config)
    features = feature_builder.build_features(raw, config.feature_config)
    labels_frame = labeler.build_labels(features)
    merged = features.merge(labels_frame, on="match_id", how="inner")
    skipped = max(len(raw) - len(merged), 0)
    feature_cols = resolve_feature_columns(
        merged.columns,
        include_goals=config.feature_config.include_goals_as_features)
    if not feature_cols:
        raise ValueError("No feature columns available after feature prep")
    x_frame = merged[feature_cols].copy()
    y_series = merged["label"].astype(str)
    # sklearn wymaga hard y; soft probs wchodzą jako sample_weight
    sample_weight = _soft_sample_weights(merged)
    return x_frame, y_series, sample_weight, merged, skipped


def _split_train_val_test(
        x_frame: pd.DataFrame,
        y_series: pd.Series,
        sample_weight: pd.Series,
        training: TrainingConfig
) -> tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame,
        pd.Series, pd.Series, pd.Series,
        pd.Series, pd.Series, pd.Series]:
    """Split into train / validation / test using config sizes."""
    stratify = y_series if y_series.nunique() > 1 else None
    x_temp, x_test, y_temp, y_test, w_temp, w_test = train_test_split(
        x_frame,
        y_series,
        sample_weight,
        test_size=training.test_size,
        random_state=training.random_state,
        stratify=stratify)

    remaining = max(1.0 - training.test_size, 1e-9)
    relative_val = min(max(training.validation_size / remaining, 0.0), 0.99)
    if relative_val <= 0.0 or len(x_temp) < 2:
        empty_x = x_temp.iloc[0:0].copy()
        empty_y = y_temp.iloc[0:0].copy()
        empty_w = w_temp.iloc[0:0].copy()
        return (
            x_temp, empty_x, x_test,
            y_temp, empty_y, y_test,
            w_temp, empty_w, w_test)

    stratify_temp = y_temp if y_temp.nunique() > 1 else None
    x_train, x_val, y_train, y_val, w_train, w_val = train_test_split(
        x_temp,
        y_temp,
        w_temp,
        test_size=relative_val,
        random_state=training.random_state,
        stratify=stratify_temp)
    return (
        x_train, x_val, x_test,
        y_train, y_val, y_test,
        w_train, w_val, w_test)


def _brier_scores_per_class(
        y_true: pd.Series,
        y_proba: np.ndarray,
        classes: list[str]) -> dict[str, float]:
    """One-vs-rest Brier score for each class probability column."""
    scores: dict[str, float] = {}
    y_str = y_true.astype(str)
    for index, class_name in enumerate(classes):
        y_binary = (y_str == class_name).astype(int)
        scores[class_name] = float(
            brier_score_loss(y_binary, y_proba[:, index]))
    return scores


def _reliability_summary(
        y_true: pd.Series,
        y_proba: np.ndarray,
        classes: list[str],
        n_bins: int = 5) -> dict[str, list[dict[str, float | int]]]:
    """Per-class reliability bins: mean predicted vs empirical rate."""
    summary: dict[str, list[dict[str, float | int]]] = {}
    y_str = y_true.astype(str)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    for index, class_name in enumerate(classes):
        y_binary = (y_str == class_name).to_numpy(dtype=float)
        probs = y_proba[:, index]
        bins: list[dict[str, float | int]] = []
        for bin_index in range(n_bins):
            low = float(edges[bin_index])
            high = float(edges[bin_index + 1])
            if bin_index == n_bins - 1:
                mask = (probs >= low) & (probs <= high)
            else:
                mask = (probs >= low) & (probs < high)
            count = int(mask.sum())
            if count == 0:
                continue
            bins.append({
                "bin_low": low,
                "bin_high": high,
                "n": count,
                "mean_predicted": float(probs[mask].mean()),
                "fraction_positive": float(y_binary[mask].mean())
            })
        summary[class_name] = bins
    return summary


def _classification_metrics(
        y_true: pd.Series,
        y_pred: np.ndarray,
        y_proba: np.ndarray,
        classes: list[str]) -> dict[str, Any]:
    report = classification_report(
        y_true,
        y_pred,
        labels=classes,
        output_dict=True,
        zero_division=0)
    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "classification_report": report
    }
    try:
        # log_loss oczekuje kolumn y_proba w porządku leksykograficznym labels
        order = sorted(range(len(classes)), key=lambda index: classes[index])
        ordered_classes = [classes[index] for index in order]
        ordered_proba = y_proba[:, order]
        metrics["log_loss"] = float(
            log_loss(y_true, ordered_proba, labels=ordered_classes))
    except ValueError:
        metrics["log_loss"] = None
    try:
        brier = _brier_scores_per_class(y_true, y_proba, classes)
        metrics["brier_score_per_class"] = brier
        metrics["brier_score_mean"] = float(np.mean(list(brier.values())))
        metrics["calibration_reliability"] = _reliability_summary(
            y_true, y_proba, classes)
    except ValueError:
        metrics["brier_score_per_class"] = None
        metrics["brier_score_mean"] = None
        metrics["calibration_reliability"] = None
    return metrics


@register_trainer("SklearnTrainer")
class SklearnTrainer(Trainer):
    """Train and evaluate scikit-learn match-assessment models."""

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: ModelRunConfig,
            sample_weight: pd.Series | None = None) -> Any:
        training = config.training_config or TrainingConfig()
        pipeline = _build_pipeline(
            training.algorithm,
            training.random_state,
            training.calibration_method)
        fit_kwargs: dict[str, Any] = {}
        if sample_weight is not None:
            fit_kwargs["model__sample_weight"] = sample_weight.to_numpy()
        pipeline.fit(features, labels, **fit_kwargs)
        return pipeline

    def train(self, config: ModelRunConfig) -> TrainingReport:
        """Train, evaluate on hold-out, and write artifacts."""
        started = datetime.now(timezone.utc)
        training = config.training_config or TrainingConfig()
        x_frame, y_series, sample_weight, _merged, skipped = _prepare_xy(config)
        if x_frame.empty:
            raise ValueError("No usable training rows after feature/label prep")

        (
            x_train, x_val, x_test,
            y_train, y_val, y_test,
            w_train, _w_val, _w_test
        ) = _split_train_val_test(x_frame, y_series, sample_weight, training)

        model = self.fit(x_train, y_train, config, sample_weight=w_train)
        y_pred = model.predict(x_test)
        y_proba = model.predict_proba(x_test)
        classes = [str(item) for item in model.classes_]
        metrics = _classification_metrics(y_test, y_pred, y_proba, classes)
        metrics["classes"] = classes
        metrics["skipped_matches"] = skipped
        if len(x_val) > 0:
            val_pred = model.predict(x_val)
            val_proba = model.predict_proba(x_val)
            metrics["validation"] = _classification_metrics(
                y_val, val_pred, val_proba, classes)
            metrics["n_validation"] = len(x_val)

        feature_columns = list(x_frame.columns)
        artifacts.ensure_artifact_dir(config.artifact_dir)
        artifacts.save_model_artifact(config.artifact_dir, model)
        artifacts.save_feature_columns(config.artifact_dir, feature_columns)
        artifacts.save_metrics(config.artifact_dir, metrics)
        artifacts.save_meta(config.artifact_dir, {
            "model_name": config.model_name,
            "model_version": config.model_version,
            "sport_id": config.sport_id,
            "task_type": config.task_type,
            "assessment_type": config.assessment_type,
            "feature_builder": config.feature_builder,
            "labeler": config.labeler,
            "trainer": config.trainer,
            "config_path": (
                str(config.config_path) if config.config_path else None),
            "training_started_at": started.isoformat(),
            "training_finished_at": datetime.now(timezone.utc).isoformat(),
            "model_id": _safe_model_id(config.model_name),
            "uses_soft_sample_weights": True
        })

        logger.info(
            "Training finished for %s: accuracy=%.4f n_train=%s n_test=%s",
            config.model_name,
            metrics["accuracy"],
            len(x_train),
            len(x_test))
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=feature_columns,
            n_train=len(x_train),
            n_test=len(x_test),
            skipped_matches=skipped)

    def evaluate(self, config: ModelRunConfig) -> EvaluationReport:
        """Evaluate a saved model on the current training extract."""
        x_frame, y_series, _weights, _merged, skipped = _prepare_xy(config)
        if x_frame.empty:
            raise ValueError(
                "No usable evaluation rows after feature/label prep")
        model = artifacts.load_model_artifact(config.artifact_dir)
        feature_columns = artifacts.load_feature_columns(config.artifact_dir)
        missing = [col for col in feature_columns if col not in x_frame.columns]
        if missing:
            raise ValueError(
                f"Missing feature columns for evaluate: {missing}")
        x_eval = x_frame[feature_columns]
        y_pred = model.predict(x_eval)
        y_proba = model.predict_proba(x_eval)
        classes = [str(item) for item in model.classes_]
        metrics = _classification_metrics(y_series, y_pred, y_proba, classes)
        metrics["skipped_matches"] = skipped
        artifacts.save_metrics(config.artifact_dir, {
            **artifacts.load_metrics(config.artifact_dir),
            "evaluation": metrics
        })
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=len(x_eval),
            skipped_matches=skipped)


def _safe_model_id(model_name: str) -> int | None:
    try:
        return resolve_model_id(model_name)
    except Exception as exc:
        logger.warning(
            "Could not resolve model_id for %s: %s", model_name, exc)
        return None


def train(config: ModelRunConfig) -> TrainingReport:
    """Module-level train entry used by CLI and tests."""
    trainer = get_trainer(config.trainer)
    return trainer.train(config)


def evaluate(config: ModelRunConfig) -> EvaluationReport:
    """Module-level evaluate entry used by CLI and tests."""
    trainer = get_trainer(config.trainer)
    return trainer.evaluate(config)
