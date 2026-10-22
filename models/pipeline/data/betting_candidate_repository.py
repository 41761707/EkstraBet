"""Read existing prediction-odds pairs for the betting meta-model."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from backend.database import get_db_connection
from models.pipeline.betting.config import BettingStrategyConfig

logger = logging.getLogger(__name__)

BETTING_CANDIDATE_COLUMNS = (
    "prediction_id",
    "odds_id",
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "kickoff",
    "value_pct",
    "odds")


def fetch_candidates(
        as_of_at: datetime,
        horizon_end: datetime,
        filters: BettingStrategyConfig) -> pd.DataFrame:
    """Return one stored prediction joined to one stored odds row.

    Kickoff is ``matches.game_date`` in the half-open window
    ``[as_of_at, horizon_end)``. Several bookmakers collapse to the
    highest price, then the lowest odds id. The statement is one
    SELECT. ``filters`` supplies the football sport name and the
    excluded model names. The probability threshold is not applied.
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
    frame = _read_sql(query, params)
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
    # Nazwa sportu i wykluczone modele są parametrami, nie stałą listą.
    # Cena <= 1 nie bierze udziału w rankingu.
    return f"""
        WITH window_matches AS (
            SELECT
                mk.id,
                mk.game_date
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
            wm.game_date AS kickoff,
            p.value AS value_pct,
            bo.odds AS odds
        FROM predictions p
        INNER JOIN window_matches wm
            ON wm.id = p.match_id
        INNER JOIN (
            SELECT
                ranked.id,
                ranked.match_id,
                ranked.event_id,
                ranked.bookmaker_id,
                ranked.odds
            FROM (
                SELECT
                    o.id,
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


def _excluded_placeholders(count: int) -> str:
    """Return one ``%s`` placeholder per excluded model name."""
    if count < 1:
        raise ValueError("excluded_model_names must not be empty")
    return ", ".join(["%s"] * count)


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    """Run one SELECT and return its rows."""
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)
