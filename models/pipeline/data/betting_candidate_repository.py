"""Read existing prediction-odds pairs for the betting meta-model."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from backend.database import get_db_connection
from backend.sports.football.markets import DEVIG_MARKETS
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.devig import fair_probability

logger = logging.getLogger(__name__)

_FAIR_INPUT_COLUMNS = (
    "implied",
    "implied_sum",
    "priced_outcomes",
    "market_size")
_PASSTHROUGH_COLUMNS = (
    "prediction_id",
    "odds_id",
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "league_id",
    "kickoff",
    "value_pct",
    "odds")
BETTING_CANDIDATE_COLUMNS = _PASSTHROUGH_COLUMNS + ("devig_probability",)
_SQL_FRAME_COLUMNS = _PASSTHROUGH_COLUMNS + _FAIR_INPUT_COLUMNS


def fetch_candidates(
        as_of_at: datetime,
        horizon_end: datetime,
        filters: BettingStrategyConfig) -> pd.DataFrame:
    """Return one stored prediction joined to one stored odds row.

    Kickoff is ``matches.game_date`` in the half-open window
    ``[as_of_at, horizon_end)``. Several bookmakers collapse to the
    highest price, then the lowest odds id. Fair probability is the
    overround of that winning bookmaker's full market, computed before
    the ranking keeps one price. The statement is one SELECT.
    ``filters`` supplies the football sport name and the excluded model
    names. The probability threshold is not applied.
    """
    _require_window(as_of_at, horizon_end)
    excluded = filters.excluded_model_names
    query = _candidate_query(len(excluded))
    # Filtr daty jest w CTE, bo MySQL nie wpycha go do rankingu.
    params = (
        as_of_at,
        horizon_end,
        filters.football_sport_name,
        *excluded)
    frame = _with_fair_probability(_read_sql(query, params))
    logger.info("Fetched %s betting candidates", len(frame))
    return frame


def _require_window(as_of_at: datetime, horizon_end: datetime) -> None:
    """Reject a window that cannot contain a kickoff."""
    if not isinstance(as_of_at, datetime):
        raise ValueError("as_of_at must be a datetime")
    if not isinstance(horizon_end, datetime):
        raise ValueError("horizon_end must be a datetime")
    if as_of_at >= horizon_end:
        raise ValueError("as_of_at must be earlier than horizon_end")


def _candidate_query(excluded_count: int) -> str:
    """Build the read of one best odds row per match and event."""
    placeholders = _excluded_placeholders(excluded_count)
    family_sql = _market_case("name")
    size_sql = _market_case("size")
    # Nazwa sportu i wykluczone modele są parametrami, nie stałą listą.
    # De-vig liczy cały cennik firmy, zanim ranking zostawi jedną cenę.
    # Cena <= 1 nie bierze udziału w rankingu.
    return f"""
        WITH window_matches AS (
            SELECT
                mk.id,
                mk.game_date,
                mk.league
            FROM matches mk
            WHERE mk.game_date >= %s
                AND mk.game_date < %s
        )
        SELECT
            p.id AS prediction_id,
            bo.id AS odds_id,
            p.match_id AS match_id,
            p.event_id AS event_id,
            p.model_id AS model_id,
            bo.bookmaker_id AS bookmaker_id,
            wm.league AS league_id,
            wm.game_date AS kickoff,
            p.value AS value_pct,
            bo.odds AS odds,
            bo.implied AS implied,
            bo.implied_sum AS implied_sum,
            bo.priced_outcomes AS priced_outcomes,
            bo.market_size AS market_size
        FROM predictions p
        INNER JOIN window_matches wm
            ON wm.id = p.match_id
        INNER JOIN (
            SELECT
                ranked.id,
                ranked.match_id,
                ranked.event_id,
                ranked.bookmaker_id,
                ranked.odds,
                ranked.implied,
                ranked.implied_sum,
                ranked.priced_outcomes,
                ranked.market_size
            FROM (
                SELECT
                    o.id,
                    o.match_id,
                    o.event AS event_id,
                    o.bookmaker AS bookmaker_id,
                    o.odds,
                    (1.0 / o.odds) AS implied,
                    {size_sql} AS market_size,
                    COUNT(*) OVER (
                        PARTITION BY o.match_id, o.bookmaker, {family_sql}
                    ) AS priced_outcomes,
                    SUM(1.0 / o.odds) OVER (
                        PARTITION BY o.match_id, o.bookmaker, {family_sql}
                    ) AS implied_sum,
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
        INNER JOIN models md
            ON md.id = p.model_id
        INNER JOIN sports s
            ON s.id = md.sport_id
        WHERE s.name = %s
            AND md.active = 1
            AND md.name NOT IN ({placeholders})
            AND p.value >= 0
            AND p.value <= 100
        ORDER BY
            wm.game_date,
            p.match_id,
            p.event_id,
            p.id
    """


def _market_case(kind: str) -> str:
    """Return a CASE that maps an event id to a family name or a size."""
    branches = []
    for name, event_ids in DEVIG_MARKETS:
        listed = ", ".join(str(event_id) for event_id in sorted(event_ids))
        if kind == "name":
            value = _sql_name(name)
        else:
            value = str(len(event_ids))
        branches.append(f"WHEN o.event IN ({listed}) THEN {value}")
    return "CASE " + " ".join(branches) + " ELSE NULL END"


def _sql_name(name: str) -> str:
    """Quote a catalog name that is already an uppercase token."""
    if not name.isascii() or not name.isalpha() or name != name.upper():
        raise ValueError(f"unsafe market name: {name}")
    return f"'{name}'"


def _with_fair_probability(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach the fair share and hide the bookmaker aggregates."""
    missing = [
        name for name in _SQL_FRAME_COLUMNS
        if name not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"candidate rows are missing columns: {joined}")
    fair = [
        fair_probability(implied, implied_sum, priced, market_size)
        for implied, implied_sum, priced, market_size in _fair_inputs(frame)]
    result = frame.loc[:, list(_PASSTHROUGH_COLUMNS)].copy()
    result["devig_probability"] = pd.Series(
        fair,
        index=frame.index,
        dtype="float64")
    return result.loc[:, list(BETTING_CANDIDATE_COLUMNS)]


def _fair_inputs(
        frame: pd.DataFrame
        ) -> list[tuple[object, object, object, object]]:
    """Return one aggregate tuple per candidate row."""
    implied = frame["implied"].tolist()
    implied_sum = frame["implied_sum"].tolist()
    priced = frame["priced_outcomes"].tolist()
    market_size = frame["market_size"].tolist()
    return list(zip(implied, implied_sum, priced, market_size))


def _excluded_placeholders(count: int) -> str:
    """Return one ``%s`` placeholder per excluded model name."""
    if count < 1:
        raise ValueError("excluded_model_names must not be empty")
    return ", ".join(["%s"] * count)


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    """Run one SELECT and return its rows."""
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)
