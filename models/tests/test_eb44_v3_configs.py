"""Loading checks for EB-44B control and V3 configs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import load_model_config


REPO_ROOT = Path(__file__).resolve().parents[2]
_PREDICTION = REPO_ROOT / "models" / "configs" / "prediction"
_OFFLINE_FROM = date(2025, 11, 1)
_OFFLINE_CALIBRATION = date(2026, 4, 1)
_OFFLINE_TO = date(2026, 9, 1)
_REFIT_CALIBRATION = date(2026, 9, 1)
# Dzień zapisania configu i znacznik epoki. SZP-428 podmienia oba.
_REFIT_DATE = date(2026, 11, 27)
_REFIT_EPOCHS = 1

_NEW_CONFIGS = [
    "models/configs/training/football_result_v2_control.json",
    "models/configs/training/football_btts_v2_control.json",
    "models/configs/training/football_goals_poisson_v1_control.json",
    "models/configs/training/football_result_v3.json",
    "models/configs/training/football_btts_v3.json",
    "models/configs/training/football_result_v3_refit.json",
    "models/configs/training/football_btts_v3_refit.json",
    "models/configs/prediction/football_result_v3.json",
    "models/configs/prediction/football_btts_v3.json"]

_LEAGUE_CONTEXT = [
    "league_ctx_home_goals",
    "league_ctx_away_goals",
    "league_ctx_btts_pct",
    "league_ctx_over_25_pct",
    "league_ctx_draw_pct",
    "league_ctx_season_matches"]

_TEAM_SUFFIXES = [
    "clean_sheet_pct",
    "failed_to_score_pct",
    "draw_pct",
    "matches_played",
    "is_newcomer",
    "rank_pct",
    "points_per_game",
    "matches_last_14d"]

_SEQUENCE_TAIL = [
    "opponent_elo_before",
    "clean_sheet",
    "failed_to_score"]

_V3_RELATIVES = {
    "result": [
        "models/configs/training/football_result_v3.json",
        "models/configs/training/football_result_v3_refit.json",
        "models/configs/prediction/football_result_v3.json"],
    "btts": [
        "models/configs/training/football_btts_v3.json",
        "models/configs/training/football_btts_v3_refit.json",
        "models/configs/prediction/football_btts_v3.json"]}

_CONTROL_PAIRS = [
    (
        "football_result_v2.json",
        "football_result_v2_control.json",
        "FOOTBALL_RESULT_V2_CONTROL"),
    (
        "football_btts_v2.json",
        "football_btts_v2_control.json",
        "FOOTBALL_BTTS_V2_CONTROL"),
    (
        "football_goals_poisson_v1.json",
        "football_goals_poisson_v1_control.json",
        "FOOTBALL_GOALS_POISSON_V1_CONTROL")]

_OFFLINE_V3 = [
    (
        "models/configs/training/football_result_v3.json",
        "FOOTBALL_RESULT_V3",
        "football_result_v3"),
    (
        "models/configs/training/football_btts_v3.json",
        "FOOTBALL_BTTS_V3",
        "football_btts_v3")]

_RELEASE_PAIRS = [
    (
        "models/configs/training/football_result_v3_refit.json",
        "models/configs/prediction/football_result_v3.json",
        "football_result_v3"),
    (
        "models/configs/training/football_btts_v3_refit.json",
        "models/configs/prediction/football_btts_v3.json",
        "football_btts_v3")]

_GATE_CANDIDATES = {
    "result_v2_control": (
        "control",
        ["result"],
        "models/configs/training/football_result_v2_control.json"),
    "btts_v2_control": (
        "control",
        ["btts"],
        "models/configs/training/football_btts_v2_control.json"),
    "goals_v1_control": (
        "control",
        ["over_25"],
        "models/configs/training/"
        "football_goals_poisson_v1_control.json"),
    "result_v3": (
        "challenger",
        ["result"],
        "models/configs/training/football_result_v3.json"),
    "btts_v3": (
        "challenger",
        ["btts"],
        "models/configs/training/football_btts_v3.json")}


def _load(relative: str) -> FutureEventsRunConfig:
    """Load one repo config and require a future-events model."""
    loaded = load_model_config(REPO_ROOT / relative)
    if not isinstance(loaded, FutureEventsRunConfig):
        raise AssertionError(
            f"{relative} is not a future-events config")
    return loaded


def _v3_sequence(columns: list[str]) -> list[str]:
    """Replace raw xG with the masked columns and append the new keys."""
    replaced: list[str] = []
    for name in columns:
        if name == "xg_for":
            replaced.extend([
                "xg_for_masked",
                "xg_against_masked",
                "xg_available"])
            continue
        if name == "xg_against":
            continue
        replaced.append(name)
    replaced.extend(_SEQUENCE_TAIL)
    return replaced


def _v3_static(columns: list[str]) -> list[str]:
    """Append league, team and absolute Elo features after the V2 list."""
    extra = list(_LEAGUE_CONTEXT)
    for side in ("home", "away"):
        extra.extend(
            f"{side}_ctx_{suffix}" for suffix in _TEAM_SUFFIXES)
    extra.append("abs_elo_diff")
    return [*columns, *extra]


@pytest.mark.parametrize("relative", _NEW_CONFIGS)
def test_eb44_config_loads(relative: str) -> None:
    config = _load(relative)
    assert config.model_name
    assert config.output_columns
    assert config.artifact_dir


def test_control_configs_keep_the_v2_inputs() -> None:
    for source_name, control_name, model_name in _CONTROL_PAIRS:
        source = _load(f"models/configs/training/{source_name}")
        control = _load(f"models/configs/training/{control_name}")
        folder = control_name.removesuffix(".json")
        assert control.model_name == model_name
        assert control.sequence_feature_columns == (
            source.sequence_feature_columns)
        assert control.static_feature_columns == (
            source.static_feature_columns)
        assert control.task_type == source.task_type
        assert control.trainer == source.trainer
        assert control.events == source.events
        assert control.model_version == source.model_version
        assert control.date_to == _OFFLINE_TO
        assert control.split is not None
        assert control.split.validation_from == _OFFLINE_FROM
        assert control.split.calibration_from == _OFFLINE_CALIBRATION
        assert control.calibration == "none"
        assert control.context_params is None
        assert control.normalize_sequences is False
        assert control.league_embedding_dim == 0
        assert control.recency_half_life_days is None
        assert control.fixed_epochs is None
        assert control.artifact_dir.parts[-2:] == ("eb44", folder)


def test_v3_configs_share_one_feature_list() -> None:
    sources = {
        "result": _load(
            "models/configs/training/football_result_v2.json"),
        "btts": _load(
            "models/configs/training/football_btts_v2.json")}
    for task, paths in _V3_RELATIVES.items():
        source = sources[task]
        sequence = _v3_sequence(source.sequence_feature_columns)
        static = _v3_static(source.static_feature_columns)
        calibration = (
            "temperature" if task == "result"
            else "temperature_isotonic")
        for relative in paths:
            config = _load(relative)
            assert config.sequence_feature_columns == sequence
            assert config.static_feature_columns == static
            assert "xg_for" not in config.sequence_feature_columns
            assert "xg_against" not in config.sequence_feature_columns
            assert config.model_version == "3.0.0"
            assert config.normalize_sequences is True
            assert config.league_embedding_dim == 4
            assert config.recency_half_life_days == 730
            assert config.context_params is not None
            assert config.context_params.league_shrink_matches == 60.0
            assert config.calibration == calibration


def test_offline_v3_uses_the_control_window() -> None:
    for relative, model_name, folder in _OFFLINE_V3:
        config = _load(relative)
        assert config.model_name == model_name
        assert config.date_to == _OFFLINE_TO
        assert config.split is not None
        assert config.split.validation_from == _OFFLINE_FROM
        assert config.split.calibration_from == _OFFLINE_CALIBRATION
        assert config.fixed_epochs is None
        assert config.artifact_dir.parts[-2:] == ("eb44", folder)


def test_refit_and_prediction_share_the_release_artifact() -> None:
    for training_path, prediction_path, folder in _RELEASE_PAIRS:
        trained = _load(training_path)
        predicted = _load(prediction_path)
        assert trained.model_name == predicted.model_name
        assert trained.artifact_dir == predicted.artifact_dir
        assert trained.artifact_dir.parts[-2:] == ("release", folder)
        assert predicted.training_config is None
        for config in (trained, predicted):
            assert config.split is not None
            assert config.split.validation_from is None
            assert config.split.calibration_from == _REFIT_CALIBRATION
            assert config.date_to == _REFIT_DATE
            assert config.fixed_epochs == _REFIT_EPOCHS


def test_registry_points_v3_at_prediction_configs() -> None:
    path = _PREDICTION / "football_model_registry.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    models = raw["models"]
    assert models["FOOTBALL_RESULT_V3"] == (
        "models/configs/prediction/football_result_v3.json")
    assert models["FOOTBALL_BTTS_V3"] == (
        "models/configs/prediction/football_btts_v3.json")
    assert "FOOTBALL_RESULT_V2" in models
    assert "FOOTBALL_GOALS_POISSON_V1" in models


def test_gate_spec_adds_controls_and_challengers() -> None:
    path = (
        REPO_ROOT
        / "models"
        / "configs"
        / "evaluation"
        / "eb44_offline_gate.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_label = {row["label"]: row for row in raw["candidates"]}
    for label, (role, families, config) in _GATE_CANDIDATES.items():
        row = by_label[label]
        assert row["role"] == role
        assert row["families"] == families
        assert row["config"] == config
    assert by_label["result_v2_champion"]["role"] == "champion"
    assert by_label["goals_v1_champion"]["families"] == ["over_25"]
