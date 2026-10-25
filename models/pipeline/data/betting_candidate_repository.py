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


_SETTLEMENT_COLUMNS = (
    "result",
    "home_team_goals",
    "away_team_goals",
    "event_name")
_ID_CHUNK = 500
_MATCH_SETTLEMENT_SQL = """
SELECT
    m.id AS match_id,
    m.result AS result,
    m.home_team_goals AS home_team_goals,
    m.away_team_goals AS away_team_goals
FROM matches m
WHERE m.id IN ({placeholders})
"""
_EVENT_NAME_SQL = """
SELECT
    e.id AS event_id,
    e.name AS event_name
FROM events e
WHERE e.id IN ({placeholders})
"""


def attach_settlement_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the match score and the event name to candidate rows.

    The label builder needs ``result``, both goal columns and
    ``events.name``. Those values are not on the prediction-odds pair.
    An empty frame does not open a connection. The statements are
    SELECT only.
    """
    _require_candidate_frame(frame)
    attached = frame.copy()
    if attached.empty:
        return _with_empty_settlement(attached)
    matches = _lookup_rows(
        _MATCH_SETTLEMENT_SQL,
        _positive_ids(attached["match_id"]),
        "match_id")
    events = _lookup_rows(
        _EVENT_NAME_SQL,
        _positive_ids(attached["event_id"]),
        "event_id")
    attached["result"] = _mapped(
        attached["match_id"], matches, "match_id", "result")
    attached["home_team_goals"] = _mapped(
        attached["match_id"], matches, "match_id", "home_team_goals")
    attached["away_team_goals"] = _mapped(
        attached["match_id"], matches, "match_id", "away_team_goals")
    attached["event_name"] = _mapped(
        attached["event_id"], events, "event_id", "event_name")
    logger.info(
        "Attached settlement columns for %s betting candidates",
        len(attached))
    return attached


def _require_candidate_frame(frame: pd.DataFrame) -> None:
    """Reject a frame that is not the candidate contract."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("candidates must be a DataFrame")
    missing = [
        name for name in BETTING_CANDIDATE_COLUMNS
        if name not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"candidates are missing columns: {joined}")
    if frame.index.has_duplicates:
        raise ValueError("candidate index must be unique")


def _with_empty_settlement(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the settlement columns without reading the database."""
    attached = frame.copy()
    for name in _SETTLEMENT_COLUMNS:
        attached[name] = pd.Series(index=attached.index, dtype="object")
    return attached


def _lookup_rows(
        sql: str,
        ids: list[int],
        key: str) -> pd.DataFrame:
    """SELECT rows for one id column, in chunks."""
    if not ids:
        return pd.DataFrame(columns=[key])
    frames = [
        _read_sql(
            sql.format(placeholders=_placeholders(chunk)),
            tuple(chunk))
        for chunk in _chunks(ids)]
    if not frames:
        return pd.DataFrame(columns=[key])
    return pd.concat(frames, ignore_index=True)


def _mapped(
        keys: pd.Series,
        table: pd.DataFrame,
        key_name: str,
        column: str) -> pd.Series:
    """Map a lookup column onto ``keys``, leaving gaps empty."""
    if table.empty or column not in table.columns or key_name not in table:
        return pd.Series([None] * len(keys), index=keys.index, dtype="object")
    unique = _first_by_key(table, key_name)
    lookup = {
        int(key): value
        for key, value in zip(
            unique[key_name].tolist(),
            unique[column].tolist())
        if not _missing_cell(key)}
    mapped = [
        None if _missing_cell(key) else lookup.get(int(key))
        for key in keys.tolist()]
    return pd.Series(mapped, index=keys.index, dtype="object")


def _first_by_key(table: pd.DataFrame, key_name: str) -> pd.DataFrame:
    """Keep the first row for each key."""
    seen: set[int] = set()
    labels: list[object] = []
    for label, key in zip(table.index.tolist(), table[key_name].tolist()):
        if _missing_cell(key):
            continue
        number = int(key)
        if number in seen:
            continue
        seen.add(number)
        labels.append(label)
    return table.loc[labels]


def _positive_ids(values: pd.Series) -> list[int]:
    """Return unique positive ids in first-seen order."""
    ordered: list[int] = []
    seen: set[int] = set()
    for value in values.tolist():
        if _missing_cell(value):
            continue
        number = int(value)
        if number <= 0 or number in seen:
            continue
        seen.add(number)
        ordered.append(number)
    return ordered


def _chunks(ids: list[int]) -> list[list[int]]:
    """Split ids so one IN list stays within the chunk size."""
    return [
        ids[start:start + _ID_CHUNK]
        for start in range(0, len(ids), _ID_CHUNK)]


def _placeholders(ids: list[int]) -> str:
    """Return one ``%s`` per id. The ids themselves stay parameters."""
    if not ids:
        raise ValueError("id chunk must not be empty")
    return ", ".join(["%s"] * len(ids))


def _missing_cell(value: object) -> bool:
    """Return whether a cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
