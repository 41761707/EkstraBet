"""Read football point adjustments for one league and season."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import pandas as pd
from mysql.connector.errors import Error as MySQLError
from pandas.errors import DatabaseError as PandasDatabaseError

from backend.database import get_db_connection


logger = logging.getLogger(__name__)

# Pandas wkleja całe SQL do komunikatu. Fraza musi wskazywać
# tę tabelę, a nie dowolne "doesn't exist".
_MISSING_ADJUSTMENTS_TABLE = re.compile(
    r"football_point_adjustments'\s+doesn't exist",
    re.IGNORECASE)

_ADJUSTMENTS_SQL = """
    SELECT
        adjustments.id AS id,
        adjustments.team_id AS team_id,
        adjustments.points_delta AS points_delta,
        adjustments.reason AS reason
    FROM football_point_adjustments adjustments
    WHERE adjustments.league_id = %s
        AND adjustments.season_id = %s
    ORDER BY adjustments.id
"""


@dataclass(frozen=True)
class PointAdjustment:
    """One team's official point change for a league season.

    ``points_delta`` is the sum of that team's rows.
    ``reason`` joins every row reason with ``"; "`` in id order.
    """

    team_id: int
    points_delta: int
    reason: str


def fetch_point_adjustments(
        league_id: int,
        season_id: int) -> dict[int, PointAdjustment]:
    """Return one summed adjustment per team.

    An empty dict means there are no rows, or the adjustments
    table is not in the database yet.
    """
    frame = _read_adjustment_frame(league_id, season_id)
    if frame is None or frame.empty:
        return {}
    return _aggregate_adjustments(frame)


def _read_adjustment_frame(
        league_id: int,
        season_id: int) -> pd.DataFrame | None:
    """Load adjustment rows, or None when the table is absent."""
    try:
        with get_db_connection() as connection:
            return pd.read_sql(
                _ADJUSTMENTS_SQL,
                connection,
                params=(league_id, season_id))
    except (MySQLError, PandasDatabaseError) as exc:
        if _is_missing_adjustments_table(exc):
            logger.warning(
                "football_point_adjustments is missing for "
                "league_id=%s season_id=%s",
                league_id,
                season_id)
            return None
        raise


def _is_missing_adjustments_table(exc: BaseException) -> bool:
    """True when this error says the adjustments table is absent."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if _MISSING_ADJUSTMENTS_TABLE.search(str(current)):
            return True
        current = current.__cause__
    return False


def _aggregate_adjustments(
        frame: pd.DataFrame) -> dict[int, PointAdjustment]:
    """Sum deltas and join reasons in id order, one row per team."""
    # Kolejność powodów jest po id, nie po kolejności wierszy ramki.
    ordered = frame.sort_values("id")
    totals: dict[int, int] = {}
    reasons: dict[int, list[str]] = {}
    for _, row in ordered.iterrows():
        team_id = int(row["team_id"])
        totals[team_id] = totals.get(team_id, 0) + int(row["points_delta"])
        reasons.setdefault(team_id, []).append(str(row["reason"]))
    adjustments: dict[int, PointAdjustment] = {}
    for team_id, points_delta in totals.items():
        adjustments[team_id] = PointAdjustment(
            team_id=team_id,
            points_delta=points_delta,
            reason="; ".join(reasons[team_id]))
    return adjustments
