"""Dual-LSTM training for future result and BTTS classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.metrics import log_loss
from sklearn.preprocessing import StandardScaler

from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.config import TrainingReport
from models.pipeline.core.registry import get_feature_builder
from models.pipeline.core.registry import register_trainer
from models.pipeline.training.splits import split_by_dates
from models.pipeline.training.trainer import Trainer


def _keras() -> Any:
    try:
        from tensorflow import keras
    except ImportError as exc:
        raise RuntimeError(
            "TensorFlow is required for future-event training") from exc
    return keras


def build_dual_lstm_classifier(
        sequence_shape: tuple[int, int],
        static_features: int,
        classes: int,
        config: FutureEventsRunConfig) -> Any:
    """Build dual home/away LSTMs plus a dense static branch."""
    keras = _keras()
    home_input = keras.Input(shape=sequence_shape, name="home_sequence")
    away_input = keras.Input(shape=sequence_shape, name="away_sequence")
    static_input = keras.Input(
        shape=(static_features,), name="static_features")
    home_branch = keras.layers.LSTM(
        config.lstm_units, name="home_lstm")(home_input)
    away_branch = keras.layers.LSTM(
        config.lstm_units, name="away_lstm")(away_input)
    static_branch = keras.layers.Dense(
        config.dense_units,
        activation="relu",
        name="static_dense")(static_input)
    merged = keras.layers.Concatenate()([
        home_branch, away_branch, static_branch])
    hidden = keras.layers.Dense(
        config.dense_units, activation="relu")(merged)
    hidden = keras.layers.Dropout(0.2)(hidden)
    output = keras.layers.Dense(
        classes, activation="softmax", name="probabilities")(hidden)
    model = keras.Model(
        inputs=[home_input, away_input, static_input],
        outputs=output)
    model.compile(
        optimizer=keras.optimizers.Adam(config.learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"])
    return model


def _fetch_finished_matches(config: FutureEventsRunConfig) -> pd.DataFrame:
    from models.pipeline.data.match_history_repository import (
        fetch_finished_matches)

    return fetch_finished_matches(
        config.sport_id, config.date_to or date.today())


def _coerce_training_payload(
        payload: Any) -> tuple[SequenceBatch, np.ndarray, np.ndarray]:
    if isinstance(payload, dict):
        batch = payload.get("batch") or payload.get("sequence_batch")
        labels = payload.get("labels")
        dates = payload.get("dates")
    elif isinstance(payload, tuple) and len(payload) == 3:
        batch, labels, dates = payload
    else:
        raise TypeError(
            "Feature builder must return (SequenceBatch, labels, dates)")
    if not isinstance(batch, SequenceBatch):
        raise TypeError("Feature builder did not return SequenceBatch")
    label_array = np.asarray(labels)
    date_array = np.asarray(dates)
    if len(label_array) != batch.X_home.shape[0]:
        raise ValueError("Training labels and sequence batch sizes differ")
    if len(date_array) != len(label_array):
        raise ValueError("Training dates and labels sizes differ")
    return batch, label_array, date_array


def _prepare_training_data(
        config: FutureEventsRunConfig
) -> tuple[SequenceBatch, np.ndarray, np.ndarray]:
    matches = _fetch_finished_matches(config)
    if matches.empty:
        raise ValueError("No finished matches available for training")
    builder = get_feature_builder(config.feature_builder)
    method = getattr(builder, "build_training_batch", None)
    if method is None:
        method = getattr(builder, "build_training_data", None)
    if method is None:
        raise TypeError(
            f"{type(builder).__name__} must implement build_training_batch")
    return _coerce_training_payload(method(matches, config))


def chronological_split(
        batch: SequenceBatch,
        labels: np.ndarray,
        dates: np.ndarray,
        validation_size: float
) -> tuple[SequenceBatch, SequenceBatch, np.ndarray, np.ndarray]:
    """Split ordered samples without shuffling or future leakage."""
    if not 0.0 < validation_size < 1.0:
        raise ValueError("validation_size must be between zero and one")
    order = np.argsort(dates, kind="stable")
    split_at = max(1, int(len(order) * (1.0 - validation_size)))
    if split_at >= len(order):
        split_at = len(order) - 1
    train_index = order[:split_at]
    validation_index = order[split_at:]
    train_batch = _slice_batch(batch, train_index)
    validation_batch = _slice_batch(batch, validation_index)
    return (
        train_batch,
        validation_batch,
        labels[train_index],
        labels[validation_index])


def _slice_batch(batch: SequenceBatch, indexes: np.ndarray) -> SequenceBatch:
    return SequenceBatch(
        X_home=batch.X_home[indexes],
        X_away=batch.X_away[indexes],
        X_static=batch.X_static[indexes])


@dataclass(frozen=True)
class _Holdout:
    """Train rows and an optional validation holdout."""

    train_batch: SequenceBatch
    train_labels: np.ndarray
    validation_batch: SequenceBatch | None
    validation_labels: np.ndarray | None


def _uses_fixed_epochs(config: FutureEventsRunConfig) -> bool:
    """Return whether training refits for a fixed number of epochs."""
    return (
        config.split is not None
        and config.split.validation_from is None)


def _epoch_count(config: FutureEventsRunConfig) -> int:
    if not _uses_fixed_epochs(config):
        return config.epochs
    if config.fixed_epochs is None:
        raise ValueError(
            "fixed_epochs is required when validation_from is omitted")
    return config.fixed_epochs


def _holdout_split(
        batch: SequenceBatch,
        labels: np.ndarray,
        dates: np.ndarray,
        config: FutureEventsRunConfig) -> _Holdout:
    """Use date windows when ``split`` is set, otherwise a fraction."""
    if config.split is None:
        validation_size = (
            config.training_config.validation_size
            if config.training_config else 0.15)
        train_batch, val_batch, y_train, y_val = chronological_split(
            batch, labels, dates, validation_size)
        return _Holdout(train_batch, y_train, val_batch, y_val)
    if config.date_to is None:
        raise ValueError("date_to is required when split is set")
    indexes = split_by_dates(dates, config.split, config.date_to)
    validation_batch = None
    validation_labels = None
    if len(indexes.validation) > 0:
        validation_batch = _slice_batch(batch, indexes.validation)
        validation_labels = labels[indexes.validation]
    return _Holdout(
        _slice_batch(batch, indexes.train),
        labels[indexes.train],
        validation_batch,
        validation_labels)


def _scale_holdout(
        train_batch: SequenceBatch,
        validation_batch: SequenceBatch | None
) -> tuple[SequenceBatch, SequenceBatch | None, StandardScaler]:
    if validation_batch is None:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(train_batch.X_static)
        return (
            SequenceBatch(
                train_batch.X_home, train_batch.X_away, scaled),
            None,
            scaler)
    train_scaled, validation_scaled, scaler = _scale_static(
        train_batch, validation_batch)
    return train_scaled, validation_scaled, scaler


def _fit_chronological_model(
        model: Any,
        train_batch: SequenceBatch,
        train_labels: np.ndarray,
        validation_batch: SequenceBatch | None,
        validation_labels: np.ndarray | None,
        config: FutureEventsRunConfig) -> Any:
    """Fit without shuffling. Fixed epochs skip early stopping."""
    fit_kwargs: dict[str, Any] = {
        "epochs": _epoch_count(config),
        "batch_size": config.batch_size,
        "shuffle": False,
        "verbose": 0
    }
    if validation_batch is not None and validation_labels is not None:
        keras = _keras()
        fit_kwargs["validation_data"] = (
            _model_inputs(validation_batch), validation_labels)
        fit_kwargs["callbacks"] = [keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=config.patience,
            restore_best_weights=True)]
    elif validation_batch is not None or validation_labels is not None:
        raise ValueError(
            "validation batch and labels must both be present or absent")
    return model.fit(
        _model_inputs(train_batch), train_labels, **fit_kwargs)


def _score_validation(
        model: Any,
        validation_batch: SequenceBatch | None,
        validation_labels: np.ndarray | None,
        metric_fn: Callable[[np.ndarray, np.ndarray], dict[str, float]]
) -> tuple[dict[str, float], int]:
    if validation_batch is None or validation_labels is None:
        return {}, 0
    predicted = np.asarray(
        model.predict(_model_inputs(validation_batch), verbose=0))
    return metric_fn(validation_labels, predicted), len(validation_labels)


def _best_epoch(history: Any, config: FutureEventsRunConfig) -> int:
    """Return the 1-based epoch whose weights are kept."""
    if _uses_fixed_epochs(config):
        return _epoch_count(config)
    losses = np.asarray(history.history["val_loss"])
    return int(np.argmin(losses)) + 1


def _split_meta(
        config: FutureEventsRunConfig,
        best_epoch: int | None) -> dict[str, Any]:
    if config.split is None:
        return {}
    date_to = None
    if config.date_to is not None:
        date_to = config.date_to.isoformat()
    return {
        "best_epoch": best_epoch,
        "split": config.split.model_dump(mode="json"),
        "date_to": date_to
    }


def _scale_static(
        train_batch: SequenceBatch,
        validation_batch: SequenceBatch
) -> tuple[SequenceBatch, SequenceBatch, StandardScaler]:
    scaler = StandardScaler()
    train_static = scaler.fit_transform(train_batch.X_static)
    validation_static = scaler.transform(validation_batch.X_static)
    return (
        SequenceBatch(
            train_batch.X_home, train_batch.X_away, train_static),
        SequenceBatch(
            validation_batch.X_home,
            validation_batch.X_away,
            validation_static),
        scaler)


def _model_inputs(batch: SequenceBatch) -> list[np.ndarray]:
    return [batch.X_home, batch.X_away, batch.X_static]


def _classification_metrics(
        labels: np.ndarray,
        probabilities: np.ndarray) -> dict[str, float]:
    predictions = np.argmax(probabilities, axis=1)
    classes = list(range(probabilities.shape[1]))
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "log_loss": float(log_loss(labels, probabilities, labels=classes))
    }


@register_trainer("LstmTrainer")
class LstmTrainer(Trainer):
    """Train and evaluate dual-LSTM future-event classifiers."""

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: FutureEventsRunConfig,
            sample_weight: pd.Series | None = None) -> Any:
        raise NotImplementedError(
            "Use train() with sequence feature-builder output")

    def train(self, config: FutureEventsRunConfig) -> TrainingReport:
        """Train with a chronological holdout and persist Keras artifacts."""
        batch, labels, dates = _prepare_training_data(config)
        holdout = _holdout_split(batch, labels, dates, config)
        train_batch, val_batch, scaler = _scale_holdout(
            holdout.train_batch, holdout.validation_batch)
        classes = 3 if config.task_type == "result" else 2
        model = build_dual_lstm_classifier(
            train_batch.X_home.shape[1:],
            train_batch.X_static.shape[1],
            classes,
            config)
        history = _fit_chronological_model(
            model,
            train_batch,
            holdout.train_labels,
            val_batch,
            holdout.validation_labels,
            config)
        metrics, n_test = _score_validation(
            model,
            val_batch,
            holdout.validation_labels,
            _classification_metrics)
        best_epoch = _best_epoch(history, config)
        _save_artifacts(config, model, scaler, metrics, best_epoch)
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=(
                config.sequence_feature_columns
                + config.static_feature_columns),
            n_train=len(holdout.train_labels),
            n_test=n_test)

    def evaluate(self, config: FutureEventsRunConfig) -> EvaluationReport:
        """Evaluate a persisted classifier on the latest chronological slice."""
        batch, labels, dates = _prepare_training_data(config)
        validation_size = (
            config.training_config.validation_size
            if config.training_config else 0.15)
        _, val_batch, _, y_val = chronological_split(
            batch, labels, dates, validation_size)
        scaler = artifacts.load_scaler_artifact(
            config.artifact_dir, required=True)
        scaled = SequenceBatch(
            val_batch.X_home,
            val_batch.X_away,
            scaler.transform(val_batch.X_static))
        model = artifacts.load_keras_model_artifact(config.artifact_dir)
        probabilities = np.asarray(
            model.predict(_model_inputs(scaled), verbose=0))
        metrics = _classification_metrics(y_val, probabilities)
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=len(y_val))


def _save_artifacts(
        config: FutureEventsRunConfig,
        model: Any,
        scaler: StandardScaler,
        metrics: dict[str, float],
        best_epoch: int | None = None) -> None:
    artifacts.save_keras_model_artifact(config.artifact_dir, model)
    artifacts.save_scaler_artifact(config.artifact_dir, scaler)
    artifacts.save_metrics(config.artifact_dir, metrics)
    meta = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "task_type": config.task_type,
        "window_size": config.window_size,
        "sequence_feature_columns": config.sequence_feature_columns,
        "static_feature_columns": config.static_feature_columns
    }
    meta.update(_split_meta(config, best_epoch))
    artifacts.save_meta(config.artifact_dir, meta)


def train_result_model(config: FutureEventsRunConfig) -> TrainingReport:
    """Train the dedicated three-class result model."""
    if config.task_type != "result":
        raise ValueError("Result trainer requires task_type='result'")
    return LstmTrainer().train(config)


def train_btts_model(config: FutureEventsRunConfig) -> TrainingReport:
    """Train the dedicated two-class BTTS model."""
    if config.task_type != "btts":
        raise ValueError("BTTS trainer requires task_type='btts'")
    return LstmTrainer().train(config)
