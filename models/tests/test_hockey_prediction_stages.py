"""Initial and final NHL prediction stages."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
import pytest

from backend.repositories.model_statistics_maintenance_repository import (
    StoredFinalPick)
from backend.repositories.model_statistics_maintenance_repository import (
    delete_unsettled_bets)
from backend.services.model_statistics_maintenance_service import (
    replace_changed_finals)
from models.pipeline.core.cli import _store_hockey_team_prediction
from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import main
from models.pipeline.core.config import PredictionWriteRow
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.team_features import (
    committed_goalie_state)
from models.pipeline.features.hockey.team_features import (
    projected_starter_save)
from models.pipeline.persistence.hockey_prediction_run_writer import (
    write_prediction_run)
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.prediction.hockey_player_props import _score_matches
from models.tests.test_model_runner import _hockey_ratings_model
from models.tests.test_model_runner import _hockey_upcoming
from models.tests.test_model_runner import _run_predict_hockey


def test_stage_defaults_to_initial() -> None:
    parser = build_parser()
    args = parser.parse_args(["predict-hockey", "--league-id", "45"])
    assert args.stage == "initial"


def test_final_stage_requires_match_ids(
        capsys: pytest.CaptureFixture[str]) -> None:
    hockey = main([
        "predict-hockey", "--league-id", "45", "--stage", "final"])
    props = main([
        "predict-hockey-props", "--league-id", "45", "--stage", "final"])
    assert hockey == 1
    assert props == 1
    error = capsys.readouterr().err
    assert error.count("--stage final requires --match-ids") == 2


def test_final_without_confirmed_lineup_skips_the_match(
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(
            logging.WARNING, logger="models.pipeline.core.cli"):
        code, _selected, writer = _run_predict_hockey(
            [
                "predict-hockey",
                "--league-id",
                "45",
                "--stage",
                "final",
                "--match-ids",
                "501",
                "--write-db",
                "--select-finals"],
            [501],
            _hockey_upcoming((501, 10, 20)),
            MagicMock())
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["stage"] == "final"
    assert payload["result"]["models"][0]["matches"] == []
    assert "confirmed lineup" in caplog.text
    assert "501" in caplog.text


def _recording_writers(
        stages: list[str],
        order: list[str]):
    """Capture stage snapshots and the order of the final-stage writes."""

    def _snap(
            match_id: int,
            model_id: int,
            stage: str,
            market_probs: dict[str, float],
            conn: object = None) -> None:
        order.append(f"snapshot:{stage}")
        stages.append(stage)
        assert market_probs

    def _replace(
            match_id: int,
            model_id: int,
            new_ids: list[int],
            conn: object = None) -> int:
        order.append("replace")
        assert new_ids
        return 1

    def _lookup(
            match_id: int,
            model_id: int,
            event_ids: list[int],
            conn: object = None) -> dict[int, int]:
        order.append("lookup")
        return {
            int(event_id): 1000 + int(event_id)
            for event_id in event_ids}

    def _write(rows, conn=None, *, values_are_percent=False):
        assert values_are_percent is True
        order.append("write")
        return len(list(rows))

    return _snap, _replace, _lookup, _write


def _confirmed_lineup(
        match_id: int,
        team_id: int,
        stage: str) -> ProbableLineup:
    assert stage == "final"
    return ProbableLineup(match_id=match_id, team_id=team_id, players=[])


def test_final_overwrites_predictions_and_keeps_the_initial_snapshot(
        capsys: pytest.CaptureFixture[str]) -> None:
    model = replace(
        _hockey_ratings_model(), beta_off=0.8, beta_def=0.4)
    stages: list[str] = []
    order: list[str] = []
    snap, replace_finals, lookup, write = _recording_writers(stages, order)
    code, _selected, _writer = _run_predict_hockey(
        [
            "predict-hockey",
            "--league-id",
            "45",
            "--stage",
            "initial",
            "--write-db",
            "--select-finals"],
        [501],
        _hockey_upcoming((501, 10, 20)),
        write,
        model=model,
        snapshot_writer=snap,
        finals_replacer=replace_finals,
        id_lookup=lookup)
    assert code == 0
    initial = json.loads(capsys.readouterr().out)
    initial_home = initial["result"]["models"][0]["matches"][0]["markets"][
        "ml_home"]
    ratios = {
        "home_off_ratio": 1.35,
        "away_off_ratio": 0.75,
        "home_def_ratio": 1.1,
        "away_def_ratio": 0.85}
    with patch(
            "models.pipeline.core.cli._lineup_history_if_needed",
            return_value=(object(), None)), patch(
            "models.pipeline.core.cli.ratios_for_lineups",
            return_value=ratios):
        code, _selected, _writer = _run_predict_hockey(
            [
                "predict-hockey",
                "--league-id",
                "45",
                "--stage",
                "final",
                "--match-ids",
                "501",
                "--write-db",
                "--select-finals"],
            [501],
            _hockey_upcoming((501, 10, 20)),
            write,
            model=model,
            resolver=_confirmed_lineup,
            snapshot_writer=snap,
            finals_replacer=replace_finals,
            id_lookup=lookup)
    assert code == 0
    final = json.loads(capsys.readouterr().out)
    final_home = final["result"]["models"][0]["matches"][0]["markets"][
        "ml_home"]
    assert final_home != pytest.approx(initial_home)
    assert stages == ["initial", "final"]
    assert order == [
        "write",
        "snapshot:initial",
        "lookup",
        "replace",
        "write",
        "snapshot:final"]


def test_confirmed_goalie_moves_the_ratings_model(
        capsys: pytest.CaptureFixture[str]) -> None:
    moment = datetime(2026, 10, 7, 19, 0)
    stats = _goalie_box_scores()
    home = _confirmed_net()
    away = ProbableLineup(
        match_id=501,
        team_id=20,
        players=[_skater(200)])
    model = _hockey_ratings_model()
    state = committed_goalie_state(stats)
    starter = projected_starter_save(home, state, moment, 501)
    assert starter is not None
    assert starter != pytest.approx(0.91)
    changed = derive_hockey_markets(model.score_distribution(
        10,
        20,
        home_starter_save=starter,
        away_starter_save=0.90,
        home_team_save=0.91,
        away_team_save=0.90))
    unchanged = derive_hockey_markets(model.score_distribution(
        10,
        20,
        home_starter_save=0.91,
        away_starter_save=0.90,
        home_team_save=0.91,
        away_team_save=0.90))
    assert changed["ml_home"] != pytest.approx(unchanged["ml_home"])

    def _resolver(match_id: int, team_id: int, stage: str):
        assert stage == "final"
        if team_id == 10:
            return home
        return away

    upcoming = pd.DataFrame([{
        "match_id": 501,
        "home_team": 10,
        "away_team": 20,
        "game_date": moment,
        "season": 13}])
    code, _selected, _writer = _run_predict_hockey(
        [
            "predict-hockey",
            "--league-id",
            "45",
            "--stage",
            "final",
            "--match-ids",
            "501"],
        [501],
        upcoming,
        MagicMock(),
        model=model,
        resolver=_resolver,
        rosters=pd.DataFrame(),
        stats=stats)
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    markets = payload["result"]["models"][0]["matches"][0]["markets"]
    assert markets["ml_home"] == pytest.approx(changed["ml_home"])


def _goalie_box_scores() -> pd.DataFrame:
    played = datetime(2026, 1, 2)
    rows = []
    for player_id, saves in ((101, 80), (102, 97)):
        rows.append({
            "match_id": 1,
            "player_id": player_id,
            "team_id": 10,
            "game_date": played,
            "shots_against": 100,
            "shots_saved": saves,
            "toi_seconds": 3600})
    return pd.DataFrame(rows)


def _confirmed_net() -> ProbableLineup:
    return ProbableLineup(
        match_id=501,
        team_id=10,
        players=[
            _goalie(101, 1, 0.2),
            _goalie(102, 0, 0.8)])


def _goalie(
        player_id: int,
        starter: int,
        start_probability: float) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="G",
        line=1,
        pp_unit=None,
        is_starting_goalie=starter,
        confidence=1.0,
        source="CONFIRMED",
        start_probability=start_probability)


def _skater(player_id: int) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="C",
        line=1,
        pp_unit=None,
        is_starting_goalie=None,
        confidence=1.0,
        source="CONFIRMED")


def test_final_props_skip_a_match_without_a_confirmed_lineup(
        caplog: pytest.LogCaptureFixture) -> None:
    fixtures = pd.DataFrame([{
        "match_id": 501,
        "home_team": 10,
        "away_team": 20,
        "game_date": datetime(2026, 10, 7, 18, 0),
        "season": 13}])
    with caplog.at_level(
            logging.WARNING,
            logger="models.pipeline.prediction.hockey_player_props"):
        with patch(
                "models.pipeline.prediction.hockey_player_props."
                "resolve_lineup_for_stage",
                return_value=None) as resolver:
            scored = _score_matches(
                MagicMock(),
                MagicMock(),
                fixtures,
                9,
                {},
                False,
                "final")
    assert scored == []
    assert resolver.call_args_list[0].args[2] == "final"
    assert "confirmed lineup" in caplog.text


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


def test_write_prediction_run_rejects_an_unknown_stage() -> None:
    with pytest.raises(ValueError, match="stage"):
        write_prediction_run(1, 2, "later", {"ml_home": 50.0})


def test_write_prediction_run_upserts_one_stage_and_leaves_the_other() -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value
    with patch(
            "models.pipeline.persistence.hockey_prediction_run_writer."
            "get_db_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = connection
        write_prediction_run(
            5, 21, "final", {"ml_away": 40.0, "ml_home": 60.0})
    sql = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "hockey_prediction_runs" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "DELETE" not in sql.upper()
    assert params[:3] == (5, 21, "final")
    assert json.loads(params[3]) == {"ml_away": 40.0, "ml_home": 60.0}
    connection.commit.assert_called_once()


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


def test_final_store_commits_once_after_the_new_final() -> None:
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

    def _snapshot(*_args, **kwargs):
        order.append("snapshot")
        assert kwargs.get("conn", _args[-1] if _args else None) is connection
        connection.commit.assert_not_called()

    with patch(
            "models.pipeline.core.cli.lookup_prediction_ids",
            side_effect=_lookup), patch(
            "models.pipeline.core.cli.replace_changed_finals",
            side_effect=_replace), patch(
            "models.pipeline.core.cli.write_predictions",
            side_effect=_write), patch(
            "models.pipeline.core.cli.write_prediction_run",
            side_effect=_snapshot), patch(
            "models.pipeline.core.cli.get_db_connection",
            return_value=manager):
        written = _store_hockey_team_prediction(
            501, 21, [_final_row()], {"ml_home": 60.0}, "final", True)
    assert written == 1
    assert order == ["lookup", "replace", "write", "snapshot"]
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


def test_failed_final_write_rolls_back_the_removed_pick() -> None:
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
            "models.pipeline.core.cli.write_prediction_run") as snapshot, patch(
            "models.pipeline.core.cli.get_db_connection",
            return_value=manager):
        with pytest.raises(RuntimeError, match="insert failed"):
            _store_hockey_team_prediction(
                501, 21, [_final_row()], {"ml_home": 60.0}, "final", True)
    drop_finals.assert_called_once_with([1], connection)
    drop_bets.assert_called_once_with(501, 21, [235], connection)
    snapshot.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
