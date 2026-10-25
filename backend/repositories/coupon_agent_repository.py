"""Future settleable prediction-odds pairs for the coupon agent."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pandas as pd

from backend.database import get_db_connection
from backend.repositories.tipster_repository import FOOTBALL_SPORT_ID
from backend.repositories.tipster_repository import _FINISHED_RESULTS
from backend.services.probability_service import to_unit_probability
from backend.sports.football.event_settlement_registry import (
    is_settleable_event)


MAX_CANDIDATES = 200
_EDGE_POINTS = 100.0
CANDIDATE_COLUMNS = (
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "odds",
    "model_probability",
    "implied_probability",
    "value_edge_pp",
    "kickoff",
    "league_id",
    "league_tier",
    "event_family")
_SQL_COLUMNS = (
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "odds",
    "probability_pct",
    "kickoff",
    "league_id",
    "league_tier",
    "event_name",
    "event_family")
_NULLABLE_COLUMNS = ("league_id", "league_tier", "event_family")

# Katalog kuponu przyjmuje tylko piłkę; inny sport odpada przy zapisie.
# Predykat rezultatu jest ten sam: 1/X/2 nie wchodzi do puli.
# Limit jest po filtrze rejestru, żeby niesettleable nie zjadł slotu.
_CANDIDATE_SQL = """
    WITH window_matches AS (
        SELECT
            mk.id,
            mk.game_date,
            mk.league
        FROM matches mk
        WHERE mk.game_date >= %s
            AND mk.game_date < %s
            AND mk.sport_id = %s
            AND (
                mk.result IS NULL
                OR mk.result NOT IN (%s, %s, %s)
            )
    )
    SELECT
        p.match_id AS match_id,
        p.event_id AS event_id,
        p.model_id AS model_id,
        bo.bookmaker_id AS bookmaker_id,
        bo.odds AS odds,
        p.value AS probability_pct,
        wm.game_date AS kickoff,
        wm.league AS league_id,
        l.tier AS league_tier,
        e.name AS event_name,
        ef.name AS event_family
    FROM final_predictions fp
    INNER JOIN predictions p
        ON p.id = fp.predictions_id
    INNER JOIN window_matches wm
        ON wm.id = p.match_id
    INNER JOIN (
        SELECT
            ranked.match_id,
            ranked.event_id,
            ranked.bookmaker_id,
            ranked.odds
        FROM (
            SELECT
                o.match_id,
                o.event AS event_id,
                o.bookmaker AS bookmaker_id,
                o.odds,
                ROW_NUMBER() OVER (
                    PARTITION BY o.match_id, o.event
                    ORDER BY o.odds DESC, o.id ASC
                ) AS rn
            FROM odds o
            INNER JOIN window_matches wm_odds
                ON wm_odds.id = o.match_id
            WHERE o.odds > 1
        ) ranked
        WHERE ranked.rn = 1
    ) bo
        ON bo.match_id = p.match_id
        AND bo.event_id = p.event_id
    INNER JOIN events e
        ON e.id = p.event_id
    LEFT JOIN leagues l
        ON l.id = wm.league
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one
        ON efm_one.event_id = e.id
    LEFT JOIN event_families ef
        ON ef.id = efm_one.event_family_id
    ORDER BY
        wm.game_date,
        p.match_id,
        p.event_id,
        p.model_id,
        p.id
"""


def fetch_candidates(
        now: datetime,
        horizon_days: int = 7) -> pd.DataFrame:
    """Return settleable published prediction-odds pairs in the window.

    Kickoff is ``matches.game_date`` in the half-open interval
    ``[now, now + horizon_days)``. The window is football only, and a
    final result of 1, X or 2 is omitted, the same rule as the tipster
    catalog. One bookmaker survives per match and event: the highest
    price, then the lowest odds id. Probability is the published
    percentage on the unit scale. Implied probability is ``1 / odds``
    without removing the bookmaker margin. At most ``MAX_CANDIDATES``
    rows are kept, earliest kickoff first. ``event_family`` is the
    catalog family name, not its id.
    """
    horizon_end = _horizon_end(now, horizon_days)
    frame = _read_sql(
        _CANDIDATE_SQL,
        (
            now,
            horizon_end,
            FOOTBALL_SPORT_ID,
            *_FINISHED_RESULTS))
    return _to_candidates(frame)


def _horizon_end(now: datetime, horizon_days: int) -> datetime:
    """Return the exclusive end of a positive day window."""
    if not isinstance(now, datetime):
        raise ValueError("now must be a datetime")
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int):
        raise ValueError("horizon_days must be a positive integer")
    if horizon_days < 1:
        raise ValueError("horizon_days must be a positive integer")
    return now + timedelta(days=horizon_days)


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    """Run one SELECT and return its rows."""
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)


def _to_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep rows the settlement registry and the unit scale accept."""
    _require_sql_columns(frame)
    if frame.empty:
        return _empty_frame()
    records = [
        candidate
        for row in frame.to_dict(orient="records")
        if (candidate := _candidate_or_none(row)) is not None]
    records.sort(key=_sort_key)
    if not records:
        return _empty_frame()
    return _frame_from_records(records[:MAX_CANDIDATES])


def _require_sql_columns(frame: pd.DataFrame) -> None:
    """Reject a read that does not match the candidate SELECT."""
    missing = [
        name for name in _SQL_COLUMNS
        if name not in frame.columns]
    if not missing:
        return
    joined = ", ".join(missing)
    raise ValueError(f"candidate rows are missing columns: {joined}")


def _candidate_or_none(row: dict[str, object]) -> dict[str, object] | None:
    """Map one SQL row, or return None when it cannot be a leg."""
    event_id = _optional_int(row.get("event_id"))
    event_name = _optional_str(row.get("event_name"))
    if event_id is None or event_name is None:
        return None
    if not is_settleable_event(event_id, event_name):
        return None
    probability = _open_unit_probability(row.get("probability_pct"))
    odds = _odds_above_one(row.get("odds"))
    identity = _required_identity(row)
    kickoff = row.get("kickoff")
    if probability is None or odds is None or identity is None:
        return None
    if _is_missing(kickoff):
        return None
    implied = 1.0 / odds
    # implied bez de-vig: marża zostaje w kursie (świadoma decyzja v1)
    return {
        "match_id": identity[0],
        "event_id": event_id,
        "model_id": identity[1],
        "bookmaker_id": identity[2],
        "odds": odds,
        "model_probability": probability,
        "implied_probability": implied,
        "value_edge_pp": (probability - implied) * _EDGE_POINTS,
        "kickoff": kickoff,
        "league_id": _optional_int(row.get("league_id")),
        "league_tier": _optional_int(row.get("league_tier")),
        "event_family": _optional_str(row.get("event_family"))}


def _required_identity(
        row: dict[str, object]) -> tuple[int, int, int] | None:
    """Return match, model and bookmaker ids, or None if one is missing."""
    match_id = _optional_int(row.get("match_id"))
    model_id = _optional_int(row.get("model_id"))
    bookmaker_id = _optional_int(row.get("bookmaker_id"))
    if match_id is None or model_id is None or bookmaker_id is None:
        return None
    return (match_id, model_id, bookmaker_id)


def _sort_key(row: dict[str, object]) -> tuple[object, int, int, int]:
    """Order the pool by kickoff, then by stable ids."""
    return (
        row["kickoff"],
        int(row["match_id"]),
        int(row["event_id"]),
        int(row["model_id"]))


def _open_unit_probability(value: object) -> float | None:
    """Convert a DB percentage and keep only the open unit interval."""
    number = _finite_float(value)
    if number is None:
        return None
    unit = to_unit_probability(number)
    if unit <= 0.0 or unit >= 1.0:
        return None
    return unit


def _odds_above_one(value: object) -> float | None:
    """Keep a price that can be inverted into an implied probability."""
    number = _finite_float(value)
    if number is None or number <= 1.0:
        return None
    return number


def _finite_float(value: object) -> float | None:
    """Return a finite float, or None for a blank or non-numeric value."""
    if isinstance(value, bool) or _is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _optional_int(value: object) -> int | None:
    """Return an int, or None when the SQL value is blank."""
    if isinstance(value, bool) or _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    """Return a stripped string, or None when the SQL value is blank."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _is_missing(value: object) -> bool:
    """Return True for None, NaN, NaT and a blank string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)


def _frame_from_records(records: list[dict[str, object]]) -> pd.DataFrame:
    """Build the public frame and keep nullable fields as None."""
    columns = {
        name: [row[name] for row in records]
        for name in CANDIDATE_COLUMNS}
    frame = pd.DataFrame(columns)
    for name in _NULLABLE_COLUMNS:
        frame[name] = [
            None if _is_missing(value) else value
            for value in frame[name].tolist()]
    return frame.loc[:, list(CANDIDATE_COLUMNS)]


def _empty_frame() -> pd.DataFrame:
    """Return a zero-row frame with the public candidate columns."""
    return pd.DataFrame(columns=list(CANDIDATE_COLUMNS))
