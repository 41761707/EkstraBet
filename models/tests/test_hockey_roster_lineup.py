"""The next-game sheet is the current ``hockey_rosters`` rows."""

from __future__ import annotations

import pandas as pd

from models.pipeline.lineups.hockey_roster_lineup import load_roster_lineup


def test_starter_is_line_one_and_backup_stays_off_the_net() -> None:
    lineup = load_roster_lineup(_rows(), team_id=7, match_id=5)
    assert lineup is not None
    by_id = {player.player_id: player for player in lineup.players}
    assert by_id[1].is_starting_goalie == 1
    assert by_id[1].line == 1
    assert by_id[2].is_starting_goalie == 0
    assert by_id[2].line == 2
    assert by_id[2].position == "G"


def test_line_zero_and_injured_are_left_out() -> None:
    lineup = load_roster_lineup(_rows(), team_id=7, match_id=5)
    assert lineup is not None
    dressed = {player.player_id for player in lineup.players}
    assert 3 not in dressed
    assert 9 not in dressed
    assert 8 not in dressed
    assert 4 in dressed
    assert 5 in dressed


def test_an_empty_seat_is_not_filled_from_line_zero() -> None:
    frame = pd.DataFrame([
        _row(8, "C", 0, 0),
        _row(4, "D", 1, 0)])
    lineup = load_roster_lineup(frame, team_id=7, match_id=5)
    assert lineup is not None
    assert [player.player_id for player in lineup.players] == [4]


def test_missing_club_returns_none() -> None:
    assert load_roster_lineup(_rows(), team_id=99, match_id=5) is None
    assert load_roster_lineup(pd.DataFrame(), team_id=7, match_id=5) is None


def _rows() -> pd.DataFrame:
    return pd.DataFrame([
        _row(1, "G", 1, 0),
        _row(2, "G", 2, 0),
        _row(3, "G", 0, 1),
        _row(4, "C", 1, 0),
        _row(5, "D", 3, 0),
        _row(9, "D", 2, 1),
        _row(8, "LW", 0, 1),
        _row(6, "C", 1, 0, team_id=8)])


def _row(
        player_id: int,
        position: str,
        line: int,
        injured: int,
        team_id: int = 7) -> dict[str, object]:
    return {
        "team_id": team_id,
        "player_id": player_id,
        "position": position,
        "line": line,
        "pp": 1 if position == "C" else 0,
        "is_injured": injured}
