"""One hockey prediction replaces a changed final on the next run."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from backend.repositories.model_statistics_maintenance_repository import (
    StoredFinalPick)
from backend.repositories.model_statistics_maintenance_repository import (
    delete_unsettled_bets)
from backend.services.model_statistics_maintenance_service import (
    replace_changed_finals)
from models.pipeline.core.cli import _store_hockey_team_prediction
from models.pipeline.core.cli import build_parser
from models.pipeline.core.config import PredictionWriteRow


def test_predict_hockey_has_no_stage() -> None:
    parser = build_parser()
    args = parser.parse_args(["predict-hockey", "--league-id", "45"])
    assert not hasattr(args, "stage")
    with pytest.raises(SystemExit):
        parser.parse_args([
            "predict-hockey",
            "--league-id",
            "45",
            "--stage",
            "final"])


def test_changed_family_replaces_the_final_and_the_unsettled_bet() -> None:
    stored = [
        StoredFinalPick(final_id=1, prediction_id=10, event_id=234),
        StoredFinalPick(final_id=2, prediction_id=12, event_id=236)]
    connection = MagicMock()
    with patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.fetch_stored_finals",
            return_value=stored) as fetch, patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_final_predictions",
            return_value=1) as drop_finals, patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_unsettled_bets",
            return_value=1) as drop_bets, patch(
            "backend.services.model_statistics_maintenance_service."
            "get_db_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = connection
        removed = replace_changed_finals(501, 21, [11, 12])
    assert removed == 1
    fetch.assert_called_once_with(501, 21, connection)
    drop_finals.assert_called_once_with([1], connection)
    drop_bets.assert_called_once_with(501, 21, [234], connection)
    connection.commit.assert_called_once()


def test_unsettled_bet_delete_keeps_a_settled_row() -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.rowcount = 1
    deleted = delete_unsettled_bets(501, 21, [234, 234], connection)
    sql = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "outcome IS NULL" in sql
    assert "DELETE FROM bets" in sql
    assert params == (501, 21, 234)
    assert deleted == 1
    cursor.close.assert_called_once()


def test_replace_changed_finals_leaves_a_shared_connection_open() -> None:
    connection = MagicMock()
    stored = [StoredFinalPick(final_id=1, prediction_id=10, event_id=235)]
    with patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.fetch_stored_finals",
            return_value=stored), patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_final_predictions",
            return_value=1), patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_unsettled_bets",
            return_value=1):
        removed = replace_changed_finals(501, 21, [11], connection)
    assert removed == 1
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()


def _shared_connection() -> tuple[MagicMock, MagicMock]:
    connection = MagicMock()
    manager = MagicMock()
    manager.__enter__.return_value = connection
    manager.__exit__.return_value = False
    return connection, manager


def _final_row() -> PredictionWriteRow:
    return PredictionWriteRow(
        match_id=501,
        model_id=21,
        event_id=234,
        value=60.0,
        is_final=True)


def test_store_replaces_the_old_final_before_the_insert() -> None:
    connection, manager = _shared_connection()
    order: list[str] = []

    def _lookup(*_args, **_kwargs):
        order.append("lookup")
        return {234: 11}

    def _replace(*args, **kwargs):
        order.append("replace")
        shared = kwargs.get("conn", args[-1] if args else None)
        assert shared is connection
        connection.commit.assert_not_called()
        return 1

    def _write(rows, conn=None, *, values_are_percent=False):
        order.append("write")
        assert conn is connection
        assert values_are_percent is True
        connection.commit.assert_not_called()
        return len(list(rows))

    with patch(
            "models.pipeline.core.cli.lookup_prediction_ids",
            side_effect=_lookup), patch(
            "models.pipeline.core.cli.replace_changed_finals",
            side_effect=_replace), patch(
            "models.pipeline.core.cli.write_predictions",
            side_effect=_write), patch(
            "models.pipeline.core.cli.get_db_connection",
            return_value=manager):
        written = _store_hockey_team_prediction(
            501, 21, [_final_row()], True)
    assert written == 1
    assert order == ["lookup", "replace", "write"]
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


def test_failed_write_rolls_back_the_removed_pick() -> None:
    connection, manager = _shared_connection()
    stored = [StoredFinalPick(final_id=1, prediction_id=10, event_id=235)]

    def _write(_rows, conn=None, *, values_are_percent=False):
        assert conn is connection
        assert values_are_percent is True
        raise RuntimeError("insert failed")

    with patch(
            "models.pipeline.core.cli.lookup_prediction_ids",
            return_value={234: 11}), patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.fetch_stored_finals",
            return_value=stored), patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_final_predictions",
            return_value=1) as drop_finals, patch(
            "backend.services.model_statistics_maintenance_service."
            "repo.delete_unsettled_bets",
            return_value=1) as drop_bets, patch(
            "models.pipeline.core.cli.write_predictions",
            side_effect=_write), patch(
            "models.pipeline.core.cli.get_db_connection",
            return_value=manager):
        with pytest.raises(RuntimeError, match="insert failed"):
            _store_hockey_team_prediction(
                501, 21, [_final_row()], True)
    drop_finals.assert_called_once_with([1], connection)
    drop_bets.assert_called_once_with(501, 21, [235], connection)
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
