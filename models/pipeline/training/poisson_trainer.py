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
from models.pipeline.training.lstm_trainer import _apply_sequence_normalization
from models.pipeline.training.lstm_trainer import _artifact_league_vocab
from models.pipeline.training.lstm_trainer import _best_epoch
from models.pipeline.training.lstm_trainer import _fit_chronological_model
from models.pipeline.training.lstm_trainer import _holdout_split
from models.pipeline.training.lstm_trainer import _keras
from models.pipeline.training.lstm_trainer import _league_branch
from models.pipeline.training.lstm_trainer import _prepare_training_data
from models.pipeline.training.lstm_trainer import _save_league_vocab_artifact
from models.pipeline.training.lstm_trainer import _scale_holdout
from models.pipeline.training.lstm_trainer import _score_validation
from models.pipeline.training.lstm_trainer import _split_meta
from models.pipeline.training.lstm_trainer import _training_league_vocab
from models.pipeline.training.lstm_trainer import _training_normalization_layer
from models.pipeline.training.lstm_trainer import _vocab_size
from models.pipeline.training.lstm_trainer import chronological_split
from models.pipeline.training.model_inputs import model_inputs
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
        config: FutureEventsRunConfig,
        normalization_layer: Any | None = None,
        league_vocab_size: int | None = None) -> Any:
    """Build dual LSTMs with two positive home/away Poisson rates.

    When ``normalization_layer`` is set, both sequences pass through
    that one layer before the LSTMs. A positive ``league_embedding_dim``
    adds a ``league_index`` input and joins its embedding with the
    branches before the hidden layer.
    """
    keras = _keras()
    home_input = keras.Input(shape=sequence_shape, name="home_sequence")
    away_input = keras.Input(shape=sequence_shape, name="away_sequence")
    static_input = keras.Input(
        shape=(static_features,), name="static_features")
    home_sequence, away_sequence = _apply_sequence_normalization(
        home_input, away_input, normalization_layer)
    home_branch = keras.layers.LSTM(
        config.lstm_units, name="home_lstm")(home_sequence)
    away_branch = keras.layers.LSTM(
        config.lstm_units, name="away_lstm")(away_sequence)
    static_branch = keras.layers.Dense(
        config.dense_units,
        activation="relu",
        name="static_dense")(static_input)
    inputs = [home_input, away_input, static_input]
    branches = [home_branch, away_branch, static_branch]
    league = _league_branch(config, league_vocab_size)
    if league is not None:
        league_input, league_vector = league
        inputs.append(league_input)
        branches.append(league_vector)
    merged = keras.layers.Concatenate()(branches)
    hidden = keras.layers.Dense(
        config.dense_units, activation="relu")(merged)
    raw_rates = keras.layers.Dense(2, name="raw_lambdas")(hidden)
    positive_rates = keras.layers.Activation(
        "softplus", name="positive_lambdas")(raw_rates)
    rates = keras.layers.Rescaling(
        scale=1.0,
        offset=POISSON_EPSILON,
        name="lambdas")(positive_rates)
    model = keras.Model(inputs=inputs, outputs=rates)
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
        holdout = _holdout_split(batch, labels, dates, config)
        train_batch, val_batch, scaler = _scale_holdout(
            holdout.train_batch, holdout.validation_batch)
        normalization_layer = _training_normalization_layer(
            config, train_batch)
        league_vocab = _training_league_vocab(config, train_batch)
        model = build_poisson_model(
            train_batch.X_home.shape[1:],
            train_batch.X_static.shape[1],
            config,
            normalization_layer,
            _vocab_size(league_vocab))
        history = _fit_chronological_model(
            model,
            train_batch,
            holdout.train_labels,
            val_batch,
            holdout.validation_labels,
            config,
            league_vocab)
        metrics, n_test = _score_validation(
            model,
            val_batch,
            holdout.validation_labels,
            _poisson_metrics,
            config,
            league_vocab)
        best_epoch = _best_epoch(history, config)
        _save_artifacts(
            config, model, scaler, metrics, best_epoch, league_vocab)
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
            scaler.transform(val_batch.X_static),
            val_batch.league_ids)
        model = artifacts.load_keras_model_artifact(config.artifact_dir)
        rates = np.asarray(model.predict(
            model_inputs(
                scaled, config, _artifact_league_vocab(config)),
            verbose=0))
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
        metrics: dict[str, float],
        best_epoch: int | None = None,
        league_vocab: list[int] | None = None) -> None:
    artifacts.save_keras_model_artifact(config.artifact_dir, model)
    artifacts.save_scaler_artifact(config.artifact_dir, scaler)
    artifacts.save_metrics(config.artifact_dir, metrics)
    _save_league_vocab_artifact(config, league_vocab)
    meta = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "task_type": config.task_type,
        "window_size": config.window_size,
        "sequence_feature_columns": config.sequence_feature_columns,
        "static_feature_columns": config.static_feature_columns,
        "output": ["lambda_home", "lambda_away"],
        "loss": "independent_poisson_nll"
    }
    meta.update(_split_meta(config, best_epoch))
    artifacts.save_meta(config.artifact_dir, meta)


def train_poisson_model(
        config: FutureEventsRunConfig) -> TrainingReport:
    """Train the future-event goals and exact-score Poisson model."""
    return PoissonTrainer().train(config)
