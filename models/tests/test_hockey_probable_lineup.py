"""Projected NHL lineups: injuries, goalie rest and stage priority."""

from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from models.pipeline.core.cli import build_parser
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.ratings import HockeyTeamRatingState
from models.pipeline.features.hockey.team_features import (
    _goalie_start_weights)
from models.pipeline.lineups.hockey_goalie_start import GOALIE_START_FEATURES
from models.pipeline.lineups.hockey_goalie_start import GoalieStartHistory
from models.pipeline.lineups.hockey_goalie_start import GoalieStartModel
from models.pipeline.lineups import hockey_probable_lineup as lineups
from models.pipeline.lineups.hockey_probable_lineup import (
    ProjectionContext)
from models.pipeline.lineups.hockey_probable_lineup import (
    _GoalieReadState)
from models.pipeline.lineups.hockey_probable_lineup import (
    apply_model_start_probabilities)
from models.pipeline.lineups.hockey_probable_lineup import (
    build_probable_lineup)
from models.pipeline.lineups.hockey_probable_lineup import lineup_for_stage
from models.pipeline.lineups.hockey_probable_lineup import (
    resolve_lineup_for_stage)
from models.pipeline.persistence.hockey_lineup_writer import (
    write_probable_lineups)


_AS_OF = datetime(2026, 10, 3, 19, 0)
_LAST_GAME = datetime(2026, 10, 1, 19, 0)


def test_injured_skater_is_replaced_by_the_highest_toi() -> None:
    lineup = build_probable_lineup(5, 7, _AS_OF, _injury_context())
    ids = {player.player_id for player in lineup.players}
    assert 2 not in ids
    assert 6 not in ids
    assert ids == {1, 3, 4}
    replacement = _player(lineup, 4)
    assert replacement.position == "LW"
    assert replacement.line == 1
    assert replacement.pp_unit == 1
    assert replacement.confidence == 0.0
    assert replacement.source == "MODEL"
    assert _player(lineup, 1).confidence == 1.0


def test_confirmed_lineup_for_the_same_match_is_not_overwritten() -> None:
    connection, cursor = _stored_connection([(5, "CONFIRMED")])
    written = write_probable_lineups([_stored_lineup(5)], connection)
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert written == 0
    assert not any(sql.strip().startswith("DELETE") for sql in statements)
    cursor.executemany.assert_not_called()
    connection.commit.assert_not_called()


def test_back_to_back_goalie_has_lower_start_probability() -> None:
    start_on = datetime(2026, 10, 1, 19, 0)
    rested_at = start_on + timedelta(days=5)
    tired_at = start_on + timedelta(days=1)
    model = _b2b_model(start_on, rested_at, tired_at)
    rested = build_probable_lineup(
        5, 7, rested_at, _goalie_context(model, start_on, rested_at))
    tired = build_probable_lineup(
        5, 7, tired_at, _goalie_context(model, start_on, tired_at))
    rested_goalie = _player(rested, 10)
    tired_goalie = _player(tired, 10)
    assert rested_goalie.start_probability is not None
    assert tired_goalie.start_probability is not None
    assert tired_goalie.start_probability < rested_goalie.start_probability
    assert tired_goalie.is_starting_goalie == 1


def test_rested_backup_is_the_only_marked_starter() -> None:
    starts, as_of = _rotation_starts()
    lineup = build_probable_lineup(
        5,
        7,
        as_of,
        _two_goalie_context(_rank_model(starts, as_of), starts, as_of))
    rested = _player(lineup, 11)
    tired = _player(lineup, 10)
    assert rested.is_starting_goalie == 1
    assert tired.is_starting_goalie == 0
    assert rested.start_probability is not None
    assert tired.start_probability is not None
    assert rested.start_probability > tired.start_probability


def test_tied_start_probabilities_mark_the_lower_player_id() -> None:
    as_of = datetime(2026, 10, 2, 19, 0)
    lineup = build_probable_lineup(
        5,
        7,
        as_of,
        _two_goalie_context(
            _TiedStarts(), _empty_starts(), as_of, backup_id=20))
    assert _player(lineup, 10).is_starting_goalie == 1
    assert _player(lineup, 20).is_starting_goalie == 0


def test_resolve_restores_model_start_probabilities(
        monkeypatch: pytest.MonkeyPatch) -> None:
    starts, as_of = _rotation_starts()
    monkeypatch.setattr(
        lineups, "_fetch_rows", lambda match_id, team_id: _stored_goalies())
    monkeypatch.setattr(
        lineups,
        "_read_model_for_match",
        lambda match_id: _GoalieReadState(
            model=_rank_model(starts, as_of),
            starts=starts,
            matches=_match_frame(as_of),
            ratings=HockeyTeamRatingState()))
    lineup = resolve_lineup_for_stage(5, 7, "initial")
    assert lineup is not None
    assert _player(lineup, 10).is_starting_goalie == 1
    assert _player(lineup, 11).start_probability is not None
    assert _player(lineup, 10).start_probability is not None
    assert (
        _player(lineup, 11).start_probability
        > _player(lineup, 10).start_probability)


def test_resolve_leaves_a_confirmed_starter_unscored(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lineups, "_fetch_rows", lambda match_id, team_id: _stored_goalies(
            "CONFIRMED"))

    def _refuse(match_id: int) -> _GoalieReadState:
        raise AssertionError(match_id)

    monkeypatch.setattr(lineups, "_read_model_for_match", _refuse)
    lineup = resolve_lineup_for_stage(5, 7, "final")
    assert lineup is not None
    assert _player(lineup, 10).start_probability is None


def test_unconfirmed_goalies_are_weighted_by_start_probability() -> None:
    tired = _goalie_player(10, 1, 0.2)
    rested = _goalie_player(11, 0, 0.8)
    weights = _goalie_start_weights(ProbableLineup(
        match_id=5, team_id=7, players=[tired, rested]))
    by_id = {player.player_id: weight for player, weight in weights}
    assert by_id == {10: pytest.approx(0.2), 11: pytest.approx(0.8)}


def test_no_previous_game_does_not_project_every_skater() -> None:
    as_of = _AS_OF
    lineup = build_probable_lineup(5, 7, as_of, ProjectionContext(
        matches=_match_frame(as_of),
        game_rosters=_empty_games(),
        current_roster=pd.DataFrame([
            _roster(1, "C", 0, 1),
            _roster(2, "LW", 0, 1),
            _roster(3, "RW", 0, 1),
            _roster(4, "D", 0, 1),
            _roster(10, "G", 0, 1)]),
        player_stats=_empty_toi(),
        goalie_model=_TiedStarts(),
        goalie_starts=_empty_starts(),
        ratings=HockeyTeamRatingState()))
    assert [player.player_id for player in lineup.players] == [10]


def test_stored_model_goalies_receive_start_probabilities() -> None:
    starts, as_of = _rotation_starts()
    stored = lineup_for_stage(5, 7, "initial", _stored_goalies())
    assert stored is not None
    assert _player(stored, 11).start_probability is None
    scored = apply_model_start_probabilities(
        stored, _rank_model(starts, as_of), starts, 1500.0, as_of)
    assert (
        _player(scored, 11).start_probability
        > _player(scored, 10).start_probability)


def test_build_hockey_lineups_parser_accepts_a_dry_run() -> None:
    args = build_parser().parse_args([
        "build-hockey-lineups",
        "--league-id",
        "45"])
    assert args.command == "build-hockey-lineups"
    assert args.league_id == 45
    assert args.write_db is False


def test_initial_prefers_confirmed_over_model() -> None:
    lineup = lineup_for_stage(7, 3, "initial", _rows("MODEL", "CONFIRMED"))
    assert lineup is not None
    assert {player.source for player in lineup.players} == {"CONFIRMED"}


def test_initial_uses_model_when_nothing_stronger_exists() -> None:
    lineup = lineup_for_stage(7, 3, "initial", _rows("MODEL"))
    assert lineup is not None
    assert lineup.players[0].source == "MODEL"
    assert lineup.players[0].start_probability is None


def test_final_ignores_a_model_lineup() -> None:
    assert lineup_for_stage(7, 3, "final", _rows("MODEL")) is None


def test_missing_rows_leave_the_club_without_a_lineup() -> None:
    empty = pd.DataFrame(columns=["source", "player_id", "position"])
    assert lineup_for_stage(7, 3, "initial", empty) is None


def _injury_context() -> ProjectionContext:
    return ProjectionContext(
        matches=_match_frame(_AS_OF),
        game_rosters=pd.DataFrame([
            _dressed(1, "C", 1),
            _dressed(2, "LW", 1),
            _dressed(3, "D", 1)]),
        current_roster=pd.DataFrame([
            _roster(1, "C", 0, 1),
            _roster(2, "LW", 1, 1),
            _roster(3, "D", 0, 1),
            _roster(4, "RW", 0, None, pp_unit=1),
            _roster(6, "RW", 0, None)]),
        player_stats=pd.DataFrame([
            _toi(4, 1200),
            _toi(6, 100)]),
        goalie_model=GoalieStartModel(),
        goalie_starts=_empty_starts(),
        ratings=HockeyTeamRatingState())


def _two_goalie_context(
        model: object,
        starts: pd.DataFrame,
        as_of: datetime,
        backup_id: int = 11) -> ProjectionContext:
    yesterday = datetime(2026, 10, 1, 19, 0)
    return ProjectionContext(
        matches=_match_frame(as_of),
        game_rosters=pd.DataFrame([
            _dressed(1, "C", 1, game_date=yesterday)]),
        current_roster=pd.DataFrame([
            _roster(1, "C", 0, 1),
            _roster(10, "G", 0, 1),
            _roster(backup_id, "G", 0, 2)]),
        player_stats=_empty_toi(),
        goalie_model=model,
        goalie_starts=starts,
        ratings=HockeyTeamRatingState())


def _rotation_starts() -> tuple[pd.DataFrame, datetime]:
    opening = datetime(2026, 9, 1, 19, 0)
    rows = [
        {
            "team_id": 7,
            "player_id": 11,
            "game_date": opening + timedelta(days=offset)}
        for offset in range(9)]
    rows.append({
        "team_id": 7,
        "player_id": 10,
        "game_date": datetime(2026, 10, 1, 19, 0)})
    return pd.DataFrame(rows), datetime(2026, 10, 2, 19, 0)


def _rank_model(
        starts: pd.DataFrame,
        as_of: datetime) -> GoalieStartModel:
    history = GoalieStartHistory.from_starts(starts)
    rested = history.feature_row(7, 11, as_of, 1500.0)
    tired = history.feature_row(7, 10, as_of, 1500.0)
    rows = [rested] * 30 + [tired] * 30
    labels = [1] * 30 + [0] * 30
    return GoalieStartModel().fit(pd.DataFrame(rows), labels)


class _TiedStarts:
    """Equal start probabilities, so the lower id stays the starter."""

    def predict_proba(self, features: pd.DataFrame) -> list[float]:
        return [0.5] * len(features)


def _stored_goalies(source: str = "MODEL") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player_id": 10,
            "position": "G",
            "line": 1,
            "pp_unit": None,
            "is_starting_goalie": 1,
            "confidence": 1.0,
            "source": source},
        {
            "player_id": 11,
            "position": "G",
            "line": 2,
            "pp_unit": None,
            "is_starting_goalie": 0,
            "confidence": 0.4,
            "source": source}])


def _goalie_player(
        player_id: int,
        starter: int,
        probability: float) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="G",
        line=1 if starter else 2,
        pp_unit=None,
        is_starting_goalie=starter,
        confidence=0.5,
        source="MODEL",
        start_probability=probability)


def _empty_games() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "match_id",
        "team_id",
        "player_id",
        "position",
        "line",
        "game_date"])


def _empty_toi() -> pd.DataFrame:
    return pd.DataFrame(columns=["player_id", "game_date", "toi_seconds"])


def _goalie_context(
        model: GoalieStartModel,
        start_on: datetime,
        as_of: datetime) -> ProjectionContext:
    return ProjectionContext(
        matches=_match_frame(as_of),
        game_rosters=pd.DataFrame([
            _dressed(10, "G", 1, game_date=start_on)]),
        current_roster=pd.DataFrame([_roster(10, "G", 0, 1)]),
        player_stats=pd.DataFrame(
            columns=["player_id", "game_date", "toi_seconds"]),
        goalie_model=model,
        goalie_starts=pd.DataFrame([{
            "team_id": 7,
            "player_id": 10,
            "game_date": start_on}]),
        ratings=HockeyTeamRatingState())


def _b2b_model(
        start_on: datetime,
        rested_at: datetime,
        tired_at: datetime) -> GoalieStartModel:
    rested = _goalie_features(start_on, rested_at)
    tired = _goalie_features(start_on, tired_at)
    rows = [rested] * 30 + [tired] * 30
    labels = [1] * 30 + [0] * 30
    return GoalieStartModel().fit(pd.DataFrame(rows), labels)


def _goalie_features(start_on: datetime, as_of: datetime) -> dict[str, float]:
    history = GoalieStartHistory.from_starts(pd.DataFrame([{
        "team_id": 7,
        "player_id": 10,
        "game_date": start_on}]))
    return history.feature_row(7, 10, as_of, 1500.0)


def _match_frame(as_of: datetime) -> pd.DataFrame:
    return pd.DataFrame([{
        "match_id": 5,
        "home_team": 7,
        "away_team": 8,
        "game_date": as_of,
        "season": 13,
        "result": "0"}])


def _dressed(
        player_id: int,
        position: str,
        line: int,
        game_date: datetime = _LAST_GAME) -> dict[str, object]:
    return {
        "match_id": 10,
        "team_id": 7,
        "player_id": player_id,
        "position": position,
        "line": line,
        "game_date": game_date}


def _roster(
        player_id: int,
        position: str,
        injured: int,
        line: int | None,
        pp_unit: int | None = None) -> dict[str, object]:
    return {
        "team_id": 7,
        "player_id": player_id,
        "position": position,
        "line": line,
        "pp_unit": pp_unit,
        "is_injured": injured}


def _toi(player_id: int, seconds: int) -> dict[str, object]:
    return {
        "player_id": player_id,
        "team_id": 7,
        "game_date": datetime(2026, 9, 1, 19, 0),
        "toi_seconds": seconds}


def _empty_starts() -> pd.DataFrame:
    return pd.DataFrame(columns=["team_id", "player_id", "game_date"])


def _player(lineup: ProbableLineup, player_id: int) -> ProbableLineupPlayer:
    return next(
        player
        for player in lineup.players
        if player.player_id == player_id)


def _stored_lineup(match_id: int) -> ProbableLineup:
    return ProbableLineup(
        match_id=match_id,
        team_id=7,
        players=[ProbableLineupPlayer(
            player_id=1,
            position="C",
            line=1,
            pp_unit=None,
            is_starting_goalie=None,
            confidence=1.0,
            source="MODEL")])


def _stored_connection(
        rows: list[tuple[int, str]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def _rows(*sources: str) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player_id": 10 + index,
            "position": "C" if index == 0 else "G",
            "line": 1,
            "pp_unit": None,
            "is_starting_goalie": 1 if index else 0,
            "confidence": 0.8,
            "source": source}
        for index, source in enumerate(sources)])


def test_goalie_feature_names_match_the_model() -> None:
    assert set(_goalie_features(
        _LAST_GAME, _AS_OF)) == set(GOALIE_START_FEATURES)
