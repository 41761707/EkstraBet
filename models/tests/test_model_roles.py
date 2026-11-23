"""Tests for model family roles and registered model lookup."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
import pytest

from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION
from models.pipeline.core.model_roles import MODEL_STATUS_RETIRED
from models.pipeline.core.model_roles import FamilyRole
from models.pipeline.core.model_roles import ModelRoleError
from models.pipeline.core.model_roles import ModelRoles
from models.pipeline.core.model_roles import effective_status
from models.pipeline.core.model_roles import fetch_event_family_ids
from models.pipeline.core.model_roles import fetch_model_roles
from models.pipeline.core.registry import RegistryError
from models.pipeline.core.registry import resolve_model_id
from models.pipeline.core.registry import resolve_registered_model_id


def _db_context() -> MagicMock:
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return context


@pytest.mark.parametrize(
    ("raw_status", "model_active", "expected"),
    [
        (None, 1, MODEL_STATUS_CHAMPION),
        (None, 0, MODEL_STATUS_RETIRED),
        (None, None, MODEL_STATUS_RETIRED),
        (MODEL_STATUS_CHAMPION, 0, MODEL_STATUS_CHAMPION),
        (MODEL_STATUS_CHALLENGER, 1, MODEL_STATUS_CHALLENGER),
        (MODEL_STATUS_RETIRED, 1, MODEL_STATUS_RETIRED)
    ])
def test_effective_status_maps_null_and_known_values(
        raw_status: str | None,
        model_active: int | None,
        expected: str) -> None:
    assert effective_status(raw_status, model_active) == expected


def test_effective_status_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="legacy"):
        effective_status("legacy", 1)


def test_status_of_returns_effective_role_or_none() -> None:
    roles = ModelRoles(
        roles=(
            FamilyRole(1, "A", 10, MODEL_STATUS_CHAMPION),
            FamilyRole(2, "B", 10, MODEL_STATUS_CHALLENGER),
            FamilyRole(1, "A", 11, MODEL_STATUS_RETIRED)),
        active_by_model={1: 1, 2: 0})
    assert roles.status_of(1, 10) == MODEL_STATUS_CHAMPION
    assert roles.status_of(2, 10) == MODEL_STATUS_CHALLENGER
    assert roles.status_of(1, 11) == MODEL_STATUS_RETIRED
    assert roles.status_of(9, 10) is None
    assert roles.champions_of(10) == [roles.roles[0]]
    assert roles.champions_of(11) == []


def test_fetch_model_roles_applies_effective_status() -> None:
    captured: dict[str, object] = {}
    frame = pd.DataFrame({
        "model_id": [1, 1, 2, 3],
        "model_name": ["RESULT", "RESULT", "BTTS", "OLD"],
        "event_family_id": [10, 11, 10, 12],
        "status": [None, "challenger", "retired", None],
        "active": [1, 1, None, 0]})

    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return frame

    with patch(
            "models.pipeline.core.model_roles.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.model_roles.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_model_roles(1)
    query = str(captured["query"])
    assert "event_model_families" in query
    assert "m.sport_id = %s" in query
    assert "active = 1" not in query
    assert captured["params"] == (1,)
    assert loaded.active_by_model == {1: 1, 2: 0, 3: 0}
    assert loaded.status_of(1, 10) == MODEL_STATUS_CHAMPION
    assert loaded.status_of(1, 11) == MODEL_STATUS_CHALLENGER
    assert loaded.status_of(2, 10) == MODEL_STATUS_RETIRED
    assert loaded.status_of(3, 12) == MODEL_STATUS_RETIRED
    assert [role.model_id for role in loaded.champions_of(10)] == [1]


def test_fetch_model_roles_rejects_unknown_status() -> None:
    frame = pd.DataFrame({
        "model_id": [1],
        "model_name": ["RESULT"],
        "event_family_id": [10],
        "status": ["legacy"],
        "active": [1]})

    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        del query, params
        return frame

    with patch(
            "models.pipeline.core.model_roles.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.model_roles.pd.read_sql",
            side_effect=_read_sql):
        with pytest.raises(ValueError, match="legacy"):
            fetch_model_roles(1)


def test_fetch_event_family_ids_returns_minimum_family() -> None:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame({
            "event_id": [10, 12],
            "event_family_id": [4, 7]})

    with patch(
            "models.pipeline.core.model_roles.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.model_roles.pd.read_sql",
            side_effect=_read_sql):
        found = fetch_event_family_ids([10, 12, 10])
    query = str(captured["query"])
    assert "MIN(event_family_id)" in query
    assert "event_family_mappings" in query
    assert captured["params"] == (10, 12)
    assert found == {10: 4, 12: 7}


def test_fetch_event_family_ids_lists_missing_ids() -> None:
    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        del query, params
        return pd.DataFrame({
            "event_id": [10],
            "event_family_id": [3]})

    with patch(
            "models.pipeline.core.model_roles.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.model_roles.pd.read_sql",
            side_effect=_read_sql):
        with pytest.raises(ModelRoleError, match="11, 12"):
            fetch_event_family_ids([10, 11, 12])


def test_fetch_event_family_ids_empty_skips_query() -> None:
    with patch(
            "models.pipeline.core.model_roles.get_db_connection") as connect:
        assert fetch_event_family_ids([]) == {}
    connect.assert_not_called()


def test_resolve_registered_model_id_ignores_active_flag() -> None:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return pd.DataFrame({"id": [15]})

    with patch(
            "models.pipeline.core.registry.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.registry.pd.read_sql",
            side_effect=_read_sql):
        model_id = resolve_registered_model_id("FOOTBALL_RESULT_V3")
    query = str(captured["query"]).lower()
    assert model_id == 15
    assert "active" not in query
    assert "where name = %s" in query
    assert captured["params"] == ("FOOTBALL_RESULT_V3",)


def test_resolve_registered_model_id_missing_model() -> None:
    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        del query, params
        return pd.DataFrame({"id": []})

    with patch(
            "models.pipeline.core.registry.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.registry.pd.read_sql",
            side_effect=_read_sql):
        with pytest.raises(RegistryError, match="FOOTBALL_MISSING"):
            resolve_registered_model_id("FOOTBALL_MISSING")


def test_resolve_model_id_still_requires_active() -> None:
    captured: dict[str, str] = {}

    def _read_sql(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        del params
        captured["query"] = query
        return pd.DataFrame({"id": [8]})

    with patch(
            "models.pipeline.core.registry.get_db_connection",
            return_value=_db_context()), patch(
            "models.pipeline.core.registry.pd.read_sql",
            side_effect=_read_sql):
        assert resolve_model_id("FOOTBALL_RESULT_V2") == 8
    assert "active = 1" in captured["query"]
