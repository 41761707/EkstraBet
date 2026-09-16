"""Map hockey match play-by-play events for the match timeline."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd


HOCKEY_PERIOD_MIN = 1
HOCKEY_PERIOD_MAX = 5
EventSide = Literal["home", "away"]


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    """Convert nullable values to stripped strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _flag_bool(value: object) -> bool:
    """Treat 1 as true; missing or other values as false."""
    return _optional_int(value) == 1


def _period_number(value: object) -> int | None:
    """Return period 1-5, or None when missing or out of range."""
    period = _optional_int(value)
    if period is None:
        return None
    if period < HOCKEY_PERIOD_MIN or period > HOCKEY_PERIOD_MAX:
        return None
    return period


def _event_side(team_id: int, home_team_id: int) -> EventSide:
    """Place the event on the home or away side of the timeline."""
    if team_id == home_team_id:
        return "home"
    return "away"


def _map_event_row(
    row: pd.Series,
    home_team_id: int) -> dict[str, Any] | None:
    """Map one play-by-play row, or None when required fields are invalid."""
    event_id_pk = _optional_int(row.get("id"))
    team_id = _optional_int(row.get("team_id"))
    player_id = _optional_int(row.get("player_id"))
    event_id = _optional_int(row.get("event_id"))
    period = _period_number(row.get("period"))
    team_name = _optional_str(row.get("team_name"))
    player_name = _optional_str(row.get("player_name"))
    event_name = _optional_str(row.get("event_name"))
    if (
            event_id_pk is None
            or team_id is None
            or player_id is None
            or event_id is None
            or period is None
            or team_name is None
            or player_name is None
            or event_name is None):
        # pomijamy niepełne wiersze, żeby timeline nie padał na brudnych danych
        return None
    event_time = _optional_str(row.get("event_time")) or ""
    return {
        "id": event_id_pk,
        "team_id": team_id,
        "team_name": team_name,
        "player_id": player_id,
        "player_name": player_name,
        "event_id": event_id,
        "event_name": event_name,
        "period": period,
        "event_time": event_time,
        "description": _optional_str(row.get("description")),
        "is_power_play": _flag_bool(row.get("pp_flag")),
        "is_empty_net": _flag_bool(row.get("en_flag")),
        "side": _event_side(team_id, home_team_id)
    }


def map_hockey_match_events(
    frame: pd.DataFrame,
    home_team_id: int) -> list[dict[str, Any]] | None:
    """Return ordered play-by-play events, or None when none can be shown."""
    if frame.empty:
        return None
    events = []
    for _, row in frame.iterrows():
        mapped = _map_event_row(row, home_team_id)
        if mapped is not None:
            events.append(mapped)
    if not events:
        return None
    return events
