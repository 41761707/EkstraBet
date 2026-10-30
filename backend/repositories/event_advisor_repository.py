"""Read-only coupon history and the future football event pool."""

from __future__ import annotations

import math
from collections.abc import Callable
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from backend.database import get_db_connection
from backend.repositories.tipster_repository import FOOTBALL_SPORT_ID
from backend.repositories.tipster_repository import _FINISHED_RESULTS
from backend.services.probability_service import to_unit_probability
from backend.services.tipster_service import MIN_ODDS
from backend.sports.football.event_settlement_registry import (
    is_settleable_event)


# Ten sam predykat co katalog: wynik '0' to mecz bez rezultatu, zostaje.
_MATCH_WINDOW = """
        SELECT
            mk.id,
            mk.game_date,
            mk.league,
            mk.home_team,
            mk.away_team
        FROM matches mk
        WHERE mk.game_date >= %s
            AND mk.game_date < %s
            AND mk.sport_id = %s
            AND (
                mk.result IS NULL
                OR mk.result NOT IN (%s, %s, %s)
            )"""

# Indeks (user_id, created_at). Otwarty kupon też jest gustem.
# Licznik eventów na nodze: kurs combined nie jest ceną jednego typu.
_HISTORY_SQL = """
    SELECT
        m.league AS league_id,
        e.event_id AS event_id,
        l.odds AS odds,
        COUNT(*) OVER (PARTITION BY l.id) AS event_count_on_leg
    FROM tipster_coupons c
    INNER JOIN tipster_coupon_legs l
        ON l.coupon_id = c.id
    INNER JOIN tipster_coupon_leg_events e
        ON e.leg_id = l.id
    INNER JOIN matches m
        ON m.id = l.match_id
    WHERE c.user_id = %s
        AND c.created_at >= %s
    ORDER BY c.id, l.id, e.id
"""

_SLIP_SQL = """
    SELECT
        m.id AS match_id,
        m.league AS league_id
    FROM matches m
    WHERE m.id IN ({placeholders})
"""

# Próg katalogu (1.01), nie próg nogi agenta. Średnia opublikowanych
# modeli; nazwy ligi i drużyn jak w pickerze.
_CANDIDATE_SQL = """
    WITH window_matches AS (
{window}
    ),
    best_odds AS (
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
            WHERE o.odds IS NOT NULL
                AND o.odds >= %s
        ) ranked
        WHERE ranked.rn = 1
    ),
    published AS (
        SELECT
            p.match_id AS match_id,
            p.event_id AS event_id,
            AVG(p.value) AS probability_pct
        FROM final_predictions fp
        INNER JOIN predictions p
            ON p.id = fp.predictions_id
        INNER JOIN window_matches wm_pub
            ON wm_pub.id = p.match_id
        GROUP BY p.match_id, p.event_id
    )
    SELECT
        pub.match_id AS match_id,
        pub.event_id AS event_id,
        e.name AS event_name,
        wm.league AS league_id,
        l.name AS league_name,
        t1.name AS home_name,
        t2.name AS away_name,
        wm.game_date AS kickoff,
        bo.odds AS odds,
        bo.bookmaker_id AS bookmaker_id,
        pub.probability_pct AS probability_pct
    FROM published pub
    INNER JOIN best_odds bo
        ON bo.match_id = pub.match_id
        AND bo.event_id = pub.event_id
    INNER JOIN window_matches wm
        ON wm.id = pub.match_id
    INNER JOIN events e
        ON e.id = pub.event_id
    INNER JOIN leagues l
        ON l.id = wm.league
    INNER JOIN teams t1
        ON t1.id = wm.home_team
    INNER JOIN teams t2
        ON t2.id = wm.away_team
    ORDER BY wm.game_date, pub.match_id, pub.event_id
""".format(window=_MATCH_WINDOW)

# Flaga bet jest parą mecz+zdarzenie, nie wierszem kursu z werdyktu.
_BET_PAIRS_SQL = """
    WITH window_matches AS (
{window}
    )
    SELECT DISTINCT
        p.match_id AS match_id,
        p.event_id AS event_id
    FROM betting_recommendations br
    INNER JOIN predictions p
        ON p.id = br.prediction_id
    INNER JOIN window_matches wm
        ON wm.id = p.match_id
    WHERE br.decision = %s
        AND br.model_fingerprint = %s
""".format(window=_MATCH_WINDOW)


def fetch_history(
        user_id: int,
        since: datetime) -> list[dict[str, Any]]:
    """Return one row per event on this user's coupons since ``since``.

    Keys are ``league_id``, ``event_id``, ``odds`` and
    ``event_count_on_leg``. A combined leg repeats the leg price on
    every event and sets the count above 1. A blank cell is omitted.
    An empty history is an empty list.
    """
    rows = _fetch_all(_HISTORY_SQL, (user_id, since))
    return _mapped(rows, _history_row)


def fetch_slip_leagues(match_ids: Sequence[int]) -> dict[int, int]:
    """Return ``match_id`` to ``matches.league`` for ids that exist.

    A missing match or a null league is absent, so it cannot boost a
    league. An empty id list does not open a connection.
    """
    unique = _unique_ids(match_ids)
    if not unique:
        return {}
    query = _SLIP_SQL.format(placeholders=_placeholders(len(unique)))
    rows = _fetch_all(query, tuple(unique))
    return _slip_leagues(rows)


def fetch_candidates(
        now: datetime,
        horizon_end: datetime) -> list[dict[str, Any]]:
    """Return future settleable football pairs in ``[now, horizon_end)``.

    Each row is the best catalog price for a published match and
    event. ``model_probability`` is the mean of published
    ``predictions.value`` on the unit scale. Keys match the scoring
    candidate except ``has_computer_bet``, which the service joins
    from ``fetch_computer_bet_pairs``. An unsettleable name is omitted
    here, the same registry as the coupon catalog.
    """
    params = _window_params(now, horizon_end) + (MIN_ODDS,)
    rows = _fetch_all(_CANDIDATE_SQL, params)
    return _mapped(rows, _candidate_row)


def fetch_computer_bet_pairs(
        fingerprint: str,
        now: datetime,
        horizon_end: datetime) -> set[tuple[int, int]]:
    """Return pairs with ``decision = bet`` for one artifact digest.

    The window matches ``fetch_candidates``. The model file is not
    opened and the selector is not called.
    """
    params = _window_params(now, horizon_end) + ("bet", fingerprint)
    rows = _fetch_all(_BET_PAIRS_SQL, params)
    pairs: set[tuple[int, int]] = set()
    for row in rows:
        pair = _bet_pair(row)
        if pair is not None:
            pairs.add(pair)
    return pairs


def _window_params(
        now: datetime,
        horizon_end: datetime) -> tuple[object, ...]:
    """Return the shared football window parameters, in SQL order."""
    return (
        now,
        horizon_end,
        FOOTBALL_SPORT_ID,
        *_FINISHED_RESULTS)


def _unique_ids(match_ids: Sequence[int]) -> list[int]:
    """Keep the first occurrence of each match id."""
    unique: dict[int, None] = {}
    for match_id in match_ids:
        unique.setdefault(match_id, None)
    return list(unique)


def _placeholders(count: int) -> str:
    """Return a comma-separated list of SQL placeholders."""
    return ", ".join("%s" for _ in range(count))


def _slip_leagues(rows: list[dict[str, Any]]) -> dict[int, int]:
    """Map match id to league id, skipping a blank cell."""
    leagues: dict[int, int] = {}
    for row in rows:
        match_id = _optional_int(row.get("match_id"))
        league_id = _optional_int(row.get("league_id"))
        if match_id is None or league_id is None:
            continue
        leagues[match_id] = league_id
    return leagues


def _mapped(
        rows: list[dict[str, Any]],
        mapper: Callable[
            [dict[str, Any]],
            dict[str, Any] | None]) -> list[dict[str, Any]]:
    """Keep rows the mapper accepts and skip a broken cell."""
    mapped: list[dict[str, Any]] = []
    for row in rows:
        item = mapper(row)
        if item is not None:
            mapped.append(item)
    return mapped


def _history_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map one coupon event, or None when a cell is blank."""
    league_id = _optional_int(row.get("league_id"))
    event_id = _optional_int(row.get("event_id"))
    odds = _finite_float(row.get("odds"))
    event_count = _optional_int(row.get("event_count_on_leg"))
    if league_id is None or event_id is None or odds is None:
        return None
    if event_count is None or event_count < 1:
        return None
    return {
        "league_id": league_id,
        "event_id": event_id,
        "odds": odds,
        "event_count_on_leg": event_count}


def _candidate_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Map one pool row, or None when it cannot be suggested."""
    event_id = _optional_int(row.get("event_id"))
    event_name = _required_text(row.get("event_name"))
    if event_id is None or event_name is None:
        return None
    if not is_settleable_event(event_id, event_name):
        return None
    identity = _candidate_identity(row)
    names = _candidate_names(row)
    kickoff = row.get("kickoff")
    if identity is None or names is None or not isinstance(kickoff, datetime):
        return None
    return {
        "match_id": identity["match_id"],
        "event_id": event_id,
        "event_name": event_name,
        "league_id": identity["league_id"],
        "league_name": names["league_name"],
        "home_name": names["home_name"],
        "away_name": names["away_name"],
        "kickoff": kickoff,
        "odds": identity["odds"],
        "bookmaker_id": identity["bookmaker_id"],
        "model_probability": identity["model_probability"]}


def _candidate_identity(
        row: dict[str, Any]) -> dict[str, Any] | None:
    """Return ids, price and unit probability, or None if one is blank."""
    match_id = _optional_int(row.get("match_id"))
    league_id = _optional_int(row.get("league_id"))
    bookmaker_id = _optional_int(row.get("bookmaker_id"))
    odds = _finite_float(row.get("odds"))
    probability = _unit_probability(row.get("probability_pct"))
    if match_id is None or league_id is None or bookmaker_id is None:
        return None
    if odds is None or probability is None:
        return None
    return {
        "match_id": match_id,
        "league_id": league_id,
        "bookmaker_id": bookmaker_id,
        "odds": odds,
        "model_probability": probability}


def _candidate_names(row: dict[str, Any]) -> dict[str, str] | None:
    """Return league and team names, or None when one is blank."""
    league_name = _required_text(row.get("league_name"))
    home_name = _required_text(row.get("home_name"))
    away_name = _required_text(row.get("away_name"))
    if league_name is None or home_name is None or away_name is None:
        return None
    return {
        "league_name": league_name,
        "home_name": home_name,
        "away_name": away_name}


def _bet_pair(row: dict[str, Any]) -> tuple[int, int] | None:
    """Return one match-event pair, or None when an id is blank."""
    match_id = _optional_int(row.get("match_id"))
    event_id = _optional_int(row.get("event_id"))
    if match_id is None or event_id is None:
        return None
    return (match_id, event_id)


def _unit_probability(value: object) -> float | None:
    """Convert a stored percentage average onto the unit scale."""
    number = _finite_float(value)
    if number is None:
        return None
    return to_unit_probability(number)


def _optional_int(value: object) -> int | None:
    """Return an int, or None for a blank or non-numeric cell."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finite_float(value: object) -> float | None:
    """Return a finite float, or None for a blank or non-numeric cell."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _required_text(value: object) -> str | None:
    """Return text, or None when the cell is blank."""
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    return text


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
