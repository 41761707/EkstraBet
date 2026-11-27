"""Tests for opt-in future-event inputs and config validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from models.pipeline.core.artifacts import load_league_vocab
from models.pipeline.core.artifacts import save_league_vocab
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.config import load_model_config
from models.pipeline.training.model_inputs import build_league_vocab
from models.pipeline.training.model_inputs import league_indexes
from models.pipeline.training.model_inputs import model_inputs
from models.pipeline.training.model_inputs import recency_sample_weights
from models.pipeline.training.model_inputs import sequence_normalization_layer

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_V2 = (
    REPO_ROOT
    / "models"
    / "configs"
    / "training"
    / "football_result_v2.json")


def _payload(**overrides: object) -> dict[str, object]:
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
    return payload


def _split_payload(**overrides: object) -> dict[str, object]:
    payload = _payload(
        date_to="2026-11-01",
        split={
            "validation_from": "2026-09-01",
            "calibration_from": "2026-10-01"
        })
    payload.update(overrides)
    return payload


def _batch(league_ids: np.ndarray | None = None) -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((3, 2, 1), dtype=np.float32),
        X_away=np.ones((3, 2, 1), dtype=np.float32),
        X_static=np.arange(6, dtype=np.float32).reshape(3, 2),
        league_ids=league_ids)


def test_v2_config_keeps_the_three_model_inputs() -> None:
    config = load_model_config(RESULT_V2)
    assert isinstance(config, FutureEventsRunConfig)
    assert config.normalize_sequences is False
    assert config.league_embedding_dim == 0
    assert config.recency_half_life_days is None
    assert config.calibration == "none"
    assert config.context_params is None
    batch = _batch()
    inputs = model_inputs(batch, config, None)
    assert inputs[0] is batch.X_home
    assert inputs[1] is batch.X_away
    assert inputs[2] is batch.X_static
    assert len(inputs) == 3


def test_model_inputs_appends_league_index_for_embedding() -> None:
    config = FutureEventsRunConfig.model_validate(
        _payload(league_embedding_dim=4))
    batch = _batch(np.array([45, 99, 1]))
    inputs = model_inputs(batch, config, [1, 7, 45])
    assert inputs[0] is batch.X_home
    assert inputs[1] is batch.X_away
    assert inputs[2] is batch.X_static
    assert inputs[3].dtype == np.int32
    assert inputs[3].shape == (3, 1)
    assert inputs[3].reshape(-1).tolist() == [3, 0, 1]


def test_model_inputs_requires_vocab_and_league_ids() -> None:
    config = FutureEventsRunConfig.model_validate(
        _payload(league_embedding_dim=4))
    with pytest.raises(ValueError, match="league_vocab"):
        model_inputs(_batch(np.array([1, 2, 3])), config, None)
    with pytest.raises(ValueError, match="league_ids"):
        model_inputs(_batch(), config, [1])


def test_build_league_vocab_returns_sorted_unique_ids() -> None:
    vocab = build_league_vocab(np.array([45, 1, 45, 7]))
    assert vocab == [1, 7, 45]


def test_league_vocab_artifact_keeps_the_given_order(
        tmp_path: Path) -> None:
    target = save_league_vocab(tmp_path, [45, 1])
    assert target.name == "league_vocab.json"
    assert load_league_vocab(tmp_path) == [45, 1]
    save_league_vocab(tmp_path, [])
    assert load_league_vocab(tmp_path) == []


def test_league_vocab_artifact_rejects_a_bad_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="league_vocab"):
        load_league_vocab(missing)
    target = save_league_vocab(tmp_path, [1])
    target.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="league_ids"):
        load_league_vocab(tmp_path)
    rejected = ["[1.5]", "[1.0]", '["45"]', "[true]", "[false]", "[null]"]
    for payload in rejected:
        target.write_text(
            '{"league_ids": ' + payload + "}", encoding="utf-8")
        with pytest.raises(ValueError, match="integers"):
            load_league_vocab(tmp_path)


def test_league_indexes_follow_the_given_vocab_order() -> None:
    indexes = league_indexes(np.array([20, 10, 30]), [20, 10])
    assert indexes.dtype == np.int32
    assert indexes.reshape(-1).tolist() == [1, 2, 0]
    empty = league_indexes(np.array([], dtype=int), [20])
    assert empty.shape == (0, 1)
    assert empty.dtype == np.int32


def test_sequence_batch_checks_league_id_length() -> None:
    home = np.zeros((2, 1, 1))
    away = np.zeros((2, 1, 1))
    static = np.zeros((2, 1))
    SequenceBatch(home, away, static, np.array([3, 4]))
    with pytest.raises(ValueError, match="league_ids length"):
        SequenceBatch(home, away, static, np.array([3]))
    with pytest.raises(ValueError, match="one-dimensional"):
        SequenceBatch(home, away, static, np.array([[3, 4]]))
    with pytest.raises(ValueError, match="numpy array"):
        SequenceBatch(home, away, static, [3, 4])  # type: ignore[arg-type]


def test_temperature_isotonic_is_limited_to_btts() -> None:
    with pytest.raises(ValidationError, match="btts"):
        FutureEventsRunConfig.model_validate(_split_payload(
            calibration="temperature_isotonic"))
    accepted = FutureEventsRunConfig.model_validate(_split_payload(
        task_type="btts",
        output_columns=["p_yes", "p_no"],
        calibration="temperature"))
    assert accepted.calibration == "temperature"
    btts = FutureEventsRunConfig.model_validate(_split_payload(
        task_type="btts",
        output_columns=["p_yes", "p_no"],
        calibration="temperature_isotonic"))
    assert btts.calibration == "temperature_isotonic"


def test_calibration_requires_a_calibration_window() -> None:
    with pytest.raises(ValidationError, match="calibration_from"):
        FutureEventsRunConfig.model_validate(
            _payload(calibration="temperature"))


def test_context_columns_require_context_params() -> None:
    with pytest.raises(ValidationError, match="context_params"):
        FutureEventsRunConfig.model_validate(_payload(
            static_feature_columns=["elo_home", "home_ctx_draw_pct"]))
    plain = FutureEventsRunConfig.model_validate(_payload(
        static_feature_columns=["elo_home", "abs_elo_diff"]))
    assert plain.context_params is None
    configured = FutureEventsRunConfig.model_validate(_payload(
        static_feature_columns=["home_ctx_draw_pct"],
        context_params={}))
    assert configured.context_params is not None
    assert configured.context_params.league_shrink_matches == 60.0
    assert configured.context_params.team_shrink_matches == 6.0
    assert configured.context_params.league_prior_days == 730
    assert configured.context_params.fatigue_days == 14


def test_sequence_normalization_adapts_to_every_training_step() -> None:
    pytest.importorskip("tensorflow")
    home = np.array([
        [[0.0, 10.0], [4.0, 30.0]],
        [[8.0, 50.0], [12.0, 70.0]]], dtype=np.float32)
    away = home + np.array([1.0, -1.0], dtype=np.float32)
    stacked = np.concatenate([home, away], axis=0)
    layer = sequence_normalization_layer(stacked)
    flat = stacked.reshape(-1, stacked.shape[-1])
    assert layer.name == "sequence_normalization"
    axis = layer.axis
    if isinstance(axis, int):
        axis = (axis,)
    assert tuple(axis) == (-1,)
    assert np.allclose(
        np.asarray(layer.mean).reshape(-1), flat.mean(axis=0))
    assert np.allclose(
        np.asarray(layer.variance).reshape(-1), flat.var(axis=0))


def test_sequence_normalization_rejects_a_vector() -> None:
    with pytest.raises(ValueError, match="feature axis"):
        sequence_normalization_layer(np.array([1.0, 2.0]))


def test_context_and_recency_bounds_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FutureEventsRunConfig.model_validate(_payload(
            context_params={"league_shrink_matches": 0}))
    with pytest.raises(ValidationError):
        FutureEventsRunConfig.model_validate(
            _payload(recency_half_life_days=0))
    with pytest.raises(ValidationError):
        FutureEventsRunConfig.model_validate(
            _payload(league_embedding_dim=-1))


def test_recency_weights_favor_the_newest_sample_and_average_one() -> None:
    dates = np.array([
        "2026-01-03",
        "2026-01-01",
        "2026-01-02"], dtype="datetime64[ns]")
    reference = np.datetime64("2026-01-03", "ns")
    weights = recency_sample_weights(dates, reference, 2)
    assert weights.shape == (3,)
    assert float(weights[0]) == pytest.approx(float(np.max(weights)))
    assert weights[0] > weights[1]
    assert weights[0] > weights[2]
    assert float(np.mean(weights)) == pytest.approx(1.0)
    age_days = (reference - dates) / np.timedelta64(1, "D")
    raw = np.power(0.5, np.asarray(age_days, dtype=np.float64) / 2.0)
    assert np.allclose(weights, raw / np.mean(raw))
    same = np.array(["2026-01-01", "2026-01-01"], dtype="datetime64[ns]")
    flat = recency_sample_weights(
        same, np.datetime64("2026-01-01", "ns"), 10)
    assert np.allclose(flat, 1.0)


def test_recency_weights_reject_unusable_dates() -> None:
    reference = np.datetime64("2026-01-01", "ns")
    column = np.array([["2026-01-01"]], dtype="datetime64[ns]")
    with pytest.raises(ValueError, match="one-dimensional"):
        recency_sample_weights(column, reference, 10)
    empty = np.array([], dtype="datetime64[ns]")
    with pytest.raises(ValueError, match="empty"):
        recency_sample_weights(empty, reference, 10)
    present = np.array(["2026-01-01"], dtype="datetime64[ns]")
    with pytest.raises(ValueError, match="half_life_days"):
        recency_sample_weights(present, reference, 0)
    missing = np.array(["NaT"], dtype="datetime64[ns]")
    with pytest.raises(ValueError, match="valid"):
        recency_sample_weights(missing, reference, 10)
