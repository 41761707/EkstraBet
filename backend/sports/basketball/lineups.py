"""Map basketball match roster rows into home and away lineups."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _jersey_number(value: object) -> int | None:
    """Return jersey number, mapping missing and -1 to None."""
    number = _optional_int(value)
    # 0 jest legalnym numerem NBA; -1 w źródle oznacza brak danych
    if number is None or number == -1:
        return None
    return number


def _is_starter(value: object) -> bool:
    """Return True only when starter flag is exactly 1."""
    starter = _optional_int(value)
    return starter == 1


def _map_player_row(row: pd.Series) -> dict[str, Any]:
    """Map one basketball match roster row."""
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_id": int(row["team_id"]),
        "number": _jersey_number(row.get("number")),
        "starter": _is_starter(row.get("starter"))
    }


def _team_players(
    frame: pd.DataFrame,
    team_id: int,
    team_name: str) -> dict[str, Any]:
    """Collect roster players for one team, skipping other team ids."""
    players: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        row_team_id = _optional_int(row.get("team_id"))
        if row_team_id != team_id:
            continue
        players.append(_map_player_row(row))
    return {
        "team_id": team_id,
        "team_name": team_name,
        "players": players
    }


def map_basketball_lineups(
    frame: pd.DataFrame,
    home_team_id: int,
    home_team_name: str,
    away_team_id: int,
    away_team_name: str) -> dict[str, Any] | None:
    """Group roster rows into home/away teams, or None if empty."""
    if frame.empty:
        return None
    return {
        "home": _team_players(frame, home_team_id, home_team_name),
        "away": _team_players(frame, away_team_id, away_team_name)
    }
