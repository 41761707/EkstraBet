"""Map hockey match roster rows into home and away lineups."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


HOCKEY_LINE_COUNT = 4
_FORWARD_POSITIONS = frozenset({"LW", "C", "RW"})
_DEFENSE_POSITION = "D"
_GOALIE_POSITION = "G"
_GOALIE_LINES = frozenset({1, 2})
_DEFENSE_LINES = frozenset({1, 2, 3})


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _position_code(value: object) -> str:
    """Return a position code, or empty string when missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _line_number(value: object) -> int | None:
    """Return line 1-4, or None when missing or out of range."""
    line = _optional_int(value)
    if line is None or line < 1 or line > HOCKEY_LINE_COUNT:
        return None
    return line


def _map_player_row(row: pd.Series) -> dict[str, Any]:
    """Map one hockey match roster row."""
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_id": int(row["team_id"]),
        "position": _position_code(row.get("position")),
        "number": _optional_int(row.get("number")),
        "line": int(row["line"])
    }


def _team_lines(
    frame: pd.DataFrame,
    team_id: int,
    team_name: str,
    player_mapper: Callable[[pd.Series], dict[str, Any]] = _map_player_row
) -> dict[str, Any]:
    """Group roster rows into four lines for one team."""
    players_by_line: dict[int, list[dict[str, Any]]] = {
        line_no: [] for line_no in range(1, HOCKEY_LINE_COUNT + 1)
    }
    for _, row in frame.iterrows():
        row_team_id = _optional_int(row.get("team_id"))
        if row_team_id != team_id:
            continue
        line = _line_number(row.get("line"))
        # pomijamy linie poza 1-4 i NULL, żeby mapper nie padał na brudnych danych
        if line is None:
            continue
        players_by_line[line].append(player_mapper(row))
    return {
        "team_id": team_id,
        "team_name": team_name,
        "lines": [
            {"line": line_no, "players": players_by_line[line_no]}
            for line_no in range(1, HOCKEY_LINE_COUNT + 1)
        ]
    }


def map_hockey_lineups(
    frame: pd.DataFrame,
    home_team_id: int,
    home_team_name: str,
    away_team_id: int,
    away_team_name: str) -> dict[str, Any] | None:
    """Group roster rows into home/away lines 1-4, or None if empty."""
    if frame.empty:
        return None
    return {
        "home": _team_lines(frame, home_team_id, home_team_name),
        "away": _team_lines(frame, away_team_id, away_team_name)
    }


def map_current_roster_lineups(
    frame: pd.DataFrame,
    home_team_id: int,
    home_team_name: str,
    away_team_id: int,
    away_team_name: str) -> dict[str, Any] | None:
    """Map ``hockey_rosters`` into the match-lineup shape.

    A goalie on line 1 is the starter and a goalie on line 2 is the
    backup. Line 0 and injured players stay off the sheet.
    """
    if frame.empty:
        return None
    kept = frame.loc[frame.apply(_is_dressed_roster_row, axis=1)]
    if kept.empty:
        return None
    return map_hockey_lineups(
        kept,
        home_team_id,
        home_team_name,
        away_team_id,
        away_team_name)


def _is_dressed_roster_row(row: pd.Series) -> bool:
    """Keep the players who dress for the next game."""
    if _optional_int(row.get("is_injured")) == 1:
        return False
    position = _position_code(row.get("position")).upper()
    line = _optional_int(row.get("line"))
    if line is None:
        return False
    if position == _GOALIE_POSITION:
        return line in _GOALIE_LINES
    if position == _DEFENSE_POSITION:
        return line in _DEFENSE_LINES
    if position in _FORWARD_POSITIONS:
        return 1 <= line <= HOCKEY_LINE_COUNT
    return False
