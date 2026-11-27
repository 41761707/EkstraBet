"""Temperature and isotonic calibration for result and BTTS models."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from sklearn.isotonic import IsotonicRegression

from models.pipeline.core.artifacts import save_meta
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.evaluation import candidates
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
from models.pipeline.prediction.future_events_predictor import (
    LoadedFutureModels)
from models.pipeline.training import lstm_trainer
from models.pipeline.training import poisson_trainer
from models.pipeline.training.calibration import apply_calibration
from models.pipeline.training.calibration import apply_temperature
from models.pipeline.training.calibration import fit_isotonic
from models.pipeline.training.calibration import fit_temperature
from models.pipeline.training.lstm_trainer import LstmTrainer
from models.pipeline.training.poisson_trainer import PoissonTrainer


def _balanced_btts() -> tuple[np.ndarray, np.ndarray]:
    """Two bins whose rates equal the predicted P(yes)."""
    block = 500
    high = np.column_stack([
        np.full(block, 0.2),
        np.full(block, 0.8)])
    low = np.column_stack([
        np.full(block, 0.8),
        np.full(block, 0.2)])
    probabilities = np.vstack([high, low])
    labels = np.concatenate([
        np.ones(400, dtype=int),
        np.zeros(100, dtype=int),
        np.ones(100, dtype=int),
        np.zeros(400, dtype=int)])
    return probabilities, labels


def _overconfident_btts() -> tuple[np.ndarray, np.ndarray]:
    """P(yes) is 0.95 while only 70 of 100 labels are yes."""
    labels = np.array([1] * 70 + [0] * 30, dtype=int)
    p_yes = np.full(labels.shape[0], 0.95)
    probabilities = np.column_stack([1.0 - p_yes, p_yes])
    return probabilities, labels


def test_temperature_is_one_when_probabilities_match_rates() -> None:
    probabilities, labels = _balanced_btts()
    temperature = fit_temperature(probabilities, labels)
    assert temperature == pytest.approx(1.0, abs=0.05)
    restored = apply_temperature(probabilities[:2], 1.0)
    assert np.allclose(restored, probabilities[:2])


def test_temperature_rises_when_the_model_is_overconfident() -> None:
    probabilities, labels = _overconfident_btts()
    temperature = fit_temperature(probabilities, labels)
    assert temperature > 1.0
    softened = apply_temperature(probabilities[:1], temperature)
    assert softened[0, 1] < probabilities[0, 1]


def test_temperature_fit_names_a_window_missing_a_class() -> None:
    binary = np.array([[0.2, 0.8], [0.3, 0.7]])
    with pytest.raises(ValueError, match="calibration"):
        fit_temperature(binary, np.array([1, 1]))
    result = np.full((4, 3), 1.0 / 3.0)
    with pytest.raises(ValueError, match="calibration"):
        fit_temperature(result, np.array([0, 0, 1, 1]))


def test_isotonic_map_is_monotonic_and_clipped() -> None:
    p_yes = np.array([0.1, 0.4, 0.2, 0.8, 0.6])
    outcomes = np.array([0, 0, 1, 1, 1])
    model = fit_isotonic(p_yes, outcomes)
    assert isinstance(model, IsotonicRegression)
    assert model.out_of_bounds == "clip"
    grid = np.linspace(0.0, 1.0, 21)
    predicted = np.asarray(model.predict(grid), dtype=float)
    assert np.all(np.diff(predicted) >= -1e-12)


def test_apply_calibration_keeps_v2_rows_and_renormalizes_btts() -> None:
    raw = np.array([[0.2, 0.8], [0.7, 0.3]])
    unchanged = apply_calibration(raw, {}, None)
    assert np.array_equal(unchanged, raw)
    calibrator = fit_isotonic(
        np.array([0.1, 0.4, 0.8]),
        np.array([0, 0, 1]))
    adjusted = apply_calibration(
        raw,
        {"calibration": "temperature_isotonic", "temperature": 1.5},
        calibrator)
    assert adjusted.shape == raw.shape
    assert np.allclose(adjusted.sum(axis=1), 1.0)
    assert not np.allclose(adjusted, raw)


def test_apply_calibration_requires_temperature_and_calibrator() -> None:
    raw = np.array([[0.4, 0.6]])
    with pytest.raises(ValueError, match="temperature"):
        apply_calibration(raw, {"calibration": "temperature"}, None)
    with pytest.raises(ValueError, match="calibrator"):
        apply_calibration(
            raw,
            {
                "calibration": "temperature_isotonic",
                "temperature": 1.0
            },
            None)


class _History:
    def __init__(self) -> None:
        self.history = {"val_loss": [0.4, 0.2]}


class _Keras:
    class callbacks:
        class EarlyStopping:
            def __init__(self, **kwargs: object) -> None:
                del kwargs


class _ProbabilityModel:
    def __init__(self, row: np.ndarray) -> None:
        self.row = np.asarray(row, dtype=float)
        self.history = _History()

    def fit(self, inputs: object, labels: object, **kwargs: object) -> _History:
        del inputs, labels, kwargs
        return self.history

    def predict(self, inputs: list[np.ndarray], verbose: int = 0) -> np.ndarray:
        del verbose
        count = len(inputs[0])
        return np.repeat(self.row.reshape(1, -1), count, axis=0)

    def save(self, path: str) -> None:
        Path(path).write_text("ok", encoding="utf-8")


def _rows() -> tuple[SequenceBatch, np.ndarray, np.ndarray]:
    count = 10
    batch = SequenceBatch(
        X_home=np.zeros((count, 2, 1), dtype=np.float32),
        X_away=np.zeros((count, 2, 1), dtype=np.float32),
        X_static=np.arange(count, dtype=np.float32).reshape(count, 1))
    dates = np.array([
        "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04",
        "2026-02-01", "2026-02-02",
        "2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04"
    ], dtype="datetime64[ns]")
    labels = np.array([0, 0, 0, 0, 0, 1, 0, 1, 2, 0], dtype=int)
    return batch, labels, dates


def _config(artifact_dir: Path, **overrides: object) -> FutureEventsRunConfig:
    payload: dict[str, object] = {
        "model_name": "test",
        "task_type": "result",
        "artifact_dir": str(artifact_dir),
        "feature_config": {},
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "football_result",
        "output_columns": ["p_home", "p_draw", "p_away"],
        "date_to": "2026-04-01",
        "epochs": 1,
        "recency_half_life_days": 365,
        "calibration": "temperature",
        "context_params": {},
        "split": {
            "validation_from": "2026-02-01",
            "calibration_from": "2026-03-01"
        }
    }
    payload.update(overrides)
    return FutureEventsRunConfig.model_validate(payload)


def _patch_lstm(
        monkeypatch: pytest.MonkeyPatch,
        payload: tuple[SequenceBatch, np.ndarray, np.ndarray],
        model: _ProbabilityModel) -> None:
    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        lstm_trainer, "_prepare_training_data", lambda config: payload)
    monkeypatch.setattr(
        lstm_trainer,
        "build_dual_lstm_classifier",
        lambda *args, **kwargs: model)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_trainer_writes_calibration_log_loss_and_meta(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = _ProbabilityModel(np.array([0.85, 0.1, 0.05]))
    _patch_lstm(monkeypatch, _rows(), model)
    LstmTrainer().train(_config(tmp_path))
    metrics = _read_json(tmp_path / "metrics.json")
    assert metrics["calibration_log_loss_after"] <= (
        metrics["calibration_log_loss_before"] + 1e-6)
    meta = _read_json(tmp_path / "meta.json")
    assert meta["calibration"] == "temperature"
    assert meta["temperature"] > 1.0
    assert meta["normalize_sequences"] is False
    assert meta["league_embedding_dim"] == 0
    assert meta["recency_half_life_days"] == 365
    assert meta["context_params"]["fatigue_days"] == 14
    assert not (tmp_path / "calibrator.joblib").is_file()


def test_btts_trainer_saves_an_isotonic_calibrator(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, _labels, dates = _rows()
    labels = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=int)
    model = _ProbabilityModel(np.array([0.2, 0.8]))
    _patch_lstm(monkeypatch, (batch, labels, dates), model)
    LstmTrainer().train(_config(
        tmp_path,
        task_type="btts",
        labeler="football_btts",
        output_columns=["p_no", "p_yes"],
        calibration="temperature_isotonic"))
    metrics = _read_json(tmp_path / "metrics.json")
    assert "calibration_log_loss_before" in metrics
    assert "calibration_log_loss_after" in metrics
    loaded = candidates.artifacts.load_calibrator(tmp_path, required=True)
    assert isinstance(loaded, IsotonicRegression)
    meta = _read_json(tmp_path / "meta.json")
    assert meta["calibration"] == "temperature_isotonic"
    assert meta["temperature"] is not None


def test_poisson_meta_keeps_a_null_temperature(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch, _labels, dates = _rows()
    goals = np.zeros((len(dates), 2), dtype=np.float32)
    model = _ProbabilityModel(np.array([1.2, 0.8]))
    monkeypatch.setattr(poisson_trainer, "_keras", lambda: _Keras)
    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (batch, goals, dates))
    monkeypatch.setattr(
        poisson_trainer,
        "build_poisson_model",
        lambda *args, **kwargs: model)
    PoissonTrainer().train(_config(
        tmp_path,
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        calibration="none"))
    meta = _read_json(tmp_path / "meta.json")
    assert meta["calibration"] == "none"
    assert meta["temperature"] is None
    assert "calibration_log_loss_before" not in _read_json(
        tmp_path / "metrics.json")


def _matchup() -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=1,
        season_id=1,
        as_of_date=date(2026, 3, 1))


def _one_row() -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((1, 2, 1), dtype=np.float32),
        X_away=np.zeros((1, 2, 1), dtype=np.float32),
        X_static=np.zeros((1, 1), dtype=np.float32))


def test_predictor_softens_an_overconfident_result() -> None:
    raw = np.array([[0.8, 0.1, 0.1]], dtype=float)

    class _Model:
        def predict(self, inputs: object, verbose: int = 0) -> np.ndarray:
            del inputs, verbose
            return raw

    config = _config(Path("."), calibration="temperature")
    meta = {"calibration": "temperature", "temperature": 2.0}
    predictor = FutureEventsPredictor(
        result_config=config,
        models=LoadedFutureModels(
            result_model=_Model(),
            result_meta=meta),
        feature_provider=lambda _matchup, _config: _one_row())
    payload = predictor.predict_pair(_matchup())
    expected = apply_temperature(raw[0], 2.0)
    result = payload["result"]
    assert result.p_home == pytest.approx(float(expected[0]))
    assert result.p_draw == pytest.approx(float(expected[1]))
    assert result.p_away == pytest.approx(float(expected[2]))
    assert result.p_home < 0.8


class _Scaler:
    def transform(self, values: np.ndarray) -> np.ndarray:
        return values


def test_candidate_applies_the_saved_temperature(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = np.array([[0.8, 0.1, 0.1]], dtype=float)
    save_meta(tmp_path, {
        "calibration": "temperature",
        "temperature": 2.0
    })

    class _Model:
        def predict(self, inputs: object, verbose: int = 0) -> np.ndarray:
            del inputs, verbose
            return raw

    monkeypatch.setattr(
        candidates.artifacts,
        "load_keras_model_artifact",
        lambda path: _Model())
    monkeypatch.setattr(
        candidates.artifacts,
        "load_scaler_artifact",
        lambda path, required=False: _Scaler())
    batch = SequenceBatch(
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 1), dtype=np.float32))
    values = candidates._predict_rows(
        _config(tmp_path, calibration="temperature"),
        batch,
        np.array([0]),
        "v3")
    expected = apply_temperature(raw, 2.0)
    assert np.allclose(values, expected)


def test_candidate_without_calibration_keeps_network_output(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = np.array([[0.8, 0.1, 0.1]], dtype=float)
    save_meta(tmp_path, {
        "calibration": "temperature",
        "temperature": 4.0
    })

    class _Model:
        def predict(self, inputs: object, verbose: int = 0) -> np.ndarray:
            del inputs, verbose
            return raw

    monkeypatch.setattr(
        candidates.artifacts,
        "load_keras_model_artifact",
        lambda path: _Model())
    monkeypatch.setattr(
        candidates.artifacts,
        "load_scaler_artifact",
        lambda path, required=False: _Scaler())
    batch = SequenceBatch(
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 2, 1), dtype=np.float32),
        np.zeros((1, 1), dtype=np.float32))
    values = candidates._predict_rows(
        _config(tmp_path, calibration="none"),
        batch,
        np.array([0]),
        "v2")
    assert np.allclose(values, raw)


def test_candidate_requires_calibration_artifacts_before_history(
        tmp_path: Path) -> None:
    directory = tmp_path / "artifact"
    directory.mkdir()
    (directory / "model.keras").write_text("x", encoding="utf-8")
    (directory / "scaler.joblib").write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="btts"):
        candidates._require_saved_model(
            directory,
            "btts",
            _config(directory, calibration="temperature_isotonic",
                    task_type="btts",
                    labeler="football_btts",
                    output_columns=["p_no", "p_yes"]))
    with pytest.raises(FileNotFoundError, match="result"):
        candidates._require_saved_model(
            directory,
            "result",
            _config(directory, calibration="temperature"))
    save_meta(directory, {
        "calibration": "temperature",
        "temperature": 1.2
    })
    candidates._require_saved_model(
        directory,
        "result",
        _config(directory, calibration="temperature"))
