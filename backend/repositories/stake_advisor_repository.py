"""Read-only model probabilities, verdicts and the agent flag."""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.database import get_db_connection
from backend.repositories.coupon_agent_repository import (
    ready_model_fingerprint)
from backend.timezone import WARSAW_TIME_ZONE


logger = logging.getLogger(__name__)
_WARSAW = ZoneInfo(WARSAW_TIME_ZONE)

_PUBLISHED_SQL = """
    SELECT
        p.id AS prediction_id,
        p.value AS value
    FROM final_predictions fp
    INNER JOIN predictions p
        ON p.id = fp.predictions_id
    WHERE p.match_id = %s
        AND p.event_id = %s
"""

_VERDICT_SQL = """
    SELECT
        br.prediction_id AS prediction_id,
        br.odds_id AS odds_id,
        br.decision AS decision,
        br.calibrated_probability AS calibrated_probability,
        o.match_id AS match_id,
        o.event AS event_id,
        o.bookmaker AS bookmaker_id,
        o.odds AS odds
    FROM betting_recommendations br
    INNER JOIN odds o
        ON o.id = br.odds_id
    WHERE br.model_fingerprint = %s
        AND br.prediction_id IN ({placeholders})
"""

# Otwarty kupon zostaje sygnałem także po 14 dniach. Czas jest na
# kuponie: tipster_coupon_legs nie ma created_at.
_AGENT_SQL = """
    SELECT 1
    FROM tipster_coupon_legs l
    INNER JOIN tipster_coupons c
        ON c.id = l.coupon_id
    INNER JOIN users u
        ON u.id = c.user_id
    INNER JOIN tipster_coupon_leg_events e
        ON e.leg_id = l.id
    WHERE l.match_id = %s
        AND u.is_system = 1
        AND e.event_id IN ({placeholders})
        AND (
            c.settled = 0
            OR c.created_at >= %s
        )
    LIMIT 1
"""


def current_fingerprint() -> str | None:
    """Return the ready EB-18 digest, or None for the baseline pool.

    Uses the coupon-agent gate. A failed report, a missing file or a
    bad JSON body stays on published predictions. The model file is
    not opened and ``allow_unready`` is not set.
    """
    try:
        return ready_model_fingerprint()
    except (OSError, UnicodeError, ValueError, TypeError):
        logger.warning(
            "Stake advisor could not read the betting artifact; "
            "using published predictions")
        return None


def fetch_published_probabilities(
        match_id: int,
        event_id: int) -> list[dict[str, Any]]:
    """Return published prediction percents for one match event.

    ``value`` is the stored 0–100 percent. An empty list means nothing
    was published for the pair.
    """
    rows = _fetch_all(_PUBLISHED_SQL, (match_id, event_id))
    return _map_rows(rows, _probability_row)


def fetch_verdicts(
        prediction_ids: list[int],
        fingerprint: str) -> list[dict[str, Any]]:
    """Return verdicts for one artifact digest, any decision.

    ``calibrated_probability`` stays on the unit scale. The joined
    odds row is the price the meta-model scored. An empty id list
    does not touch the database.
    """
    if not prediction_ids:
        return []
    placeholders = _placeholders(len(prediction_ids))
    query = _VERDICT_SQL.format(placeholders=placeholders)
    params = (fingerprint, *prediction_ids)
    rows = _fetch_all(query, params)
    return _map_rows(rows, _verdict_row)


def agent_liked(
        match_id: int,
        event_ids: list[int],
        days: int = 14,
        now: datetime | None = None) -> bool:
    """Return whether a system account played one of these events.

    An open coupon counts at any age. A settled coupon counts only
    when ``tipster_coupons.created_at`` falls inside ``days``. ``now``
    is naive Warsaw wall time; the default is the process clock.
    """
    _require_days(days)
    if not event_ids:
        return False
    clock = _require_clock(now)
    cutoff = clock - timedelta(days=days)
    placeholders = _placeholders(len(event_ids))
    query = _AGENT_SQL.format(placeholders=placeholders)
    params = (match_id, *event_ids, cutoff)
    return _fetch_one(query, params) is not None


def _require_days(days: int) -> None:
    """Reject a lookback that is not a positive day count."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer")


def _require_clock(now: datetime | None) -> datetime:
    """Return a naive Warsaw clock reading."""
    if now is None:
        return _warsaw_now()
    if not isinstance(now, datetime) or now.tzinfo is not None:
        raise ValueError("now must be naive Warsaw wall time")
    return now


def _warsaw_now() -> datetime:
    """Return the process clock as naive Warsaw wall time."""
    return datetime.now(_WARSAW).replace(tzinfo=None)


def _placeholders(count: int) -> str:
    """Return a comma-separated list of SQL placeholders."""
    return ", ".join("%s" for _ in range(count))


def _map_rows(
        rows: list[dict[str, Any]],
        mapper: Any) -> list[dict[str, Any]]:
    """Keep rows the mapper accepts and drop a broken cell."""
    mapped: list[dict[str, Any]] = []
    for row in rows:
        item = mapper(row)
        if item is not None:
            mapped.append(item)
    return mapped


def _probability_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map one published prediction, or None when a cell is blank."""
    try:
        return {
            "prediction_id": int(row["prediction_id"]),
            "value": float(row["value"])
        }
    except (KeyError, TypeError, ValueError):
        return None


def _verdict_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map one verdict and its odds row onto floats."""
    try:
        return {
            "prediction_id": int(row["prediction_id"]),
            "odds_id": int(row["odds_id"]),
            "decision": str(row["decision"]),
            "calibrated_probability": float(
                row["calibrated_probability"]),
            "match_id": int(row["match_id"]),
            "event_id": int(row["event_id"]),
            "bookmaker_id": int(row["bookmaker_id"]),
            "odds": float(row["odds"])
        }
    except (KeyError, TypeError, ValueError):
        return None


def _fetch_all(
        query: str,
        params: tuple[object, ...]) -> list[dict[str, Any]]:
    """Run one SELECT and return every row."""
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall() or []
        finally:
            cursor.close()
    return [dict(row) for row in rows]


def _fetch_one(
        query: str,
        params: tuple[object, ...]) -> dict[str, Any] | None:
    """Run one SELECT and return the first row, if any."""
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return None
    return dict(row)
