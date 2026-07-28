"""Parameterized SQL for model statistics maintenance.

Reads settlement candidates and bet-generation rows, and writes outcomes
and generated bets without interpolating user values into SQL text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from typing import cast

from backend.database import get_db_connection
from backend.sports.football.outcome_evaluator import BET_MARKET_EVENT_IDS
from backend.sports.football.outcome_evaluator import EventFamily
from backend.sports.football.outcome_evaluator import SettlementCandidate
from backend.sports.football.outcome_evaluator import SettlementTarget


SUPPORTED_FINAL_FAMILIES = (
    "REZULTAT",
    "BTTS",
    "OU",
    "GOALS",
    "EXACT")
_BET_MARKET_EVENT_ID_LIST = tuple(sorted(BET_MARKET_EVENT_IDS))
_FINISHED_RESULTS = ("1", "X", "2")

_EVENT_FAMILY_JOIN = """
    INNER JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one ON e.id = efm_one.event_id
    INNER JOIN event_families ef ON efm_one.event_family_id = ef.id
"""

_UPSERT_GENERATED_BET_SQL = """
INSERT INTO bets (
    match_id, event_id, odds, bookmaker, EV, model_id, custom_bet)
VALUES (%s, %s, %s, %s, %s, %s, 0)
ON DUPLICATE KEY UPDATE
    odds = VALUES(odds),
    bookmaker = VALUES(bookmaker),
    EV = VALUES(EV)
"""

_UPDATE_FINAL_OUTCOME_SQL = """
UPDATE final_predictions
SET outcome = %s
WHERE ID = %s
  AND outcome IS NULL
"""

_UPDATE_BET_OUTCOME_SQL = """
UPDATE bets
SET outcome = %s
WHERE id = %s
  AND outcome IS NULL
"""


@dataclass(frozen=True)
class BetGenerationScope:
    """Optional filters for automatic bet generation candidates.

    Validates that date bounds are ordered and not internally inconsistent.
    By default only unfinished matches are eligible; set ``backfill=True``
    (with at least one scope filter) to include finished matches.
    """

    league_id: int | None = None
    season_id: int | None = None
    match_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    backfill: bool = False

    def __post_init__(self) -> None:
        if (
                self.date_from is not None
                and self.date_to is not None
                and self.date_to < self.date_from):
            raise ValueError("date_to must be >= date_from")
        if self.backfill and not self.has_scope_filter():
            raise ValueError(
                "backfill requires at least one bet-generation scope filter "
                "(--league-id, --season-id, --match-id, --date-from, "
                "--date-to)")

    def has_scope_filter(self) -> bool:
        """Return whether any bet-generation scope filter is set."""
        return any([
            self.league_id is not None,
            self.season_id is not None,
            self.match_id is not None,
            self.date_from is not None,
            self.date_to is not None,
        ])


@dataclass(frozen=True)
class GeneratedBet:
    """One automatic model bet candidate or write-ready upsert row.

    ``probability`` is ``predictions.value`` on the 0–100 scale.
    ``ev`` is filled by the service via ``compute_bet_ev`` before write;
    repository mapping leaves it at ``0.0`` as a placeholder.
    """

    match_id: int
    event_id: int
    model_id: int
    bookmaker_id: int
    odds: float
    probability: float
    ev: float = 0.0


def fetch_pending_final_predictions(
        after_id: int,
        limit: int,
        scope: BetGenerationScope | None = None
) -> list[SettlementCandidate]:
    """Fetch pending final predictions for finished matches (keyset)."""
    if limit <= 0:
        return []
    family_placeholders = ", ".join(["%s"] * len(SUPPORTED_FINAL_FAMILIES))
    result_placeholders = ", ".join(["%s"] * len(_FINISHED_RESULTS))
    conditions = [
        "fp.outcome IS NULL",
        "fp.ID > %s",
        f"m.result IN ({result_placeholders})",
        f"ef.name IN ({family_placeholders})"]
    params: list[object] = [
        after_id,
        *_FINISHED_RESULTS,
        *SUPPORTED_FINAL_FAMILIES]
    if scope is not None:
        _append_scope_filters(scope, conditions, params)
    query = f"""
        SELECT
            fp.ID AS record_id,
            m.id AS match_id,
            p.event_id,
            e.name AS event_name,
            ef.name AS family,
            m.result,
            m.home_team_goals AS home_goals,
            m.away_team_goals AS away_goals
        FROM final_predictions fp
        JOIN predictions p ON p.id = fp.predictions_id
        JOIN matches m ON m.id = p.match_id
        JOIN events e ON e.id = p.event_id
        {_EVENT_FAMILY_JOIN}
        WHERE {" AND ".join(conditions)}
        ORDER BY fp.ID ASC
        LIMIT %s
    """
    params.append(limit)
    rows = _fetch_dicts(query, tuple(params))
    return [
        _to_settlement_candidate(row, "final_prediction")
        for row in rows]


def fetch_pending_bets(
        after_id: int,
        limit: int,
        scope: BetGenerationScope | None = None
) -> list[SettlementCandidate]:
    """Fetch pending bets only for priced settlement markets (keyset)."""
    if limit <= 0:
        return []
    event_placeholders = ", ".join(
        ["%s"] * len(_BET_MARKET_EVENT_ID_LIST))
    result_placeholders = ", ".join(["%s"] * len(_FINISHED_RESULTS))
    conditions = [
        "b.outcome IS NULL",
        "b.id > %s",
        f"b.event_id IN ({event_placeholders})",
        f"m.result IN ({result_placeholders})"]
    params: list[object] = [
        after_id,
        *_BET_MARKET_EVENT_ID_LIST,
        *_FINISHED_RESULTS]
    if scope is not None:
        _append_scope_filters(scope, conditions, params)
    query = f"""
        SELECT
            b.id AS record_id,
            m.id AS match_id,
            b.event_id,
            e.name AS event_name,
            ef.name AS family,
            m.result,
            m.home_team_goals AS home_goals,
            m.away_team_goals AS away_goals
        FROM bets b
        JOIN matches m ON m.id = b.match_id
        JOIN events e ON e.id = b.event_id
        {_EVENT_FAMILY_JOIN}
        WHERE {" AND ".join(conditions)}
        ORDER BY b.id ASC
        LIMIT %s
    """
    params.append(limit)
    rows = _fetch_dicts(query, tuple(params))
    return [
        _to_settlement_candidate(row, "bet")
        for row in rows]


def fetch_bet_generation_candidates(
        scope: BetGenerationScope
) -> list[GeneratedBet]:
    """Return automatic bet candidates for active finals with best odds.

    Best bookmaker odds are chosen deterministically: highest odds, then
    lowest ``odds.id`` as a tie-breaker. EV is left at ``0.0``; the service
    computes it via ``compute_bet_ev`` before write.
    """
    event_placeholders = ", ".join(
        ["%s"] * len(_BET_MARKET_EVENT_ID_LIST))
    result_placeholders = ", ".join(["%s"] * len(_FINISHED_RESULTS))
    conditions = [
        "ml.active = 1",
        f"p.event_id IN ({event_placeholders})"]
    params: list[object] = list(_BET_MARKET_EVENT_ID_LIST)
    if not scope.backfill:
        conditions.append(
            f"(m.result IS NULL OR m.result NOT IN ({result_placeholders}))")
        params.extend(_FINISHED_RESULTS)
    _append_scope_filters(scope, conditions, params)

    query = f"""
        WITH best_odds AS (
            SELECT
                o.match_id,
                o.event AS event_id,
                o.odds,
                o.bookmaker AS bookmaker_id,
                ROW_NUMBER() OVER (
                    PARTITION BY o.match_id, o.event
                    ORDER BY o.odds DESC, o.id ASC
                ) AS rn
            FROM odds o
            WHERE o.odds IS NOT NULL
              AND o.odds > 0
        )
        SELECT
            p.match_id,
            p.event_id,
            p.model_id,
            bo.bookmaker_id,
            bo.odds,
            p.value AS probability
        FROM final_predictions fp
        JOIN predictions p ON p.id = fp.predictions_id
        JOIN matches m ON m.id = p.match_id
        JOIN models ml ON ml.id = p.model_id
        JOIN best_odds bo ON (
            bo.match_id = p.match_id
            AND bo.event_id = p.event_id
            AND bo.rn = 1)
        WHERE {" AND ".join(conditions)}
        ORDER BY p.match_id ASC, p.event_id ASC, p.model_id ASC
    """
    rows = _fetch_dicts(query, tuple(params))
    return [_to_generated_bet(row) for row in rows]


def write_generated_bets(
        rows: list[GeneratedBet],
        conn: Any
) -> int:
    """Upsert odds and EV for model bets; never clear an existing outcome."""
    if not rows:
        return 0
    cursor = conn.cursor()
    try:
        cursor.executemany(
            _UPSERT_GENERATED_BET_SQL,
            [
                (
                    row.match_id,
                    row.event_id,
                    row.odds,
                    row.bookmaker_id,
                    row.ev,
                    row.model_id)
                for row in rows])
        return len(rows)
    finally:
        cursor.close()


def write_final_prediction_outcomes(
        rows: list[tuple[int, int]],
        conn: Any
) -> int:
    """Set final_predictions.outcome only while it is still NULL.

    Each row is ``(record_id, outcome)``.
    """
    return _write_outcomes(rows, conn, _UPDATE_FINAL_OUTCOME_SQL)


def write_bet_outcomes(
        rows: list[tuple[int, int]],
        conn: Any
) -> int:
    """Set bets.outcome only while it is still NULL.

    Each row is ``(record_id, outcome)``.
    """
    return _write_outcomes(rows, conn, _UPDATE_BET_OUTCOME_SQL)


def _write_outcomes(
        rows: list[tuple[int, int]],
        conn: Any,
        sql: str
) -> int:
    """Apply pending outcome updates and return rows actually changed."""
    if not rows:
        return 0
    cursor = conn.cursor()
    updated = 0
    try:
        for record_id, outcome in rows:
            cursor.execute(sql, (outcome, record_id))
            updated += int(cursor.rowcount or 0)
        return updated
    finally:
        cursor.close()


def _append_scope_filters(
        scope: BetGenerationScope,
        conditions: list[str],
        params: list[object]
) -> None:
    """Append optional league/season/match/date filters to a WHERE clause."""
    if scope.league_id is not None:
        conditions.append("m.league = %s")
        params.append(scope.league_id)
    if scope.season_id is not None:
        conditions.append("m.season = %s")
        params.append(scope.season_id)
    if scope.match_id is not None:
        conditions.append("m.id = %s")
        params.append(scope.match_id)
    if scope.date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(scope.date_from)
    if scope.date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(scope.date_to)


def _fetch_dicts(
        query: str,
        params: tuple[object, ...]
) -> list[dict[str, Any]]:
    """Execute a read query and return dictionary rows."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall() or []
            return [dict(row) for row in rows]
        finally:
            cursor.close()


def _to_settlement_candidate(
        row: dict[str, Any],
        target: SettlementTarget
) -> SettlementCandidate:
    """Map a SQL dictionary row to a settlement candidate."""
    family_name = str(row["family"])
    if family_name not in SUPPORTED_FINAL_FAMILIES:
        raise ValueError(
            f"Unsupported event family from database: {family_name}")
    return SettlementCandidate(
        record_id=int(row["record_id"]),
        target=target,
        event_id=int(row["event_id"]),
        event_name=str(row["event_name"]),
        family=cast(EventFamily, family_name),
        result=str(row["result"]),
        home_goals=_optional_int(row.get("home_goals")),
        away_goals=_optional_int(row.get("away_goals")),
        match_id=_optional_int(row.get("match_id")))


def _to_generated_bet(row: dict[str, Any]) -> GeneratedBet:
    """Map a SQL dictionary row to a bet-generation candidate."""
    return GeneratedBet(
        match_id=int(row["match_id"]),
        event_id=int(row["event_id"]),
        model_id=int(row["model_id"]),
        bookmaker_id=int(row["bookmaker_id"]),
        odds=float(row["odds"]),
        probability=float(row["probability"]))


def _optional_int(value: Any) -> int | None:
    """Convert a nullable SQL value to ``int`` or ``None``."""
    if value is None:
        return None
    return int(value)
