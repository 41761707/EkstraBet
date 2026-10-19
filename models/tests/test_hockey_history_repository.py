"""Column contracts and TOI parsing for the hockey history repository."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
import pytest

from models.pipeline.data.hockey_history_repository import (
    HOCKEY_ARENA_COLUMNS)
from models.pipeline.data.hockey_history_repository import (
    HOCKEY_MATCH_COLUMNS)
from models.pipeline.data.hockey_history_repository import (
    HOCKEY_MATCH_ROSTER_COLUMNS)
from models.pipeline.data.hockey_history_repository import (
    HOCKEY_PLAYER_STAT_COLUMNS)
from models.pipeline.data.hockey_history_repository import (
    HOCKEY_ROSTER_COLUMNS)
from models.pipeline.data.hockey_history_repository import (
    fetch_current_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_matches)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.data.hockey_history_repository import (
    fetch_team_arenas)
from models.pipeline.data.hockey_history_repository import (
    fetch_upcoming_hockey_matches)
from models.pipeline.data.hockey_history_repository import parse_toi_seconds

_REPOSITORY = "models.pipeline.data.hockey_history_repository"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("--:--", None),
        ("0", 0),
        ("96:10", 96 * 60 + 10),
        (None, None),
        ("", None),
        ("   ", None),
        ("60:00", 3600),
        ("17:01:00", 17 * 60 + 1),
        ("00:00:10", 10),
        ("19.27", 19 * 60 + 27),
        ("96:70", None),
        ("not-a-time", None)])
def test_parse_toi_seconds(raw: object, expected: int | None) -> None:
    assert parse_toi_seconds(raw) == expected


def test_fetch_hockey_matches_maps_columns() -> None:
    raw = _match_frame()
    query, params = _capture_query(fetch_hockey_matches, raw, 45)
    assert "LEFT JOIN hockey_matches_add" in query
    assert "a.OTwinner AS ot_winner" in query
    assert "a.SOwinner AS so_winner" in query
    assert params == (45, 2)


def test_fetch_upcoming_hockey_matches_filters_unplayed() -> None:
    query, params = _capture_query(
        fetch_upcoming_hockey_matches,
        _match_frame(),
        45)
    assert "m.result = '0'" in query
    assert "hockey_matches_add" in query
    assert params == (45, 2)


def test_fetch_player_stats_parses_toi_and_keeps_columns() -> None:
    raw = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "match_id": [10, 10, 10, 10],
        "player_id": [7, 8, 9, 10],
        "team_id": [3, 3, 3, 3],
        "game_date": [datetime(2026, 1, 2)] * 4,
        "season": [12, 12, 12, 12],
        "goals": [0, 1, 0, 0],
        "assists": [0, 0, 1, 0],
        "points": [0, 1, 1, 0],
        "plus_minus": [0, 1, -1, 0],
        "sog": [1, 3, 2, 0],
        "toi": ["--:--", "0", "96:10", "17:01:00"],
        "shots_against": [None, None, None, 28],
        "shots_saved": [None, None, None, 25]})
    frame = _run_fetch(fetch_hockey_player_stats, raw, 45)
    assert list(frame.columns) == HOCKEY_PLAYER_STAT_COLUMNS
    assert pd.isna(frame.loc[0, "toi_seconds"])
    assert int(frame.loc[1, "toi_seconds"]) == 0
    assert int(frame.loc[2, "toi_seconds"]) == 96 * 60 + 10
    assert int(frame.loc[3, "toi_seconds"]) == 17 * 60 + 1
    assert frame.loc[3, "shots_against"] == 28


def test_fetch_match_rosters_maps_columns() -> None:
    raw = pd.DataFrame([{
        "id": 5,
        "match_id": 10,
        "player_id": 7,
        "team_id": 3,
        "position": "C",
        "line": 1,
        "number": 19,
        "game_date": datetime(2026, 1, 2),
        "season": 12}])
    query, _params = _capture_query(fetch_hockey_match_rosters, raw, 45)
    assert "hockey_match_rosters" in query
    assert "m.game_date" in query
    assert list(raw.columns) == HOCKEY_MATCH_ROSTER_COLUMNS


def test_fetch_current_rosters_and_arenas_map_columns() -> None:
    roster = pd.DataFrame([{
        "id": 1,
        "team_id": 3,
        "player_id": 7,
        "number": 19,
        "line": 1,
        "position": "C",
        "pp": 1,
        "is_injured": 0,
        "injury_status": None,
        "injury_note": None,
        "updated_at": datetime(2026, 9, 1)}])
    arena = pd.DataFrame([{
        "team_id": 3,
        "latitude": 40.7,
        "longitude": -74.0,
        "timezone": "America/New_York"}])
    roster_query, roster_params = _capture_query(
        fetch_current_rosters,
        roster)
    arena_query, arena_params = _capture_query(fetch_team_arenas, arena)
    assert "FROM hockey_rosters" in roster_query
    assert roster_params == ()
    assert list(roster.columns) == HOCKEY_ROSTER_COLUMNS
    assert "FROM hockey_team_arenas" in arena_query
    assert arena_params == ()
    assert list(arena.columns) == HOCKEY_ARENA_COLUMNS


def _match_frame() -> pd.DataFrame:
    row = {column: None for column in HOCKEY_MATCH_COLUMNS}
    row.update({
        "match_id": 10,
        "league": 45,
        "season": 13,
        "home_team": 1,
        "away_team": 2,
        "game_date": datetime(2026, 10, 7, 19, 0),
        "round": 1,
        "sport_id": 2,
        "result": "0",
        "ot_winner": None,
        "so_winner": None})
    return pd.DataFrame([row])


def _capture_query(fetcher, raw: pd.DataFrame, *args: object) -> tuple:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return raw

    frame = _run_with_reader(fetcher, _read_sql, *args)
    assert list(frame.columns) == list(raw.columns)
    return str(captured["query"]), captured["params"]


def _run_fetch(fetcher, raw: pd.DataFrame, *args: object) -> pd.DataFrame:
    def _read_sql(
            _query: str,
            _connection: object,
            params: tuple = ()) -> pd.DataFrame:
        del params
        return raw

    return _run_with_reader(fetcher, _read_sql, *args)


def _run_with_reader(fetcher, reader, *args: object) -> pd.DataFrame:
    context = MagicMock()
    context.__enter__.return_value = MagicMock()
    context.__exit__.return_value = False
    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=context), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=reader):
        return fetcher(*args)
