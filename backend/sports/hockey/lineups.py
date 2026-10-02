"""Map hockey match roster rows into home and away lineups."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


HOCKEY_LINE_COUNT = 4
CONFIRMED_LINEUP_SOURCE = "CONFIRMED"
MODEL_LINEUP_SOURCE = "MODEL"
_PROBABLE_SOURCES = frozenset({
    CONFIRMED_LINEUP_SOURCE,
    "EXTERNAL",
    MODEL_LINEUP_SOURCE
})
_SOURCE_PRIORITY = (
    CONFIRMED_LINEUP_SOURCE,
    "EXTERNAL",
    MODEL_LINEUP_SOURCE)
_GOALIE_POSITION = "G"


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


def map_probable_hockey_lineups(
    frame: pd.DataFrame,
    home_team_id: int,
    home_team_name: str,
    away_team_id: int,
    away_team_name: str) -> dict[str, Any] | None:
    """Map a stored probable lineup into the match-lineup shape.

    ``lineup_status`` and ``source`` sit on each club. A goalie's
    ``start_probability`` is the value saved with the lineup. When that
    cell is empty, a named starter on a confirmed or external sheet is
    1 and the other goalie is 0. A model sheet is not scored here.
    """
    if frame.empty:
        return None
    home = _probable_team(frame, home_team_id, home_team_name)
    away = _probable_team(frame, away_team_id, away_team_name)
    return {"home": home, "away": away}


def _probable_team(
    frame: pd.DataFrame,
    team_id: int,
    team_name: str) -> dict[str, Any]:
    """Build one club, including status taken from its stored source."""
    team = _team_lines(
        frame,
        team_id,
        team_name,
        _map_probable_player)
    source = _team_source(frame, team_id)
    team["source"] = source
    team["lineup_status"] = _lineup_status(source)
    return team


def _map_probable_player(row: pd.Series) -> dict[str, Any]:
    """Map one probable-lineup row, including goalie start weight."""
    player = _map_player_row(row)
    player["start_probability"] = _stored_start_probability(row)
    return player


def _stored_start_probability(row: pd.Series) -> float | None:
    """Read a saved goalie weight, else 1 or 0 for a named starter."""
    if _position_code(row.get("position")).upper() != _GOALIE_POSITION:
        return None
    stored = _optional_float(row.get("start_probability"))
    if stored is not None and 0.0 <= stored <= 1.0:
        return stored
    # Brak kolumny albo NULL w MODEL nie uruchamia modelu startu.
    source = _source_code(row.get("source"))
    if source == MODEL_LINEUP_SOURCE or source is None:
        return None
    starter = _optional_int(row.get("is_starting_goalie"))
    if starter == 1:
        return 1.0
    if starter == 0:
        return 0.0
    return None


def _optional_float(value: object) -> float | None:
    """Convert nullable numeric values to floats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _team_source(frame: pd.DataFrame, team_id: int) -> str | None:
    """Pick one source for the players who land on lines 1-4."""
    sources: list[str] = []
    for _, row in frame.iterrows():
        if _optional_int(row.get("team_id")) != team_id:
            continue
        if _line_number(row.get("line")) is None:
            continue
        source = _source_code(row.get("source"))
        if source is not None:
            sources.append(source)
    return _dominant_source(sources)


def _source_code(value: object) -> str | None:
    """Return a trimmed source, or None when the cell is empty."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    source = str(value).strip().upper()
    if source == "":
        return None
    return source


def _dominant_source(sources: list[str]) -> str | None:
    """Prefer a confirmed sheet when one club mixes sources."""
    if not sources:
        return None
    unique = set(sources)
    if len(unique) == 1:
        return sources[0]
    for name in _SOURCE_PRIORITY:
        if name in unique:
            return name
    return sources[0]


def _lineup_status(source: str | None) -> str | None:
    """Map a stored source onto confirmed or probable."""
    if source == CONFIRMED_LINEUP_SOURCE:
        return "confirmed"
    if source in _PROBABLE_SOURCES:
        return "probable"
    return None
