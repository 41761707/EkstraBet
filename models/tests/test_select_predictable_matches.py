"""Rules for which upcoming NHL matches may be predicted."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from models.pipeline.data.hockey_history_repository import (
    select_predictable_matches)

_REPOSITORY = "models.pipeline.data.hockey_history_repository"
_NOW = datetime(2026, 10, 7, 12, 0)
_LEAGUE_ID = 45


def test_back_to_back_hides_the_second_game() -> None:
    frame = _schedule([
        _row(10, 1, 2, datetime(2026, 10, 7, 19, 0), "0"),
        _row(11, 1, 3, datetime(2026, 10, 8, 19, 0), "0")])
    selected = _select(frame)
    assert selected == [10]


def test_second_game_is_returned_after_the_first_has_a_result() -> None:
    frame = _schedule([
        _row(10, 1, 2, datetime(2026, 10, 7, 19, 0), "1"),
        _row(11, 1, 3, datetime(2026, 10, 8, 19, 0), "0"),
        _row(9, 3, 4, datetime(2026, 10, 5, 19, 0), "2")])
    selected = _select(frame)
    assert selected == [11]


def test_postponed_match_does_not_block_the_next_one(caplog) -> None:
    frame = _schedule([
        _row(8, 1, 2, datetime(2026, 10, 5, 10, 0), "0"),
        _row(12, 1, 2, datetime(2026, 10, 7, 19, 0), "0")])
    with caplog.at_level("WARNING"):
        selected = _select(frame)
    assert selected == [12]
    assert "8" in caplog.text


def test_match_exactly_24_hours_old_is_not_postponed() -> None:
    frame = _schedule([
        _row(13, 1, 2, datetime(2026, 10, 6, 12, 0), "0")])
    assert _select(frame) == [13]


def test_match_is_returned_only_when_next_for_both_teams() -> None:
    frame = _schedule([
        _row(20, 2, 4, datetime(2026, 10, 7, 19, 0), "0"),
        _row(21, 1, 2, datetime(2026, 10, 8, 19, 0), "0"),
        _row(22, 1, 3, datetime(2026, 10, 9, 19, 0), "0")])
    assert _select(frame) == [20]


def test_missing_earlier_result_blocks_the_team() -> None:
    frame = _schedule([
        _row(30, 1, 2, datetime(2026, 10, 6, 19, 0), None),
        _row(31, 1, 3, datetime(2026, 10, 8, 19, 0), "0")])
    assert _select(frame) == []


def test_select_passes_league_and_sport() -> None:
    captured: dict[str, object] = {}

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple = ()) -> pd.DataFrame:
        captured["query"] = query
        captured["params"] = params
        return _schedule([])

    context = MagicMock()
    context.__enter__.return_value = MagicMock()
    context.__exit__.return_value = False
    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=context), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        assert select_predictable_matches(_LEAGUE_ID, _NOW) == []
    assert "m.league = %s" in str(captured["query"])
    assert captured["params"] == (_LEAGUE_ID, 2)


def _select(frame: pd.DataFrame) -> list[int]:
    context = MagicMock()
    context.__enter__.return_value = MagicMock()
    context.__exit__.return_value = False

    def _read_sql(
            _query: str,
            _connection: object,
            params: tuple = ()) -> pd.DataFrame:
        del params
        return frame

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=context), patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        return select_predictable_matches(_LEAGUE_ID, _NOW)


def _schedule(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["match_id", "home_team", "away_team", "game_date", "result"])


def _row(
        match_id: int,
        home_team: int,
        away_team: int,
        game_date: datetime,
        result: str | None) -> dict:
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "game_date": game_date,
        "result": result}
