"""Assemble neural-net inputs for future-event models."""

from __future__ import annotations

from typing import Any

import numpy as np

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch


def model_inputs(
        batch: SequenceBatch,
        config: FutureEventsRunConfig,
        league_vocab: list[int] | None) -> list[np.ndarray]:
    """Return home, away and static arrays, plus a league index.

    The league index is appended only when ``league_embedding_dim``
    is positive. A missing vocabulary or league-id column is an error
    in that mode, so the embedding input cannot be dropped silently.
    """
    inputs = [batch.X_home, batch.X_away, batch.X_static]
    if config.league_embedding_dim <= 0:
        return inputs
    if league_vocab is None:
        raise ValueError(
            "league_vocab is required when league_embedding_dim > 0")
    if batch.league_ids is None:
        raise ValueError(
            "league_ids is required when league_embedding_dim > 0")
    inputs.append(league_indexes(batch.league_ids, league_vocab))
    return inputs


def build_league_vocab(league_ids: np.ndarray) -> list[int]:
    """Return sorted unique league ids from a training window."""
    unique = np.unique(np.asarray(league_ids))
    return [int(league_id) for league_id in unique]


def league_indexes(
        league_ids: np.ndarray,
        vocab: list[int]) -> np.ndarray:
    """Map league ids to 1-based indexes with shape ``(n, 1)``.

    A league missing from ``vocab`` becomes 0. The ``int32`` column
    matches the planned embedding input of shape ``(1,)``.
    """
    raw = np.asarray(league_ids).reshape(-1)
    positions: dict[int, int] = {}
    for index, league_id in enumerate(vocab, start=1):
        positions.setdefault(int(league_id), index)
    mapped = np.zeros(raw.shape[0], dtype=np.int32)
    for row, league_id in enumerate(raw):
        mapped[row] = positions.get(int(league_id), 0)
    return mapped.reshape(-1, 1)


def sequence_normalization_layer(train_sequences: np.ndarray) -> Any:
    """Fit one feature-wise normalization layer on training steps.

    ``train_sequences`` is ``concatenate([X_home, X_away])`` from the
    training window. Every timestep of both branches is one sample, so
    the two LSTMs share a single feature mean and variance. The layer
    is Keras ``Normalization``, which loads without custom objects.
    """
    sequences = np.asarray(train_sequences)
    if sequences.ndim < 2:
        raise ValueError("train_sequences must include a feature axis")
    try:
        from tensorflow import keras
    except ImportError as exc:
        raise RuntimeError(
            "TensorFlow is required for sequence normalization") from exc
    # Oś cech jest ostatnia; kroki czasu obu gałęzi wchodzą do adapt.
    samples = sequences.reshape(-1, sequences.shape[-1])
    layer = keras.layers.Normalization(
        axis=-1, name="sequence_normalization")
    layer.adapt(samples)
    return layer
