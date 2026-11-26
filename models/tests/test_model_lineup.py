"""Tests for the football model registry and lineup builder."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from models.pipeline.core.model_lineup import DEFAULT_REGISTRY_PATH
from models.pipeline.core.model_lineup import LineupError
from models.pipeline.core.model_lineup import build_lineup
from models.pipeline.core.model_lineup import load_model_registry
from models.pipeline.core.model_lineup import resolve_lineup
from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION
from models.pipeline.core.model_roles import MODEL_STATUS_RETIRED
from models.pipeline.core.model_roles import FamilyRole
from models.pipeline.core.model_roles import ModelRoles


REPO_ROOT = Path(__file__).resolve().parents[2]
PREDICTION_CONFIGS = REPO_ROOT / "models" / "configs" / "prediction"
RESULT_CONFIG = PREDICTION_CONFIGS / "football_result_v2.json"
BTTS_CONFIG = PREDICTION_CONFIGS / "football_btts_v2.json"
GOALS_CONFIG = PREDICTION_CONFIGS / "football_goals_poisson_v1.json"
PLAYED_BETTER_CONFIG = (
    PREDICTION_CONFIGS / "football_played_better_v1.json")


def _role(
        model_id: int,
        model_name: str,
        event_family_id: int,
        status: str,
        raw_status: str | None) -> FamilyRole:
    return FamilyRole(
        model_id=model_id,
        model_name=model_name,
        event_family_id=event_family_id,
        status=status,
        raw_status=raw_status)


def _roles(*roles: FamilyRole) -> ModelRoles:
    active = {role.model_id: 1 for role in roles}
    return ModelRoles(roles=tuple(roles), active_by_model=active)


def _named_copy(source: Path, directory: Path, model_name: str) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["model_name"] = model_name
    path = directory / f"{model_name}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_model_registry_resolves_production_configs() -> None:
    loaded = load_model_registry()
    assert loaded == {
        "FOOTBALL_RESULT_V2": RESULT_CONFIG.resolve(),
        "FOOTBALL_BTTS_V2": BTTS_CONFIG.resolve(),
        "FOOTBALL_GOALS_POISSON_V1": GOALS_CONFIG.resolve()}
    assert DEFAULT_REGISTRY_PATH.is_file()


def test_load_model_registry_rejects_missing_config(
        tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({
        "models": {
            "FOOTBALL_RESULT_V2": "models/does_not_exist.json"}}),
        encoding="utf-8")
    with pytest.raises(LineupError, match="does_not_exist"):
        load_model_registry(registry_path)


def test_build_lineup_accepts_one_champion() -> None:
    roles = _roles(_role(
        8,
        "FOOTBALL_RESULT_V2",
        10,
        MODEL_STATUS_CHAMPION,
        MODEL_STATUS_CHAMPION))
    lineup = build_lineup(roles, {"FOOTBALL_RESULT_V2": RESULT_CONFIG})
    assert len(lineup.entries) == 1
    entry = lineup.entries[0]
    assert entry.model_id == 8
    assert entry.model_name == "FOOTBALL_RESULT_V2"
    assert entry.config.model_name == "FOOTBALL_RESULT_V2"
    assert entry.config.task_type == "result"
    assert entry.family_statuses == {10: MODEL_STATUS_CHAMPION}
    assert lineup.champion_entries() == [entry]
    assert lineup.challenger_entries() == []


def test_build_lineup_keeps_challenger_beside_one_champion(
        tmp_path: Path) -> None:
    challenger_config = _named_copy(
        RESULT_CONFIG, tmp_path, "FOOTBALL_RESULT_V3")
    roles = _roles(
        _role(
            8,
            "FOOTBALL_RESULT_V2",
            10,
            MODEL_STATUS_CHAMPION,
            MODEL_STATUS_CHAMPION),
        _role(
            9,
            "FOOTBALL_RESULT_V3",
            10,
            MODEL_STATUS_CHALLENGER,
            MODEL_STATUS_CHALLENGER))
    lineup = build_lineup(roles, {
        "FOOTBALL_RESULT_V2": RESULT_CONFIG,
        "FOOTBALL_RESULT_V3": challenger_config})
    assert lineup.champion_entries()[0].model_name == "FOOTBALL_RESULT_V2"
    assert lineup.challenger_entries()[0].model_name == (
        "FOOTBALL_RESULT_V3")


def test_build_lineup_rejects_two_champions() -> None:
    roles = _roles(
        _role(
            8,
            "FOOTBALL_RESULT_V2",
            10,
            MODEL_STATUS_CHAMPION,
            MODEL_STATUS_CHAMPION),
        _role(
            9,
            "FOOTBALL_BTTS_V2",
            10,
            MODEL_STATUS_CHAMPION,
            MODEL_STATUS_CHAMPION))
    registry = {
        "FOOTBALL_RESULT_V2": RESULT_CONFIG,
        "FOOTBALL_BTTS_V2": BTTS_CONFIG}
    with pytest.raises(LineupError, match="family 10") as caught:
        build_lineup(roles, registry)
    message = str(caught.value)
    assert "FOOTBALL_RESULT_V2" in message
    assert "FOOTBALL_BTTS_V2" in message
    assert "multiple champions" in message


def test_build_lineup_rejects_family_without_champion() -> None:
    roles = _roles(_role(
        9,
        "FOOTBALL_BTTS_V2",
        11,
        MODEL_STATUS_CHALLENGER,
        MODEL_STATUS_CHALLENGER))
    with pytest.raises(LineupError, match="family 11") as caught:
        build_lineup(roles, {"FOOTBALL_BTTS_V2": BTTS_CONFIG})
    message = str(caught.value)
    assert "FOOTBALL_BTTS_V2" in message
    assert "no champion" in message


def test_build_lineup_rejects_explicit_model_outside_registry() -> None:
    roles = _roles(_role(
        1,
        "FOOTBALL_PLAYED_BETTER_V1",
        4,
        MODEL_STATUS_CHAMPION,
        MODEL_STATUS_CHAMPION))
    with pytest.raises(LineupError, match="FOOTBALL_PLAYED_BETTER_V1"):
        build_lineup(roles, {})


def test_build_lineup_skips_implicit_active_model() -> None:
    roles = _roles(
        _role(
            1,
            "FOOTBALL_PLAYED_BETTER_V1",
            4,
            MODEL_STATUS_CHAMPION,
            None),
        _role(
            8,
            "FOOTBALL_RESULT_V2",
            10,
            MODEL_STATUS_CHAMPION,
            MODEL_STATUS_CHAMPION),
        _role(
            8,
            "FOOTBALL_RESULT_V2",
            12,
            MODEL_STATUS_RETIRED,
            MODEL_STATUS_RETIRED))
    lineup = build_lineup(roles, {"FOOTBALL_RESULT_V2": RESULT_CONFIG})
    assert [entry.model_name for entry in lineup.entries] == [
        "FOOTBALL_RESULT_V2"]
    assert lineup.entries[0].family_statuses == {
        10: MODEL_STATUS_CHAMPION}


def test_build_lineup_rejects_config_model_name(
        tmp_path: Path) -> None:
    config_path = _named_copy(RESULT_CONFIG, tmp_path, "OTHER_MODEL")
    roles = _roles(_role(
        8,
        "FOOTBALL_RESULT_V2",
        10,
        MODEL_STATUS_CHAMPION,
        MODEL_STATUS_CHAMPION))
    with pytest.raises(LineupError, match="OTHER_MODEL"):
        build_lineup(roles, {"FOOTBALL_RESULT_V2": config_path})


def test_build_lineup_rejects_non_future_events_config() -> None:
    roles = _roles(_role(
        1,
        "FOOTBALL_PLAYED_BETTER_V1",
        4,
        MODEL_STATUS_CHAMPION,
        MODEL_STATUS_CHAMPION))
    registry = {"FOOTBALL_PLAYED_BETTER_V1": PLAYED_BETTER_CONFIG}
    with pytest.raises(LineupError, match="future-events"):
        build_lineup(roles, registry)


def test_resolve_lineup_uses_roles_and_registry() -> None:
    roles = _roles(_role(
        8,
        "FOOTBALL_RESULT_V2",
        10,
        MODEL_STATUS_CHAMPION,
        MODEL_STATUS_CHAMPION))
    registry = {"FOOTBALL_RESULT_V2": RESULT_CONFIG}
    registry_path = Path("registry.json")
    with patch(
            "models.pipeline.core.model_lineup.fetch_model_roles",
            return_value=roles) as fetch_roles, patch(
            "models.pipeline.core.model_lineup.load_model_registry",
            return_value=registry) as load_registry:
        lineup = resolve_lineup(1, registry_path)
    fetch_roles.assert_called_once_with(1)
    load_registry.assert_called_once_with(registry_path)
    assert lineup.entries[0].model_name == "FOOTBALL_RESULT_V2"
