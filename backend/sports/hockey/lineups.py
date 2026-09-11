"""Map hockey match roster rows into home and away lineups."""

from __future__ import annotations

from typing import Any

import pandas as pd


HOCKEY_LINE_COUNT = 4


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
    team_name: str) -> dict[str, Any]:
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
        players_by_line[line].append(_map_player_row(row))
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
