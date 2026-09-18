"""Read-only SQL access to football table special slot thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.database import get_db_connection

_SPECIAL_SLOTS_SQL = """
    SELECT league_id, top_slots, bot_slots
    FROM football_table_special_slots
    WHERE league_id = %s
    LIMIT 1
"""


@dataclass(frozen=True)
class FootballTableSpecialSlotsRecord:
    """League slot thresholds for top places and relegation."""

    league_id: int
    top_slots: int
    bot_slots: int


def fetch_special_slots(
        league_id: int) -> FootballTableSpecialSlotsRecord | None:
    """Return slot thresholds for a league, or None if missing/invalid."""
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _SPECIAL_SLOTS_SQL,
            connection,
            params=(league_id,))
    if frame.empty:
        return None
    return _map_special_slots_row(frame.iloc[0])


def _map_special_slots_row(
        row: pd.Series) -> FootballTableSpecialSlotsRecord | None:
    top_slots = _as_non_negative_int(row["top_slots"])
    bot_slots = _as_non_negative_int(row["bot_slots"])
    # ujemne albo nieparsowalne progi = brak konfiguracji, nie 500
    if top_slots is None or bot_slots is None:
        return None
    return FootballTableSpecialSlotsRecord(
        league_id=int(row["league_id"]),
        top_slots=top_slots,
        bot_slots=bot_slots)


def _as_non_negative_int(raw: Any) -> int | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value
