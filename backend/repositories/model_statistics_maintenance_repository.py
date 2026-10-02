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
from backend.sports.hockey.markets import HOCKEY_BET_MARKET_EVENT_IDS
from backend.sports.hockey.outcome_evaluator import HockeyEventFamily
from backend.sports.hockey.outcome_evaluator import HockeySettlementCandidate


FOOTBALL_SPORT_ID = 1
HOCKEY_SPORT_ID = 2
_FOOTBALL_FINAL_FAMILIES = ("REZULTAT", "BTTS", "OU", "GOALS", "EXACT")
_HOCKEY_FINAL_FAMILIES = ("HOCKEY_ML", "HOCKEY_OU_55", "HOCKEY_OU_65",
    "HOCKEY_PL_HOME", "HOCKEY_PL_AWAY", "HOCKEY_HOME_TT_25",
    "HOCKEY_HOME_TT_35", "HOCKEY_AWAY_TT_25", "HOCKEY_AWAY_TT_35")
_FOOTBALL_FAMILY_NAMES = frozenset(_FOOTBALL_FINAL_FAMILIES)
_HOCKEY_FAMILY_NAMES = frozenset(_HOCKEY_FINAL_FAMILIES)
SUPPORTED_FINAL_FAMILIES = (
    *_FOOTBALL_FINAL_FAMILIES,
    *_HOCKEY_FINAL_FAMILIES)
_PRICED_BET_EVENT_IDS = BET_MARKET_EVENT_IDS | HOCKEY_BET_MARKET_EVENT_IDS
_BET_MARKET_EVENT_ID_LIST = tuple(sorted(_PRICED_BET_EVENT_IDS))
SettlementRow = SettlementCandidate | HockeySettlementCandidate
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

_HOCKEY_MATCH_ADD_JOIN = """
    LEFT JOIN hockey_matches_add hma ON hma.match_id = m.id
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
) -> list[SettlementRow]:
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
            m.away_team_goals AS away_goals,
            m.sport_id AS sport_id,
            hma.OTwinner AS ot_winner,
            hma.SOwinner AS so_winner
        FROM final_predictions fp
        JOIN predictions p ON p.id = fp.predictions_id
        JOIN matches m ON m.id = p.match_id
        JOIN events e ON e.id = p.event_id
        {_EVENT_FAMILY_JOIN}
        {_HOCKEY_MATCH_ADD_JOIN}
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
) -> list[SettlementRow]:
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
            m.away_team_goals AS away_goals,
            m.sport_id AS sport_id,
            hma.OTwinner AS ot_winner,
            hma.SOwinner AS so_winner
        FROM bets b
        JOIN matches m ON m.id = b.match_id
        JOIN events e ON e.id = b.event_id
        {_EVENT_FAMILY_JOIN}
        {_HOCKEY_MATCH_ADD_JOIN}
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


@dataclass(frozen=True)
class StoredFinalPick:
    """One selected final and the event it currently points at."""

    final_id: int
    prediction_id: int
    event_id: int


_STORED_FINALS_SQL = """
SELECT
    fp.ID AS final_id,
    fp.predictions_id AS prediction_id,
    p.event_id AS event_id
FROM final_predictions fp
INNER JOIN predictions p ON p.id = fp.predictions_id
WHERE p.match_id = %s
  AND p.model_id = %s
"""

_DELETE_FINALS_SQL = """
DELETE FROM final_predictions
WHERE ID IN ({placeholders})
"""

_DELETE_UNSETTLED_BETS_SQL = """
DELETE FROM bets
WHERE match_id = %s
  AND model_id = %s
  AND outcome IS NULL
  AND event_id IN ({placeholders})
"""


def fetch_stored_finals(
        match_id: int,
        model_id: int,
        conn: Any) -> list[StoredFinalPick]:
    """Return the finals currently stored for one match and model."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(_STORED_FINALS_SQL, (int(match_id), int(model_id)))
        rows = cursor.fetchall() or []
    finally:
        cursor.close()
    return [
        StoredFinalPick(
            final_id=int(row["final_id"]),
            prediction_id=int(row["prediction_id"]),
            event_id=int(row["event_id"]))
        for row in rows]


def delete_final_predictions(
        final_ids: list[int],
        conn: Any) -> int:
    """Delete final rows by primary key. Returns the requested count."""
    unique_ids = list(dict.fromkeys(int(item) for item in final_ids))
    if not unique_ids:
        return 0
    placeholders = ", ".join(["%s"] * len(unique_ids))
    sql = _DELETE_FINALS_SQL.format(placeholders=placeholders)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, tuple(unique_ids))
    finally:
        cursor.close()
    return len(unique_ids)


def delete_unsettled_bets(
        match_id: int,
        model_id: int,
        event_ids: list[int],
        conn: Any) -> int:
    """Delete unsettled bets for the given events.

    A bet with ``outcome`` already set stays. Settled rows are not
    part of a pre-match lineup refresh.
    """
    unique_ids = list(dict.fromkeys(int(item) for item in event_ids))
    if not unique_ids:
        return 0
    placeholders = ", ".join(["%s"] * len(unique_ids))
    sql = _DELETE_UNSETTLED_BETS_SQL.format(placeholders=placeholders)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (int(match_id), int(model_id), *unique_ids))
        return int(cursor.rowcount or 0)
    finally:
        cursor.close()


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
) -> SettlementRow:
    """Map a SQL dictionary row to the sport-specific candidate."""
    family_name = str(row["family"])
    _require_supported_family(family_name)
    sport_id = _sport_id_for_row(row, family_name)
    if sport_id == HOCKEY_SPORT_ID:
        return _to_hockey_candidate(row, target, family_name)
    return _to_football_candidate(row, target, family_name)


def _require_supported_family(family_name: str) -> None:
    """Reject a family that settlement does not know how to price."""
    if family_name not in SUPPORTED_FINAL_FAMILIES:
        raise ValueError(
            f"Unsupported event family from database: {family_name}")


def _sport_id_for_row(row: dict[str, Any], family_name: str) -> int:
    """Resolve sport id and check that it matches the event family.

    Missing ``sport_id`` stays football so older fixtures work.
    A hockey family still requires an explicit hockey sport id.
    """
    sport_id = _optional_int(row.get("sport_id"))
    if sport_id is None:
        if family_name in _HOCKEY_FAMILY_NAMES:
            raise ValueError("Hockey family requires matches.sport_id")
        return FOOTBALL_SPORT_ID
    if sport_id == HOCKEY_SPORT_ID:
        if family_name not in _HOCKEY_FAMILY_NAMES:
            raise ValueError(
                f"Hockey sport_id with non-hockey family: {family_name}")
        return sport_id
    if sport_id == FOOTBALL_SPORT_ID:
        if family_name not in _FOOTBALL_FAMILY_NAMES:
            raise ValueError(
                f"Football sport_id with non-football family: {family_name}")
        return sport_id
    raise ValueError(f"Unsupported sport_id from database: {sport_id}")


def _to_football_candidate(
        row: dict[str, Any],
        target: SettlementTarget,
        family_name: str
) -> SettlementCandidate:
    """Map a football SQL row to a football settlement candidate."""
    return SettlementCandidate(
        record_id=int(row["record_id"]),
        target=target,
        event_id=int(row["event_id"]),
        event_name=str(row["event_name"]),
        family=cast(EventFamily, family_name),
        result=str(row["result"]),
        home_goals=_optional_int(row.get("home_goals")),
        away_goals=_optional_int(row.get("away_goals")),
        match_id=_optional_int(row.get("match_id")),
        sport_id=FOOTBALL_SPORT_ID)


def _to_hockey_candidate(
        row: dict[str, Any],
        target: SettlementTarget,
        family_name: str
) -> HockeySettlementCandidate:
    """Map a hockey SQL row, including overtime winner columns."""
    return HockeySettlementCandidate(
        record_id=int(row["record_id"]),
        target=target,
        event_id=int(row["event_id"]),
        event_name=str(row["event_name"]),
        family=cast(HockeyEventFamily, family_name),
        result=str(row["result"]),
        home_goals=_optional_int(row.get("home_goals")),
        away_goals=_optional_int(row.get("away_goals")),
        ot_winner=_optional_int(row.get("ot_winner")),
        so_winner=_optional_int(row.get("so_winner")),
        match_id=_optional_int(row.get("match_id")),
        sport_id=HOCKEY_SPORT_ID)


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
