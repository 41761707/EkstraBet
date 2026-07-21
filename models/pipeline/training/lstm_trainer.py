"""Dual-LSTM training for future result and BTTS classifiers."""

from __future__ import annotations

from datetime import date
from typing import Any

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
        validation_size = (
            config.training_config.validation_size
            if config.training_config else 0.15)
        train_batch, val_batch, y_train, y_val = chronological_split(
            batch, labels, dates, validation_size)
        train_batch, val_batch, scaler = _scale_static(
            train_batch, val_batch)
        classes = 3 if config.task_type == "result" else 2
        model = build_dual_lstm_classifier(
            train_batch.X_home.shape[1:],
            train_batch.X_static.shape[1],
            classes,
            config)
        keras = _keras()
        model.fit(
            _model_inputs(train_batch),
            y_train,
            validation_data=(_model_inputs(val_batch), y_val),
            epochs=config.epochs,
            batch_size=config.batch_size,
            shuffle=False,
            callbacks=[keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=config.patience,
                restore_best_weights=True)],
            verbose=0)
        probabilities = np.asarray(
            model.predict(_model_inputs(val_batch), verbose=0))
        metrics = _classification_metrics(y_val, probabilities)
        _save_artifacts(config, model, scaler, metrics)
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=(
                config.sequence_feature_columns
                + config.static_feature_columns),
            n_train=len(y_train),
            n_test=len(y_val))

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
        metrics: dict[str, float]) -> None:
    artifacts.save_keras_model_artifact(config.artifact_dir, model)
    artifacts.save_scaler_artifact(config.artifact_dir, scaler)
    artifacts.save_metrics(config.artifact_dir, metrics)
    artifacts.save_meta(config.artifact_dir, {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "task_type": config.task_type,
        "window_size": config.window_size,
        "sequence_feature_columns": config.sequence_feature_columns,
        "static_feature_columns": config.static_feature_columns
    })


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
