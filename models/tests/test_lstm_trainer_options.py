"""Tests for optional sequence normalization in the LSTM networks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.training import lstm_trainer
from models.pipeline.training import poisson_trainer
from models.pipeline.training.lstm_trainer import LstmTrainer
from models.pipeline.training.lstm_trainer import build_dual_lstm_classifier
from models.pipeline.training.model_inputs import sequence_normalization_layer
from models.pipeline.training.poisson_trainer import PoissonTrainer
from models.pipeline.training.poisson_trainer import build_poisson_model


def _config(**overrides: object) -> FutureEventsRunConfig:
    payload: dict[str, object] = {
        "model_name": "test",
        "task_type": "result",
        "artifact_dir": ".",
        "feature_config": {},
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "football_result",
        "output_columns": ["p_home", "p_draw", "p_away"]
    }
    payload.update(overrides)
    return FutureEventsRunConfig.model_validate(payload)


def _sequences() -> np.ndarray:
    home = np.array([
        [[10.0, 1.0], [30.0, 3.0]],
        [[10.0, 1.0], [30.0, 3.0]],
        [[0.0, 100.0], [0.0, 100.0]],
        [[0.0, 100.0], [0.0, 100.0]]], dtype=np.float32)
    return np.concatenate([home, home + 5.0], axis=0)


def _normalization_layers(model: Any) -> list[Any]:
    return [
        layer for layer in model.layers
        if layer.__class__.__name__ == "Normalization"]


def _lstm_reads_normalization(model: Any, name: str) -> bool:
    history = model.get_layer(name).input._keras_history
    return history.operation.__class__.__name__ == "Normalization"


def test_network_has_normalization_only_when_the_layer_is_passed() -> None:
    pytest.importorskip("tensorflow")
    shape = (2, 2)
    plain = _config()
    layer = sequence_normalization_layer(_sequences())
    classifier = build_dual_lstm_classifier(shape, 1, 3, plain)
    poisson = build_poisson_model(shape, 1, plain)
    assert _normalization_layers(classifier) == []
    assert _normalization_layers(poisson) == []
    normalized_classifier = build_dual_lstm_classifier(
        shape, 1, 3, plain, layer)
    assert len(_normalization_layers(normalized_classifier)) == 1
    assert _lstm_reads_normalization(normalized_classifier, "home_lstm")
    assert _lstm_reads_normalization(normalized_classifier, "away_lstm")
    assert len(normalized_classifier.inputs) == 3
    other = sequence_normalization_layer(_sequences())
    normalized_poisson = build_poisson_model(shape, 1, plain, other)
    assert len(_normalization_layers(normalized_poisson)) == 1
    assert _lstm_reads_normalization(normalized_poisson, "home_lstm")
    assert _lstm_reads_normalization(normalized_poisson, "away_lstm")
    assert len(normalized_poisson.inputs) == 3


def test_normalized_model_loads_without_custom_objects(
        tmp_path: Path) -> None:
    tensorflow = pytest.importorskip("tensorflow")
    model = build_dual_lstm_classifier(
        (2, 2),
        1,
        3,
        _config(),
        sequence_normalization_layer(_sequences()))
    target = tmp_path / "model.keras"
    model.save(target)
    loaded = tensorflow.keras.models.load_model(target)
    assert len(_normalization_layers(loaded)) == 1
    home = np.zeros((2, 2, 2), dtype=np.float32)
    away = np.ones((2, 2, 2), dtype=np.float32)
    static = np.zeros((2, 1), dtype=np.float32)
    before = np.asarray(model.predict(
        [home, away, static], verbose=0))
    after = np.asarray(loaded.predict(
        [home, away, static], verbose=0))
    assert np.allclose(before, after)


class _History:
    def __init__(self) -> None:
        self.history = {"val_loss": [0.2]}


class _RecordingModel:
    def __init__(self, width: int) -> None:
        self.width = width
        self.history = _History()

    def fit(self, inputs, labels, **kwargs):
        del inputs, labels, kwargs
        return self.history

    def predict(self, inputs, verbose=0):
        del verbose
        count = len(inputs[0])
        return np.full((count, self.width), 1.0 / self.width)

    def save(self, path) -> None:
        Path(path).write_text("ok", encoding="utf-8")


class _Keras:
    class callbacks:
        class EarlyStopping:
            def __init__(self, **kwargs) -> None:
                del kwargs


def _window_payload() -> tuple[SequenceBatch, np.ndarray]:
    home = np.array([
        [[10.0, 1.0], [30.0, 3.0]],
        [[10.0, 1.0], [30.0, 3.0]],
        [[0.0, 100.0], [0.0, 100.0]],
        [[0.0, 100.0], [0.0, 100.0]]], dtype=np.float32)
    away = home + 5.0
    static = np.arange(4, dtype=np.float32).reshape(4, 1)
    dates = np.array([
        "2026-01-01",
        "2026-02-01",
        "2026-06-01",
        "2026-08-01"], dtype="datetime64[ns]")
    return SequenceBatch(home, away, static), dates


def _split_config(
        artifact_dir: Path,
        **overrides: object) -> FutureEventsRunConfig:
    payload: dict[str, object] = {
        "artifact_dir": str(artifact_dir),
        "date_to": "2026-09-01",
        "epochs": 1,
        "split": {
            "validation_from": "2026-05-01",
            "calibration_from": "2026-07-01"
        }
    }
    payload.update(overrides)
    return _config(**payload)


def test_trainers_fit_normalization_on_the_training_window_only(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, dates = _window_payload()
    seen: dict[str, Any] = {}

    def _layer(sequences: np.ndarray) -> str:
        seen["sequences"] = np.array(sequences, copy=True)
        return "norm"

    def _build(*args: object, **kwargs: object) -> _RecordingModel:
        del kwargs
        seen["layer"] = args[-1]
        width = 3 if len(args) == 5 else 2
        return _RecordingModel(width)

    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        lstm_trainer, "sequence_normalization_layer", _layer)
    monkeypatch.setattr(
        lstm_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros(4, dtype=np.int64), dates))
    monkeypatch.setattr(
        lstm_trainer, "build_dual_lstm_classifier", _build)
    LstmTrainer().train(_split_config(
        tmp_path / "lstm", normalize_sequences=True))
    # Czerwiec i sierpień są poza oknem treningowym.
    expected = np.concatenate(
        [batch.X_home[:2], batch.X_away[:2]], axis=0)
    assert np.array_equal(seen["sequences"], expected)
    assert seen["layer"] == "norm"

    seen.clear()
    LstmTrainer().train(_split_config(tmp_path / "plain"))
    assert "sequences" not in seen
    assert seen["layer"] is None

    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (
            batch, np.zeros((4, 2), dtype=np.float32), dates))
    monkeypatch.setattr(poisson_trainer, "build_poisson_model", _build)
    poisson_config = _split_config(
        tmp_path / "poisson",
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        normalize_sequences=True)
    PoissonTrainer().train(poisson_config)
    assert np.array_equal(seen["sequences"], expected)
    assert seen["layer"] == "norm"
