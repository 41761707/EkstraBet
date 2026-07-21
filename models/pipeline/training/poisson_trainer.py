"""Independent-Poisson training on the shared dual-LSTM backbone."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.config import TrainingReport
from models.pipeline.core.registry import register_trainer
from models.pipeline.training.lstm_trainer import _keras
from models.pipeline.training.lstm_trainer import _model_inputs
from models.pipeline.training.lstm_trainer import _prepare_training_data
from models.pipeline.training.lstm_trainer import _scale_static
from models.pipeline.training.lstm_trainer import chronological_split
from models.pipeline.training.trainer import Trainer


POISSON_EPSILON = 1e-6


def poisson_nll(y_true: Any, lambdas: Any) -> Any:
    """Return mean independent Poisson negative log-likelihood."""
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError(
            "TensorFlow is required for Poisson training") from exc
    rates = tf.maximum(lambdas, POISSON_EPSILON)
    targets = tf.cast(y_true, rates.dtype)
    component = rates - targets * tf.math.log(rates)
    component += tf.math.lgamma(targets + 1.0)
    return tf.reduce_mean(tf.reduce_sum(component, axis=-1))


def build_poisson_model(
        sequence_shape: tuple[int, int],
        static_features: int,
        config: FutureEventsRunConfig) -> Any:
    """Build dual LSTMs with two positive home/away Poisson rates."""
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
    raw_rates = keras.layers.Dense(2, name="raw_lambdas")(hidden)
    positive_rates = keras.layers.Activation(
        "softplus", name="positive_lambdas")(raw_rates)
    rates = keras.layers.Rescaling(
        scale=1.0,
        offset=POISSON_EPSILON,
        name="lambdas")(positive_rates)
    model = keras.Model(
        inputs=[home_input, away_input, static_input],
        outputs=rates)
    model.compile(
        optimizer=keras.optimizers.Adam(config.learning_rate),
        loss=poisson_nll)
    return model


def _poisson_metrics(
        targets: np.ndarray,
        rates: np.ndarray) -> dict[str, float]:
    safe_rates = np.maximum(rates, POISSON_EPSILON)
    log_factorial = np.vectorize(
        lambda value: float(math.lgamma(value + 1.0)))(targets)
    nll = safe_rates - targets * np.log(safe_rates) + log_factorial
    return {
        "poisson_nll": float(np.mean(np.sum(nll, axis=1))),
        "home_goals_mae": float(np.mean(
            np.abs(targets[:, 0] - rates[:, 0]))),
        "away_goals_mae": float(np.mean(
            np.abs(targets[:, 1] - rates[:, 1])))
    }


@register_trainer("PoissonTrainer")
class PoissonTrainer(Trainer):
    """Train independent home/away Poisson rates chronologically."""

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: FutureEventsRunConfig,
            sample_weight: pd.Series | None = None) -> Any:
        raise NotImplementedError(
            "Use train() with sequence feature-builder output")

    def train(self, config: FutureEventsRunConfig) -> TrainingReport:
        """Train a Poisson model and persist Keras/scaler metadata."""
        if config.task_type != "goals_poisson":
            raise ValueError(
                "Poisson trainer requires task_type='goals_poisson'")
        batch, labels, dates = _prepare_training_data(config)
        validation_size = (
            config.training_config.validation_size
            if config.training_config else 0.15)
        train_batch, val_batch, y_train, y_val = chronological_split(
            batch, labels, dates, validation_size)
        train_batch, val_batch, scaler = _scale_static(
            train_batch, val_batch)
        model = build_poisson_model(
            train_batch.X_home.shape[1:],
            train_batch.X_static.shape[1],
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
        rates = np.asarray(model.predict(
            _model_inputs(val_batch), verbose=0))
        metrics = _poisson_metrics(y_val, rates)
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
        """Evaluate saved Poisson rates on the newest holdout."""
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
        rates = np.asarray(
            model.predict(_model_inputs(scaled), verbose=0))
        metrics = _poisson_metrics(y_val, rates)
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=len(y_val))


def _save_artifacts(
        config: FutureEventsRunConfig,
        model: Any,
        scaler: Any,
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
        "static_feature_columns": config.static_feature_columns,
        "output": ["lambda_home", "lambda_away"],
        "loss": "independent_poisson_nll"
    })


def train_poisson_model(
        config: FutureEventsRunConfig) -> TrainingReport:
    """Train the future-event goals and exact-score Poisson model."""
    return PoissonTrainer().train(config)
