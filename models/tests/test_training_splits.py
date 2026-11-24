"""Tests for date windows and fixed-epoch future-event training."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from models.pipeline.core.config import ChronoSplit
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.training import lstm_trainer
from models.pipeline.training import poisson_trainer
from models.pipeline.training.lstm_trainer import LstmTrainer
from models.pipeline.training.poisson_trainer import PoissonTrainer
from models.pipeline.training.splits import split_by_dates


def _config_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "model_name": "test",
        "task_type": "result",
        "artifact_dir": ".",
        "feature_config": {},
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "football_result",
        "output_columns": ["1", "X", "2"]
    }
    payload.update(overrides)
    return payload


def _config(**overrides: object) -> FutureEventsRunConfig:
    return FutureEventsRunConfig.model_validate(
        _config_payload(**overrides))


def _dates(*values: str) -> np.ndarray:
    return np.array(values, dtype="datetime64[ns]")


def test_split_by_dates_assigns_boundary_days_to_the_later_window() -> None:
    dates = _dates(
        "2026-09-01",
        "2026-08-31",
        "2026-10-01",
        "2026-09-15",
        "2026-10-20")
    indexes = split_by_dates(
        dates,
        ChronoSplit(
            validation_from=date(2026, 9, 1),
            calibration_from=date(2026, 10, 1)),
        date(2026, 11, 1))
    assert indexes.train.tolist() == [1]
    assert indexes.validation.tolist() == [0, 3]
    assert indexes.calibration.tolist() == [2, 4]


def test_split_by_dates_rejects_empty_windows() -> None:
    dates = _dates("2026-09-15", "2026-10-20")
    with pytest.raises(ValueError, match="train window"):
        split_by_dates(
            dates,
            ChronoSplit(
                validation_from=date(2026, 8, 1),
                calibration_from=date(2026, 10, 1)),
            date(2026, 11, 1))
    with pytest.raises(ValueError, match="validation window"):
        split_by_dates(
            _dates("2026-08-01", "2026-10-20"),
            ChronoSplit(
                validation_from=date(2026, 9, 1),
                calibration_from=date(2026, 10, 1)),
            date(2026, 11, 1))
    with pytest.raises(ValueError, match="calibration window"):
        split_by_dates(
            _dates("2026-08-01", "2026-09-15"),
            ChronoSplit(
                validation_from=date(2026, 9, 1),
                calibration_from=date(2026, 10, 1)),
            date(2026, 11, 1))


def test_split_by_dates_allows_empty_validation_without_boundary() -> None:
    indexes = split_by_dates(
        _dates("2026-01-15", "2026-10-01"),
        ChronoSplit(calibration_from=date(2026, 9, 1)),
        date(2026, 11, 1))
    assert indexes.train.tolist() == [0]
    assert indexes.validation.tolist() == []
    assert indexes.calibration.tolist() == [1]


def test_split_by_dates_puts_every_row_in_train_when_both_bounds_are_omitted(
        ) -> None:
    indexes = split_by_dates(
        _dates("2026-01-01", "2026-06-01"),
        ChronoSplit(),
        date(2026, 11, 1))
    assert indexes.train.tolist() == [0, 1]
    assert indexes.validation.tolist() == []
    assert indexes.calibration.tolist() == []


def test_split_by_dates_rejects_rows_on_or_after_date_to() -> None:
    with pytest.raises(ValueError, match="date_to"):
        split_by_dates(
            _dates("2026-08-01", "2026-11-01"),
            ChronoSplit(validation_from=date(2026, 9, 1)),
            date(2026, 11, 1))


def test_chrono_split_requires_date_to_and_ordered_bounds() -> None:
    with pytest.raises(ValidationError, match="date_to"):
        _config(split={"validation_from": "2026-09-01"})
    with pytest.raises(ValidationError, match="fixed_epochs"):
        _config(
            date_to="2026-11-01",
            split={"calibration_from": "2026-10-01"})
    with pytest.raises(ValidationError, match="calibration_from"):
        _config(
            date_to="2026-11-01",
            split={
                "validation_from": "2026-10-01",
                "calibration_from": "2026-09-01"
            })
    with pytest.raises(ValidationError, match="calibration_from"):
        _config(
            date_to="2026-11-01",
            split={
                "validation_from": "2026-09-01",
                "calibration_from": "2026-11-01"
            })
    with pytest.raises(ValidationError, match="greater than or equal"):
        _config(fixed_epochs=0)


def test_chrono_split_accepts_fixed_epochs_and_validation_only() -> None:
    refit = _config(
        date_to="2026-11-01",
        fixed_epochs=12,
        split={"calibration_from": "2026-09-01"})
    assert refit.split is not None
    assert refit.split.validation_from is None
    assert refit.fixed_epochs == 12
    validated = _config(
        date_to="2026-11-01",
        split={"validation_from": "2026-09-01"})
    assert validated.fixed_epochs is None
    assert validated.split is not None
    assert validated.split.calibration_from is None
    unchanged = _config()
    assert unchanged.split is None
    assert unchanged.date_to is None


class _History:
    def __init__(self, losses: list[float] | None) -> None:
        self.history: dict[str, list[float]] = {}
        if losses is not None:
            self.history["val_loss"] = losses


class _RecordingModel:
    def __init__(
            self,
            losses: list[float] | None = None,
            classes: int = 3) -> None:
        self.kwargs: dict[str, object] | None = None
        self.history = _History(losses)
        self.classes = classes

    def fit(self, inputs, labels, **kwargs):
        del inputs, labels
        self.kwargs = kwargs
        return self.history

    def predict(self, inputs, verbose=0):
        del verbose
        count = len(inputs[0])
        return np.full((count, self.classes), 1.0 / self.classes)

    def save(self, path) -> None:
        Path(path).write_text("ok", encoding="utf-8")


class _Keras:
    class callbacks:
        class EarlyStopping:
            def __init__(self, **kwargs) -> None:
                self.kwargs = kwargs


def _samples(rows: int) -> tuple[SequenceBatch, np.ndarray, np.ndarray]:
    batch = SequenceBatch(
        X_home=np.zeros((rows, 2, 1), dtype=np.float32),
        X_away=np.zeros((rows, 2, 1), dtype=np.float32),
        X_static=np.arange(rows, dtype=np.float32).reshape(rows, 1))
    labels = np.zeros(rows, dtype=np.int64)
    start = np.datetime64("2026-01-01")
    dates = start + np.arange(rows).astype("timedelta64[D]")
    return batch, labels, dates


def _patch_lstm(monkeypatch, payload, model: _RecordingModel) -> None:
    monkeypatch.setattr(
        lstm_trainer, "_prepare_training_data", lambda config: payload)
    monkeypatch.setattr(
        lstm_trainer,
        "build_dual_lstm_classifier",
        lambda *args, **kwargs: model)
    monkeypatch.setattr(lstm_trainer, "_keras", lambda: _Keras)


def _read_meta(artifact_dir: Path) -> dict[str, object]:
    return json.loads(
        (artifact_dir / "meta.json").read_text(encoding="utf-8"))


def test_train_without_split_keeps_fraction_holdout_and_meta(
        tmp_path: Path, monkeypatch) -> None:
    batch, labels, dates = _samples(10)
    model = _RecordingModel(losses=[0.4, 0.2])
    _patch_lstm(monkeypatch, (batch, labels, dates), model)
    report = LstmTrainer().train(_config(
        artifact_dir=str(tmp_path),
        training_config={"validation_size": 0.2}))
    assert report.n_train == 8
    assert report.n_test == 2
    assert model.kwargs is not None
    assert model.kwargs["epochs"] == 50
    assert model.kwargs["shuffle"] is False
    assert "validation_data" in model.kwargs
    callbacks = model.kwargs["callbacks"]
    assert isinstance(callbacks, list)
    assert callbacks[0].kwargs["monitor"] == "val_loss"
    assert callbacks[0].kwargs["restore_best_weights"] is True
    meta = _read_meta(tmp_path)
    assert "split" not in meta
    assert "best_epoch" not in meta
    assert "date_to" not in meta
    assert meta["task_type"] == "result"


def test_train_with_date_split_records_best_epoch(
        tmp_path: Path, monkeypatch) -> None:
    batch, labels, dates = _samples(10)
    model = _RecordingModel(losses=[0.4, 0.1, 0.3])
    _patch_lstm(monkeypatch, (batch, labels, dates), model)
    report = LstmTrainer().train(_config(
        artifact_dir=str(tmp_path),
        date_to="2026-01-11",
        split={"validation_from": "2026-01-08"}))
    assert report.n_train == 7
    assert report.n_test == 3
    assert model.kwargs is not None
    assert model.kwargs["epochs"] == 50
    meta = _read_meta(tmp_path)
    assert meta["best_epoch"] == 2
    assert meta["date_to"] == "2026-01-11"
    assert meta["split"] == {
        "validation_from": "2026-01-08",
        "calibration_from": None
    }


def test_poisson_trainer_reuses_lstm_keras_loader() -> None:
    assert poisson_trainer._keras is lstm_trainer._keras


def test_fixed_epochs_skips_validation_for_both_trainers(
        tmp_path: Path, monkeypatch) -> None:
    batch, labels, dates = _samples(4)
    lstm_model = _RecordingModel()
    _patch_lstm(monkeypatch, (batch, labels, dates), lstm_model)
    lstm_dir = tmp_path / "lstm"
    report = LstmTrainer().train(_config(
        artifact_dir=str(lstm_dir),
        date_to="2026-01-05",
        fixed_epochs=4,
        split={"calibration_from": "2026-01-03"}))
    assert report.n_train == 2
    assert report.n_test == 0
    assert report.metrics == {}
    assert lstm_model.kwargs is not None
    assert lstm_model.kwargs["epochs"] == 4
    assert "validation_data" not in lstm_model.kwargs
    assert "callbacks" not in lstm_model.kwargs
    assert _read_meta(lstm_dir)["best_epoch"] == 4
    poisson_model = _RecordingModel(classes=2)
    poisson_batch = SequenceBatch(
        batch.X_home, batch.X_away, batch.X_static)
    poisson_labels = np.zeros((4, 2), dtype=np.float32)
    monkeypatch.setattr(
        poisson_trainer,
        "_prepare_training_data",
        lambda config: (poisson_batch, poisson_labels, dates))
    monkeypatch.setattr(
        poisson_trainer,
        "build_poisson_model",
        lambda *args, **kwargs: poisson_model)
    poisson_dir = tmp_path / "poisson"
    poisson_report = PoissonTrainer().train(_config(
        artifact_dir=str(poisson_dir),
        task_type="goals_poisson",
        output_columns=["lambda_home", "lambda_away"],
        date_to="2026-01-05",
        fixed_epochs=6,
        split={"calibration_from": "2026-01-03"}))
    assert poisson_report.n_train == 2
    assert poisson_report.n_test == 0
    assert poisson_model.kwargs is not None
    assert poisson_model.kwargs["epochs"] == 6
    assert "validation_data" not in poisson_model.kwargs
    meta = _read_meta(poisson_dir)
    assert meta["best_epoch"] == 6
    assert meta["loss"] == "independent_poisson_nll"
