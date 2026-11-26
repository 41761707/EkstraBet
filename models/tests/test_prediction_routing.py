"""Tests for champion and challenger prediction routing."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from models.pipeline.core.config import PredictionWriteRow
from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION
from models.pipeline.core.model_roles import MODEL_STATUS_RETIRED
from models.pipeline.core.model_roles import FamilyRole
from models.pipeline.core.model_roles import ModelRoleError
from models.pipeline.core.model_roles import ModelRoles
from models.pipeline.persistence.prediction_writer import (
    persist_routed_rows,
    route_prediction_rows,
    write_shadow_predictions)


def _roles() -> ModelRoles:
    return ModelRoles(
        roles=(
            FamilyRole(10, "CHAMP", 1, MODEL_STATUS_CHAMPION),
            FamilyRole(20, "CHAL", 1, MODEL_STATUS_CHALLENGER),
            FamilyRole(30, "OLD", 1, MODEL_STATUS_RETIRED)),
        active_by_model={10: 1, 20: 0, 30: 0, 40: 1, 50: 0})


def _row(
        model_id: int,
        *,
        is_final: bool = False,
        event_id: int = 7) -> PredictionWriteRow:
    return PredictionWriteRow(
        match_id=100,
        model_id=model_id,
        event_id=event_id,
        value=0.625,
        is_final=is_final)


def _connection() -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.lastrowid = 50
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def _owned_connection() -> tuple[MagicMock, MagicMock, MagicMock]:
    connection, cursor = _connection()
    manager = MagicMock()
    manager.__enter__.return_value = connection
    manager.__exit__.return_value = False
    return manager, connection, cursor


def test_route_publishes_champion_unchanged() -> None:
    row = _row(10, is_final=True)
    routed = route_prediction_rows([row], _roles(), {7: 1})
    assert routed.published == [row]
    assert routed.published[0] is row
    assert routed.shadow == []


def test_route_shadows_challenger_and_clears_final() -> None:
    row = _row(20, is_final=True)
    routed = route_prediction_rows([row], _roles(), {7: 1})
    assert routed.published == []
    assert len(routed.shadow) == 1
    shadow = routed.shadow[0]
    assert shadow is not row
    assert shadow.is_final is False
    assert shadow.match_id == row.match_id
    assert shadow.model_id == row.model_id
    assert shadow.event_id == row.event_id
    assert shadow.value == row.value


def test_route_rejects_retired_model() -> None:
    with pytest.raises(ModelRoleError, match="Retired model"):
        route_prediction_rows([_row(30)], _roles(), {7: 1})


def test_route_publishes_active_model_without_role() -> None:
    row = _row(40, is_final=True)
    routed = route_prediction_rows([row], _roles(), {7: 1})
    assert routed.published == [row]
    assert routed.shadow == []


def test_route_rejects_inactive_model_without_role() -> None:
    with pytest.raises(ModelRoleError, match="not registered for family"):
        route_prediction_rows([_row(50)], _roles(), {7: 1})


def test_route_rejects_unknown_model_as_unregistered() -> None:
    with pytest.raises(ModelRoleError, match="not registered for family 1"):
        route_prediction_rows([_row(99)], _roles(), {7: 1})


def test_route_rejects_missing_event_family() -> None:
    with pytest.raises(ModelRoleError, match="missing for event id: 9"):
        route_prediction_rows([_row(10, event_id=9)], _roles(), {7: 1})


def test_write_shadow_predictions_upserts_percentage() -> None:
    connection, cursor = _connection()
    written = write_shadow_predictions([_row(20)], connection)
    assert written == 1
    sql, params = cursor.execute.call_args.args
    assert "INSERT INTO model_shadow_predictions" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "value = VALUES(value)" in sql
    assert params == (100, 7, 20, 62.5)
    connection.commit.assert_not_called()


def test_write_shadow_predictions_rejects_final_row() -> None:
    connection, cursor = _connection()
    with pytest.raises(ValueError, match="cannot be marked as final"):
        write_shadow_predictions([_row(20, is_final=True)], connection)
    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()


def test_write_shadow_predictions_commits_owned_connection() -> None:
    manager, connection, _cursor = _owned_connection()
    with patch(
            "models.pipeline.persistence.prediction_writer."
            "get_db_connection",
            return_value=manager):
        written = write_shadow_predictions([_row(20)])
    assert written == 1
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


def test_persist_routed_rows_uses_one_transaction() -> None:
    manager, connection, cursor = _owned_connection()
    rows = [_row(10, is_final=True), _row(20, is_final=True)]
    with patch(
            "models.pipeline.persistence.prediction_writer."
            "get_db_connection",
            return_value=manager) as connect:
        published, shadow = persist_routed_rows(rows, _roles(), {7: 1})
    assert (published, shadow) == (1, 1)
    connect.assert_called_once()
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    prediction_inserts = [
        call for call in cursor.execute.call_args_list
        if "INSERT INTO predictions " in call.args[0]]
    shadow_inserts = [
        call for call in cursor.execute.call_args_list
        if "model_shadow_predictions" in call.args[0]]
    assert len(prediction_inserts) == 1
    assert prediction_inserts[0].args[1] == (100, 7, 10, 62.5)
    assert len(shadow_inserts) == 1
    assert shadow_inserts[0].args[1] == (100, 7, 20, 62.5)
    final_inserts = [
        call for call in cursor.execute.call_args_list
        if "INSERT INTO final_predictions" in call.args[0]]
    assert len(final_inserts) == 1
    assert final_inserts[0].args[1] == (50,)


def test_persist_routed_rows_leaves_caller_connection_uncommitted() -> None:
    connection, _cursor = _connection()
    rows = [_row(10, is_final=True), _row(20)]
    published, shadow = persist_routed_rows(
        rows, _roles(), {7: 1}, connection)
    assert (published, shadow) == (1, 1)
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()


def test_persist_routed_rows_rolls_back_when_shadow_write_fails() -> None:
    manager, connection, cursor = _owned_connection()

    def execute(sql: str, _params: object = None) -> None:
        if "model_shadow_predictions" in sql:
            raise RuntimeError("shadow failed")

    cursor.execute.side_effect = execute
    rows = [_row(10, is_final=True), _row(20, is_final=True)]
    with patch(
            "models.pipeline.persistence.prediction_writer."
            "get_db_connection",
            return_value=manager):
        with pytest.raises(RuntimeError, match="shadow failed"):
            persist_routed_rows(rows, _roles(), {7: 1})
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    prediction_inserts = [
        call for call in cursor.execute.call_args_list
        if "INSERT INTO predictions " in call.args[0]]
    assert len(prediction_inserts) == 1
    assert prediction_inserts[0].args[1][2] == 10


def test_persist_does_not_write_when_routing_fails() -> None:
    manager, connection, _cursor = _owned_connection()
    with patch(
            "models.pipeline.persistence.prediction_writer."
            "get_db_connection",
            return_value=manager) as connect:
        with pytest.raises(ModelRoleError, match="Retired model"):
            persist_routed_rows([_row(30)], _roles(), {7: 1})
    connect.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()
