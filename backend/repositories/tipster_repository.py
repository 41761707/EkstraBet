"""SQL queries for tipster bankrolls and coupons keyed by users.id."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.database import get_db_connection
from backend.sports.football.event_settlement_registry import (
    is_settleable_event)


def _net_odds_factor_sql() -> str:
    """Stake fraction left after the Polish betting tax."""
    factor = Decimal("1") - Decimal(str(BETTING_TAX_RATE))
    return format(factor, "f")


def _settled_profit_sql(apply_tax: bool) -> str:
    """Settled profit. A win pays odds on 88% of stake; a loss takes it all."""
    if not apply_tax:
        return "c.profit"
    # wygrana od stawki netto, przegrana od kwoty, którą gracz wpłacił
    factor = _net_odds_factor_sql()
    win = (
        f"ROUND(c.stake_amount * (c.combined_odds * {factor} - 1), 2)")
    return f"IF(c.outcome = 1, {win}, -c.stake_amount)"


def _open_stake_expr() -> str:
    """Stakes locked in coupons that are not settled yet."""
    return """COALESCE((
        SELECT SUM(c.stake_amount)
        FROM tipster_coupons c
        WHERE c.user_id = tb.user_id AND c.settled = 0
    ), 0)"""


def _taxed_balance_expr() -> str:
    """Capital plus taxed settled profit, minus stakes still in play."""
    profit = _settled_profit_sql(True)
    return (
        "tb.initial_capital + COALESCE(("
        f"SELECT SUM({profit}) "
        "FROM tipster_coupons c "
        "WHERE c.user_id = tb.user_id AND c.settled = 1"
        f"), 0) - {_open_stake_expr()}")


def _bankroll_select_sql() -> str:
    """Owner bankroll with profit and balance after the 12% tax."""
    profit = _settled_profit_sql(True)
    balance = _taxed_balance_expr()
    return f"""
    SELECT
        tb.user_id,
        tb.currency,
        tb.initial_capital,
        tb.unit_size,
        {balance} AS current_balance,
        {_open_stake_expr()} AS open_stake,
        COALESCE((
            SELECT SUM({profit})
            FROM tipster_coupons c
            WHERE c.user_id = tb.user_id AND c.settled = 1
        ), 0) AS realized_pnl
    FROM tipster_bankrolls tb
    WHERE tb.user_id = %s
    LIMIT 1
"""


def _coupon_list_columns(apply_tax: bool) -> str:
    """Open rows keep stored NULL profit; settled rows follow the tax view."""
    if not apply_tax:
        return _COUPON_COLUMNS
    taxed = _settled_profit_sql(True)
    listed = f"IF(c.settled = 1, {taxed}, c.profit) AS profit"
    return _COUPON_COLUMNS.replace("profit", listed, 1)


def _performance_facts_sql(apply_tax: bool) -> str:
    """Performance facts; taxed profit replaces the stored column."""
    if not apply_tax:
        return _PERFORMANCE_FACTS_SQL
    taxed = _settled_profit_sql(True)
    return _PERFORMANCE_FACTS_SQL.replace(
        "c.profit,", f"{taxed} AS profit,", 1)


# saldo: kapitał + zysk rozliczony - stawki kuponów, które jeszcze są w grze
_CURRENT_BALANCE_EXPR = f"""
    tb.initial_capital + COALESCE((
        SELECT SUM(c.profit)
        FROM tipster_coupons c
        WHERE c.user_id = tb.user_id AND c.settled = 1
    ), 0) - {_open_stake_expr()}
"""

_BALANCE_COLUMNS = f"""
    tb.user_id,
    tb.currency,
    tb.initial_capital,
    tb.unit_size,
    {_CURRENT_BALANCE_EXPR} AS current_balance,
    {_open_stake_expr()} AS open_stake,
    COALESCE((
        SELECT SUM(c.profit)
        FROM tipster_coupons c
        WHERE c.user_id = tb.user_id AND c.settled = 1
    ), 0) AS realized_pnl
"""

_SELECT_BANKROLL_BY_USER_ID = f"""
    SELECT {_BALANCE_COLUMNS}
    FROM tipster_bankrolls tb
    WHERE tb.user_id = %s
    LIMIT 1
"""

_SELECT_BY_USERNAME = f"""
    SELECT
        u.username,
        u.display_name,
        u.is_system,
        {_BALANCE_COLUMNS}
    FROM users u
    INNER JOIN tipster_bankrolls tb ON tb.user_id = u.id
    WHERE u.username = %s
    LIMIT 1
"""

_UPSERT_BANKROLL = """
    INSERT INTO tipster_bankrolls (
        user_id, currency, initial_capital, unit_size)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        currency = VALUES(currency),
        unit_size = VALUES(unit_size)
"""

_UPDATE_BANKROLL_SETTINGS = """
    UPDATE tipster_bankrolls
    SET currency = %s, unit_size = %s
    WHERE user_id = %s
"""

_ADD_TO_INITIAL_CAPITAL = """
    UPDATE tipster_bankrolls
    SET initial_capital = initial_capital + %s
    WHERE user_id = %s
"""

_INSERT_COUPON = """
    INSERT INTO tipster_coupons (
        user_id, stake_amount, stake_units, stake_input_mode,
        combined_odds)
    VALUES (%s, %s, %s, %s, %s)
"""

_INSERT_LEG = """
    INSERT INTO tipster_coupon_legs (
        coupon_id, match_id, odds, bookmaker_id, source)
    VALUES (%s, %s, %s, %s, %s)
"""

_INSERT_LEG_EVENT = """
    INSERT INTO tipster_coupon_leg_events (leg_id, event_id)
    VALUES (%s, %s)
"""

_COUPON_COLUMNS = """
    id,
    user_id,
    stake_amount,
    stake_units,
    stake_input_mode,
    combined_odds,
    settled,
    outcome,
    profit,
    created_at
"""

_SELECT_COUPON_BY_ID = f"""
    SELECT {_COUPON_COLUMNS}
    FROM tipster_coupons
    WHERE id = %s
    LIMIT 1
"""

_SELECT_LEGS_FOR_COUPONS = """
    SELECT
        l.id AS leg_id,
        l.coupon_id,
        l.match_id,
        l.odds,
        l.bookmaker_id,
        l.source,
        l.outcome,
        e.event_id,
        ev.name AS event_name,
        t1.name AS home_name,
        t2.name AS away_name
    FROM tipster_coupon_legs l
    LEFT JOIN matches m ON m.id = l.match_id
    LEFT JOIN teams t1 ON m.home_team = t1.id
    LEFT JOIN teams t2 ON m.away_team = t2.id
    LEFT JOIN tipster_coupon_leg_events e ON e.leg_id = l.id
    LEFT JOIN events ev ON ev.id = e.event_id
    WHERE l.coupon_id IN ({placeholders})
    ORDER BY l.id ASC, e.id ASC
"""

_FINISHED_RESULTS = ("1", "X", "2")

_OPEN_LEG_COLUMNS = [
    "leg_id",
    "coupon_id",
    "match_id",
    "leg_outcome",
    "event_id",
    "event_name",
    "family",
    "result",
    "home_goals",
    "away_goals",
    "home_ck",
    "away_ck",
    "home_fouls",
    "away_fouls",
    "home_yc",
    "away_yc",
    "home_rc",
    "away_rc",
    "home_off",
    "away_off",
    "stake_amount",
    "combined_odds"]

_SELECT_OPEN_LEGS_FOR_FINISHED_MATCHES = """
    SELECT
        l.id AS leg_id,
        l.coupon_id,
        l.match_id,
        l.outcome AS leg_outcome,
        e.event_id,
        ev.name AS event_name,
        ef.name AS family,
        m.result,
        m.home_team_goals AS home_goals,
        m.away_team_goals AS away_goals,
        m.home_team_ck AS home_ck,
        m.away_team_ck AS away_ck,
        m.home_team_fouls AS home_fouls,
        m.away_team_fouls AS away_fouls,
        m.home_team_yc AS home_yc,
        m.away_team_yc AS away_yc,
        m.home_team_rc AS home_rc,
        m.away_team_rc AS away_rc,
        m.home_team_off AS home_off,
        m.away_team_off AS away_off,
        c.stake_amount,
        c.combined_odds
    FROM tipster_coupon_legs l
    INNER JOIN tipster_coupons c ON c.id = l.coupon_id
    INNER JOIN tipster_coupon_leg_events e ON e.leg_id = l.id
    INNER JOIN events ev ON ev.id = e.event_id
    INNER JOIN matches m ON m.id = l.match_id
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one ON ev.id = efm_one.event_id
    LEFT JOIN event_families ef ON efm_one.event_family_id = ef.id
    WHERE c.settled = 0
      AND (
        EXISTS (
            SELECT 1
            FROM tipster_coupon_legs open_leg
            INNER JOIN matches open_match
                ON open_match.id = open_leg.match_id
            WHERE open_leg.coupon_id = c.id
              AND open_leg.outcome IS NULL
              AND open_match.result IN (%s, %s, %s)
        )
        OR NOT EXISTS (
            SELECT 1
            FROM tipster_coupon_legs pending_leg
            WHERE pending_leg.coupon_id = c.id
              AND pending_leg.outcome IS NULL
        )
      )
    ORDER BY l.coupon_id ASC, l.id ASC, e.id ASC
"""

_WRITE_LEG_OUTCOME = """
    UPDATE tipster_coupon_legs
    SET outcome = %s
    WHERE id = %s
      AND outcome IS NULL
"""

_COMPLETE_COUPON = """
    UPDATE tipster_coupons c
    INNER JOIN (
        SELECT
            coupon_id,
            IF(MIN(outcome) = 1 AND MAX(outcome) = 1, 1, 0)
                AS coupon_outcome
        FROM tipster_coupon_legs
        GROUP BY coupon_id
    ) legs ON legs.coupon_id = c.id
    SET
        c.settled = 1,
        c.outcome = legs.coupon_outcome,
        c.profit = IF(
            legs.coupon_outcome = 1,
            ROUND(c.stake_amount * (c.combined_odds - 1), 2),
            -c.stake_amount)
    WHERE c.id = %s
      AND c.settled = 0
      AND NOT EXISTS (
          SELECT 1
          FROM tipster_coupon_legs pending
          WHERE pending.coupon_id = c.id
            AND pending.outcome IS NULL)
"""

FOOTBALL_SPORT_ID = 1
UNMAPPED_EVENT_FAMILY_NAME = "OTHER"

_LEADERBOARD_COLUMNS = [
    "user_id",
    "username",
    "display_name",
    "is_system",
    "currency",
    "bets_count",
    "won_count",
    "accuracy_pct",
    "legs_count",
    "legs_won",
    "legs_won_on_lost_coupons",
    "stake_total",
    "profit_total",
    "avg_profit",
    "avg_odds",
    "roi_pct",
    "current_balance"]

_LEADERBOARD_SORT_COLUMNS = {
    "profit_total": "profit_total",
    "roi_pct": "roi_pct",
    "accuracy_pct": "accuracy_pct",
    "avg_odds": "avg_odds",
    "avg_profit": "avg_profit",
    "bets_count": "bets_count",
    "current_balance": "current_balance"}

_INT_DIMENSION_FIELDS = frozenset({
    "event_family_id", "league_id", "country_id"})

_EVENT_FAMILY_ONE = """
    SELECT
        efm.event_id,
        MIN(efm.event_family_id) AS event_family_id
    FROM event_family_mappings efm
    GROUP BY efm.event_id
"""

_PERFORMANCE_FACTS_SQL = f"""
    SELECT
        c.id AS coupon_id,
        c.outcome,
        c.stake_amount,
        c.profit,
        l.id AS leg_id,
        l.outcome AS leg_outcome,
        l.odds AS leg_odds,
        lg.id AS league_id,
        lg.name AS league_name,
        ct.id AS country_id,
        ct.name AS country_name,
        ct.emoji AS country_emoji,
        ef.id AS event_family_id,
        ef.name AS event_family_name
    FROM tipster_coupons c
    INNER JOIN tipster_coupon_legs l ON l.coupon_id = c.id
    INNER JOIN matches m ON m.id = l.match_id
    LEFT JOIN leagues lg ON lg.id = m.league
    LEFT JOIN countries ct ON ct.id = lg.country
    INNER JOIN tipster_coupon_leg_events e ON e.leg_id = l.id
    LEFT JOIN ({_EVENT_FAMILY_ONE}) efm ON efm.event_id = e.event_id
    LEFT JOIN event_families ef ON ef.id = efm.event_family_id
    WHERE c.user_id = %s
      AND c.settled = 1
"""

_SELECT_CATALOG_EVENTS = """
    SELECT id, name
    FROM events
    ORDER BY id ASC
"""

_CATALOG_MATCH_COLUMNS = """
    m.id,
    m.league AS league_id,
    l.name AS league_name,
    l.tier AS league_tier,
    m.game_date,
    m.result,
    m.home_team AS home_id,
    t1.name AS home_name,
    t1.shortcut AS home_shortcut,
    m.away_team AS away_id,
    t2.name AS away_name,
    t2.shortcut AS away_shortcut
"""


def get_by_username(username: str) -> dict[str, Any] | None:
    """Return user identity joined with bankroll, or None if missing."""
    row = _fetch_one(_SELECT_BY_USERNAME, (username,))
    if row is None:
        return None
    return _joined_bankroll_document(row)


def get_bankroll(
        user_id: int,
        apply_tax: bool = False) -> dict[str, Any] | None:
    """Return bankroll settings and SQL balances, or None if missing.

    ``apply_tax`` recomputes settled profit for the view. Stored profit
    stays the no-tax settlement.
    """
    query = (
        _bankroll_select_sql()
        if apply_tax else _SELECT_BANKROLL_BY_USER_ID)
    row = _fetch_one(query, (user_id,))
    if row is None:
        return None
    return _bankroll_document(row)


def upsert_bankroll(
        user_id: int,
        currency: str,
        initial_capital: float,
        unit_size: float) -> None:
    """Insert bankroll settings; duplicate PK does not rewrite capital."""
    _execute_write(
        _UPSERT_BANKROLL,
        (user_id, currency, initial_capital, unit_size))


def update_bankroll_settings(
        user_id: int, currency: str, unit_size: float) -> None:
    """Update currency and unit_size without touching initial_capital."""
    _execute_write(
        _UPDATE_BANKROLL_SETTINGS, (currency, unit_size, user_id))


def add_to_initial_capital(
        user_id: int, amount: float) -> dict[str, Any] | None:
    """Increase initial_capital and return the updated bankroll document."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_ADD_TO_INITIAL_CAPITAL, (amount, user_id))
            # amount > 0 zawsze zmienia wiersz — rowcount 0 to brak bankrolla,
            # nie no-op tej samej wartości (CLIENT_FOUND_ROWS nie jest włączony)
            if cursor.rowcount == 0:
                conn.rollback()
                return None
            # mysql-connector bez autocommit — close bez commit cofa UPDATE
            conn.commit()
            cursor.execute(_SELECT_BANKROLL_BY_USER_ID, (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        raise RuntimeError("Bankroll could not be read back")
    return _bankroll_document(dict(row))


def insert_coupon(
        user_id: int,
        stake_amount: float,
        stake_units: float | None,
        stake_input_mode: str,
        legs: list[dict[str, Any]],
        combined_odds: float | None = None) -> dict[str, Any]:
    """Insert a coupon, legs and events in one transaction.

    ``combined_odds`` is the product of per-leg odds. A combined leg still
    contributes a single bookmaker price, not a product of its events.
    The service may pass the snapshot; otherwise it is computed here.
    """
    snapshot = combined_odds
    if snapshot is None:
        snapshot = _combined_odds(legs)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            document = _write_coupon_graph(
                cursor,
                user_id,
                stake_amount,
                stake_units,
                stake_input_mode,
                snapshot,
                legs)
            # mysql-connector bez autocommit — close bez commit cofa cały graf
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return document


def fetch_coupons(
        user_id: int,
        settled: int | None,
        page: int,
        page_size: int,
        apply_tax: bool = False) -> tuple[list[dict[str, Any]], int]:
    """Return a coupon page with nested legs; visibility is a service concern.

    ``apply_tax`` replaces settled profit in the SELECT. Open coupons
    keep a NULL profit. The stored column is not rewritten.
    """
    where_sql, where_params = _coupon_list_filters(user_id, settled)
    offset = (page - 1) * page_size
    columns = _coupon_list_columns(apply_tax)
    coupon_from = "tipster_coupons c" if apply_tax else "tipster_coupons"
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM tipster_coupons
        {where_sql}
    """
    list_sql = f"""
        SELECT {columns}
        FROM {coupon_from}
        {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT %s OFFSET %s
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(count_sql, where_params)
            total_row = cursor.fetchone()
            cursor.execute(
                list_sql, (*where_params, page_size, offset))
            coupon_rows = list(cursor.fetchall())
            legs_by_coupon = _fetch_legs_by_coupon_ids(
                cursor, [int(row["id"]) for row in coupon_rows])
        finally:
            cursor.close()
    total = int(total_row["total"]) if total_row else 0
    items = [
        _coupon_document(
            dict(row),
            legs_by_coupon.get(int(row["id"]), []))
        for row in coupon_rows]
    return items, total


def fetch_open_legs_for_finished_matches() -> pd.DataFrame:
    """Return open-coupon legs that can be settled or closed.

    Includes sibling legs of the same coupon so AND/close can be decided
    without a second query, plus already-settled coupons still open after
    a crash between ``write_leg_outcome`` and ``complete_coupon``.
    """
    rows = _fetch_all(
        _SELECT_OPEN_LEGS_FOR_FINISHED_MATCHES, _FINISHED_RESULTS)
    if not rows:
        return pd.DataFrame(columns=_OPEN_LEG_COLUMNS)
    # dtype=object zachowuje DECIMAL z mysql-connector (inaczej pandas
    # potrafi zrzucić stawkę i kurs do float64)
    return pd.DataFrame(rows, columns=_OPEN_LEG_COLUMNS, dtype=object)


def write_leg_outcome(leg_id: int, outcome: int) -> None:
    """Set a leg outcome only while it is still NULL."""
    _execute_write(_WRITE_LEG_OUTCOME, (outcome, leg_id))


def complete_coupon(coupon_id: int) -> int:
    """Close a coupon from persisted leg outcomes; return rows changed."""
    return _execute_write(_COMPLETE_COUPON, (coupon_id,))


def fetch_leaderboard(
        filters: dict[str, Any] | None = None
        ) -> tuple[pd.DataFrame, int]:
    """Return a ranking page and the total bankroll-user count.

    Ranking always includes humans and system accounts that have a
    bankroll row when no coupon filters are set (LEFT JOIN stats).
    League, tier, family or date filters INNER JOIN stats so users
    without matching settled volume are omitted. Coupon lists are not
    selected. ``current_balance`` stays the unfiltered bankroll formula.
    Optional metric columns stay Python ``None`` (object dtype) so a
    system agent with zero settled coupons does not become NaN in JSON.
    """
    resolved = filters or {}
    count_sql, count_params = _leaderboard_count_query(resolved)
    list_sql, list_params = _leaderboard_query(resolved)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(count_sql, count_params)
            total_row = cursor.fetchone()
            cursor.execute(list_sql, list_params)
            rows = list(cursor.fetchall() or [])
        finally:
            cursor.close()
    total = int(total_row["total"]) if total_row else 0
    return _leaderboard_frame(rows), total


def fetch_performance(
        user_id: int,
        apply_tax: bool = False) -> dict[str, Any]:
    """Return settled-coupon breakdowns by family, league and country.

    Attribution is membership (coupon belongs to a dimension value),
    not stake allocation. A combined BTTS+O2.5 coupon counts in both
    families with the full stake and profit; a two-league parlay does
    the same per league and per country. Summing ``profit_total``
    across buckets can exceed the user's realized PnL.

    ``won`` is the coupon result. ``legs_won`` is the leg result, so a
    lost accumulator can still show a family whose own leg won. A
    combined leg has one outcome for every event on it.

    ``avg_odds`` is the mean of those leg prices, not the coupon's
    combined odds.

    Unmapped settleable markets (corners, DNB, handicap) share one
    bucket: ``event_family_id`` is None and ``event_family_name`` is
    ``OTHER`` so best/worst never surface a nameless row. Ranking
    filter ``event_family`` equal to ``OTHER`` or ``0`` selects the
    same unmapped events.
    """
    # mappingi nie pokrywają rożnych/DNB/AH — jedna etykieta dla UI
    rows = [
        _label_unmapped_event_family(row)
        for row in _fetch_all(
            _performance_facts_sql(apply_tax), (user_id,))]
    by_event_family = _aggregate_dimension(
        rows,
        ("event_family_id", "event_family_name"),
        skip_none=False)
    by_league = _aggregate_dimension(
        rows, ("league_id", "league_name"), skip_none=True)
    by_country = _aggregate_dimension(
        rows,
        ("country_id", "country_name"),
        skip_none=True,
        extra_fields=("country_emoji",))
    best_family, worst_family = _best_worst(by_event_family)
    best_league, worst_league = _best_worst(by_league)
    best_country, worst_country = _best_worst(by_country)
    return {
        "by_event_family": by_event_family,
        "by_league": by_league,
        "by_country": by_country,
        "best_event_family": best_family,
        "worst_event_family": worst_family,
        "best_league": best_league,
        "worst_league": worst_league,
        "best_country": best_country,
        "worst_country": worst_country}


_SELECT_SUGGESTED_CATALOG_ODDS = """
    SELECT o.odds AS odds
    FROM odds o
    WHERE o.match_id = %s
      AND o.event = %s
      AND o.odds IS NOT NULL
      AND o.odds >= %s
      AND EXISTS (
          SELECT 1
          FROM predictions p
          WHERE p.match_id = o.match_id
            AND p.event_id = o.event)
    ORDER BY o.odds DESC, o.id ASC
    LIMIT 1
"""


def fetch_suggested_catalog_odds(
        match_id: int,
        event_id: int,
        min_odds: float) -> float | None:
    """Return the best odds for a predicted event, or None.

    Highest price wins. Equal prices keep the lowest ``odds.id``, the same
    tie-break as automatic bet generation. No prediction or no price means
    the coupon field stays empty for the user to type.
    """
    row = _fetch_one(
        _SELECT_SUGGESTED_CATALOG_ODDS,
        (match_id, event_id, min_odds))
    if row is None or row.get("odds") is None:
        return None
    return float(row["odds"])


def fetch_catalog_matches(
        date_from: date | None,
        date_to: date | None,
        league_ids: list[int] | None) -> dict[str, Any]:
    """Return upcoming unfinished football matches and settleable events.

    Events are filtered in Python via the settlement registry so line
    markets parsed from names stay in sync with evaluator support.
    Matches and events are separate lists — not a cartesian product.
    Kick-off is always ``game_date >= CURRENT_TIMESTAMP``; date and
    league arguments only narrow that upcoming window.
    """
    # picker składa combined sam — nie dublujemy eventów przy każdym meczu
    match_sql, match_params = _catalog_matches_query(
        date_from, date_to, league_ids)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(match_sql, match_params)
            match_rows = list(cursor.fetchall() or [])
            cursor.execute(_SELECT_CATALOG_EVENTS)
            event_rows = list(cursor.fetchall() or [])
        finally:
            cursor.close()
    return {
        "matches": [_catalog_match_document(row) for row in match_rows],
        "events": [
            _catalog_event_document(row)
            for row in event_rows
            if is_settleable_event(int(row["id"]), str(row["name"] or ""))]}


def _write_coupon_graph(
        cursor: Any,
        user_id: int,
        stake_amount: float,
        stake_units: float | None,
        stake_input_mode: str,
        combined_odds: float,
        legs: list[dict[str, Any]]) -> dict[str, Any]:
    cursor.execute(
        _INSERT_COUPON,
        (
            user_id,
            stake_amount,
            stake_units,
            stake_input_mode,
            combined_odds))
    coupon_id = int(cursor.lastrowid)
    inserted_legs = [
        _insert_leg(cursor, coupon_id, leg) for leg in legs]
    cursor.execute(_SELECT_COUPON_BY_ID, (coupon_id,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Inserted coupon could not be read back")
    return _coupon_document(dict(row), inserted_legs)


def _insert_leg(
        cursor: Any,
        coupon_id: int,
        leg: dict[str, Any]) -> dict[str, Any]:
    cursor.execute(
        _INSERT_LEG,
        (
            coupon_id,
            int(leg["match_id"]),
            leg["odds"],
            leg.get("bookmaker_id"),
            str(leg["source"])))
    leg_id = int(cursor.lastrowid)
    event_ids = [int(event_id) for event_id in leg["event_ids"]]
    for event_id in event_ids:
        cursor.execute(_INSERT_LEG_EVENT, (leg_id, event_id))
    return _leg_document(
        leg_id,
        int(leg["match_id"]),
        event_ids,
        leg["odds"],
        leg.get("bookmaker_id"),
        str(leg["source"]),
        None)


def _combined_odds(legs: list[dict[str, Any]]) -> float:
    """Return the product of per-leg odds, ignoring events inside a combined."""
    product = Decimal("1")
    for leg in legs:
        product *= _as_decimal(leg["odds"])
    return float(product)


def _coupon_list_filters(
        user_id: int,
        settled: int | None) -> tuple[str, tuple[object, ...]]:
    conditions = ["user_id = %s"]
    params: list[object] = [user_id]
    if settled is not None:
        conditions.append("settled = %s")
        params.append(settled)
    return "WHERE " + " AND ".join(conditions), tuple(params)


def _fetch_legs_by_coupon_ids(
        cursor: Any,
        coupon_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not coupon_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(coupon_ids))
    cursor.execute(
        _SELECT_LEGS_FOR_COUPONS.format(placeholders=placeholders),
        tuple(coupon_ids))
    return _group_leg_rows(list(cursor.fetchall()))


def _group_leg_rows(
        rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    legs_by_id: dict[int, dict[str, Any]] = {}
    order_by_coupon: dict[int, list[int]] = {}
    for row in rows:
        leg_id = int(row["leg_id"])
        coupon_id = int(row["coupon_id"])
        if leg_id not in legs_by_id:
            legs_by_id[leg_id] = _leg_document(
                leg_id,
                int(row["match_id"]),
                [],
                row["odds"],
                row["bookmaker_id"],
                str(row["source"]),
                row["outcome"],
                row.get("home_name"),
                row.get("away_name"),
                [])
            order_by_coupon.setdefault(coupon_id, []).append(leg_id)
        event_id = row.get("event_id")
        if event_id is not None:
            legs_by_id[leg_id]["event_ids"].append(int(event_id))
            event_name = row.get("event_name")
            legs_by_id[leg_id]["event_names"].append(
                str(event_name) if event_name else f"#{int(event_id)}")
    return {
        coupon_id: [legs_by_id[leg_id] for leg_id in leg_ids]
        for coupon_id, leg_ids in order_by_coupon.items()}


def _coupon_document(
        row: dict[str, Any],
        legs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "stake_amount": float(row["stake_amount"]),
        "stake_units": _as_optional_float(row["stake_units"]),
        "stake_input_mode": str(row["stake_input_mode"]),
        "combined_odds": float(row["combined_odds"]),
        "settled": int(row["settled"]),
        "outcome": _as_optional_int(row["outcome"]),
        "profit": _as_optional_float(row["profit"]),
        "created_at": row["created_at"],
        "legs": legs}


def _leg_document(
        leg_id: int,
        match_id: int,
        event_ids: list[int],
        odds: object,
        bookmaker_id: object,
        source: str,
        outcome: object,
        home_name: object = None,
        away_name: object = None,
        event_names: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": leg_id,
        "match_id": match_id,
        "home_name": _as_optional_str(home_name),
        "away_name": _as_optional_str(away_name),
        "event_ids": event_ids,
        "event_names": list(event_names or []),
        "odds": float(odds),
        "bookmaker_id": _as_optional_int(bookmaker_id),
        "source": source,
        "outcome": _as_optional_int(outcome)}


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _as_optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _bankroll_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": int(row["user_id"]),
        "currency": str(row["currency"]),
        "initial_capital": float(row["initial_capital"]),
        "unit_size": float(row["unit_size"]),
        "current_balance": float(row["current_balance"]),
        "open_stake": float(row["open_stake"]),
        "realized_pnl": float(row["realized_pnl"])}


def _joined_bankroll_document(row: dict[str, Any]) -> dict[str, Any]:
    document = _bankroll_document(row)
    document["username"] = str(row["username"])
    document["display_name"] = row["display_name"]
    document["is_system"] = int(row["is_system"])
    return document


def _leaderboard_query(
        filters: dict[str, Any]) -> tuple[str, tuple[object, ...]]:
    stats_sql, stats_params = _leaderboard_stats_subquery(filters)
    stats_join = _leaderboard_stats_join(filters)
    user_where, user_params = _leaderboard_user_filters(filters)
    sort_column, sort_order = _leaderboard_sort(filters)
    limit_sql, limit_params = _leaderboard_limit(filters)
    apply_tax = bool(filters.get("apply_tax"))
    balance_expr = (
        _taxed_balance_expr() if apply_tax else _CURRENT_BALANCE_EXPR)
    query = f"""
        SELECT
            u.id AS user_id,
            u.username,
            u.display_name,
            u.is_system,
            tb.currency,
            COALESCE(stats.bets_count, 0) AS bets_count,
            COALESCE(stats.won_count, 0) AS won_count,
            CASE
                WHEN COALESCE(stats.bets_count, 0) = 0 THEN NULL
                ELSE ROUND(
                    stats.won_count * 100.0 / stats.bets_count, 2)
            END AS accuracy_pct,
            COALESCE(stats.legs_count, 0) AS legs_count,
            COALESCE(stats.legs_won, 0) AS legs_won,
            COALESCE(stats.legs_won_on_lost_coupons, 0)
                AS legs_won_on_lost_coupons,
            COALESCE(stats.stake_total, 0) AS stake_total,
            COALESCE(stats.profit_total, 0) AS profit_total,
            CASE
                WHEN COALESCE(stats.bets_count, 0) = 0 THEN NULL
                ELSE ROUND(stats.profit_total / stats.bets_count, 2)
            END AS avg_profit,
            ROUND(stats.avg_odds, 4) AS avg_odds,
            CASE
                WHEN COALESCE(stats.stake_total, 0) = 0 THEN NULL
                ELSE ROUND(
                    stats.profit_total * 100.0 / stats.stake_total, 2)
            END AS roi_pct,
            {balance_expr} AS current_balance
        FROM users u
        INNER JOIN tipster_bankrolls tb ON tb.user_id = u.id
        {stats_join} (
            {stats_sql}
        ) stats ON stats.user_id = u.id
        {user_where}
        ORDER BY {sort_column} {sort_order}, u.id ASC
        {limit_sql}
    """
    return query, (*stats_params, *user_params, *limit_params)


def _leaderboard_count_query(
        filters: dict[str, Any]) -> tuple[str, tuple[object, ...]]:
    user_where, user_params = _leaderboard_user_filters(filters)
    if not _has_coupon_volume_filters(filters):
        query = f"""
            SELECT COUNT(*) AS total
            FROM users u
            INNER JOIN tipster_bankrolls tb ON tb.user_id = u.id
            {user_where}
        """
        return query, tuple(user_params)
    # ten sam zbiór co lista: INNER JOIN stats przy filtrze volume
    stats_sql, stats_params = _leaderboard_stats_subquery(filters)
    query = f"""
        SELECT COUNT(*) AS total
        FROM users u
        INNER JOIN tipster_bankrolls tb ON tb.user_id = u.id
        INNER JOIN (
            {stats_sql}
        ) stats ON stats.user_id = u.id
        {user_where}
    """
    return query, (*stats_params, *user_params)


def _leaderboard_stats_subquery(
        filters: dict[str, Any]) -> tuple[str, list[object]]:
    """Coupon totals plus leg hits for the same filters.

    A coupon still counts in full when one of its legs matches.
    Without a league, tier or family filter, ``avg_odds`` is the mean
    combined coupon price. Those filters narrow the price to the
    matching legs only.
    """
    coupon_where, coupon_params = _coupon_stats_filters(filters)
    leg_sql, leg_params = _leaderboard_leg_stats_sql(filters)
    profit_sql = _settled_profit_sql(bool(filters.get("apply_tax")))
    odds_sql = (
        "leg_stats.avg_odds"
        if _ranking_uses_leg_odds(filters)
        else "coupons.avg_odds")
    coupon_odds_sql = (
        ""
        if _ranking_uses_leg_odds(filters)
        else ",\n                    AVG(c.combined_odds) AS avg_odds")
    subquery = f"""
            SELECT
                coupons.user_id,
                coupons.bets_count,
                coupons.won_count,
                coupons.stake_total,
                coupons.profit_total,
                leg_stats.legs_count,
                leg_stats.legs_won,
                leg_stats.legs_won_on_lost_coupons,
                {odds_sql} AS avg_odds
            FROM (
                SELECT
                    c.user_id,
                    COUNT(*) AS bets_count,
                    SUM(CASE WHEN c.outcome = 1 THEN 1 ELSE 0 END)
                        AS won_count,
                    SUM(c.stake_amount) AS stake_total,
                    SUM({profit_sql}) AS profit_total{coupon_odds_sql}
                FROM tipster_coupons c
                WHERE {coupon_where}
                GROUP BY c.user_id
            ) coupons
            INNER JOIN (
                {leg_sql}
            ) leg_stats ON leg_stats.user_id = coupons.user_id
    """
    return subquery, [*coupon_params, *leg_params]


def _ranking_uses_leg_odds(filters: dict[str, Any]) -> bool:
    """True when a filter narrows odds from the coupon to its legs."""
    return _has_leg_domain_filters(filters)


def _has_coupon_volume_filters(filters: dict[str, Any]) -> bool:
    # bez volume 0-profit nie może wyprzedzać strat na odfiltrowanej lidze
    if filters.get("date_from") is not None:
        return True
    if filters.get("date_to") is not None:
        return True
    return _has_leg_domain_filters(filters)


def _has_leg_domain_filters(filters: dict[str, Any]) -> bool:
    if filters.get("tier") is not None:
        return True
    if filters.get("event_family") is not None:
        return True
    if filters.get("event_ids"):
        return True
    return bool(filters.get("league_ids"))


def _leaderboard_stats_join(filters: dict[str, Any]) -> str:
    if _has_coupon_volume_filters(filters):
        return "INNER JOIN"
    return "LEFT JOIN"


def _is_unmapped_event_family_filter(event_family: object) -> bool:
    # "0" z querystringu to kubełek OTHER, nie id rodziny
    if isinstance(event_family, str):
        token = event_family.strip().upper()
        if token == UNMAPPED_EVENT_FAMILY_NAME:
            return True
        event_family = token
    try:
        return int(event_family) == 0
    except (TypeError, ValueError):
        return False


def _label_unmapped_event_family(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("event_family_id") is not None:
        return row
    labeled = dict(row)
    labeled["event_family_name"] = UNMAPPED_EVENT_FAMILY_NAME
    return labeled


def _leaderboard_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    # dtype=object: None w accuracy/roi nie awansuje do NaN obok float
    if not rows:
        return pd.DataFrame(
            columns=_LEADERBOARD_COLUMNS, dtype=object)
    documents = [_leaderboard_document(row) for row in rows]
    return pd.DataFrame(
        documents, columns=_LEADERBOARD_COLUMNS, dtype=object)


def _leaderboard_leg_stats_sql(
        filters: dict[str, Any]) -> tuple[str, list[object]]:
    """One row per user: matching legs, their hit rate and mean price."""
    joins, where, params = _leaderboard_leg_filter(filters)
    sql = f"""
                SELECT
                    matched.user_id,
                    COUNT(*) AS legs_count,
                    SUM(matched.leg_won) AS legs_won,
                    SUM(matched.won_on_lost)
                        AS legs_won_on_lost_coupons,
                    AVG(matched.odds) AS avg_odds
                FROM (
                    SELECT DISTINCT
                        c.user_id,
                        l.id AS leg_id,
                        l.odds AS odds,
                        CASE WHEN l.outcome = 1 THEN 1 ELSE 0 END
                            AS leg_won,
                        CASE
                            WHEN l.outcome = 1 AND c.outcome <> 1
                            THEN 1
                            ELSE 0
                        END AS won_on_lost
                    FROM tipster_coupons c
                    INNER JOIN tipster_coupon_legs l
                        ON l.coupon_id = c.id
                    {joins}
                    WHERE {where}
                ) matched
                GROUP BY matched.user_id
    """
    return sql, params


def _coupon_stats_filters(
        filters: dict[str, Any]) -> tuple[str, list[object]]:
    conditions, params = _settled_coupon_conditions(filters)
    exists_sql, exists_params = _matching_leg_exists(filters)
    if exists_sql:
        conditions.append(exists_sql)
        params.extend(exists_params)
    return " AND ".join(conditions), params


def _settled_coupon_conditions(
        filters: dict[str, Any]) -> tuple[list[str], list[object]]:
    conditions = ["c.settled = 1"]
    params: list[object] = []
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from is not None:
        conditions.append("CAST(c.created_at AS DATE) >= %s")
        params.append(date_from)
    if date_to is not None:
        conditions.append("CAST(c.created_at AS DATE) <= %s")
        params.append(date_to)
    return conditions, params


def _leaderboard_leg_filter(
        filters: dict[str, Any]) -> tuple[str, str, list[object]]:
    """Joins and WHERE for legs that match the ranking filters."""
    conditions, params = _settled_coupon_conditions(filters)
    joins, extra_conditions, extra_params = _dimensional_leg_joins(
        filters)
    conditions.extend(extra_conditions)
    params.extend(extra_params)
    return " ".join(joins), " AND ".join(conditions), params


def _matching_leg_exists(
        filters: dict[str, Any]) -> tuple[str, list[object]]:
    joins, conditions, params = _dimensional_leg_joins(filters)
    if not joins and not conditions:
        return "", []
    exists_sql = (
        "EXISTS (SELECT 1 FROM tipster_coupon_legs l "
        + " ".join(joins)
        + " WHERE l.coupon_id = c.id AND "
        + " AND ".join(conditions)
        + ")")
    return exists_sql, params


def _dimensional_leg_joins(
        filters: dict[str, Any]
        ) -> tuple[list[str], list[str], list[object]]:
    """League, tier, family and event constraints for one coupon leg."""
    league_ids = list(filters.get("league_ids") or [])
    tier = filters.get("tier")
    event_family = filters.get("event_family")
    event_ids = list(filters.get("event_ids") or [])
    has_domain = bool(league_ids) or tier is not None
    has_events = event_family is not None or bool(event_ids)
    if not has_domain and not has_events:
        return [], [], []
    joins = ["INNER JOIN matches m ON m.id = l.match_id"]
    conditions: list[str] = []
    params: list[object] = []
    if league_ids or tier is not None:
        joins.append("INNER JOIN leagues lg ON lg.id = m.league")
    if league_ids:
        placeholders = ", ".join(["%s"] * len(league_ids))
        conditions.append(f"m.league IN ({placeholders})")
        params.extend(int(league_id) for league_id in league_ids)
    if tier is not None:
        conditions.append("lg.tier = %s")
        params.append(int(tier))
    _append_event_family_leg_filter(
        joins, conditions, params, event_family)
    _append_event_ids_leg_filter(joins, conditions, params, event_ids)
    return joins, conditions, params


def _append_event_family_leg_filter(
        joins: list[str],
        conditions: list[str],
        params: list[object],
        event_family: object) -> None:
    if event_family is None:
        return
    joins.append(
        "INNER JOIN tipster_coupon_leg_events e ON e.leg_id = l.id")
    if _is_unmapped_event_family_filter(event_family):
        conditions.append(
            "NOT EXISTS ("
            f"SELECT 1 FROM ({_EVENT_FAMILY_ONE}) efm "
            "WHERE efm.event_id = e.event_id)")
        return
    joins.append(
        f"INNER JOIN ({_EVENT_FAMILY_ONE}) efm "
        "ON efm.event_id = e.event_id")
    conditions.append("efm.event_family_id = %s")
    params.append(int(event_family))


def _append_event_ids_leg_filter(
        joins: list[str],
        conditions: list[str],
        params: list[object],
        event_ids: list[object]) -> None:
    if not event_ids:
        return
    if "tipster_coupon_leg_events e" not in " ".join(joins):
        joins.append(
            "INNER JOIN tipster_coupon_leg_events e "
            "ON e.leg_id = l.id")
    placeholders = ", ".join(["%s"] * len(event_ids))
    conditions.append(f"e.event_id IN ({placeholders})")
    params.extend(int(event_id) for event_id in event_ids)


def _leaderboard_user_filters(
        filters: dict[str, Any]) -> tuple[str, list[object]]:
    is_system = filters.get("is_system")
    if is_system is None:
        return "", []
    return "WHERE u.is_system = %s", [int(is_system)]


def _leaderboard_sort(filters: dict[str, Any]) -> tuple[str, str]:
    sort_by = str(filters.get("sort_by") or "profit_total")
    sort_column = _LEADERBOARD_SORT_COLUMNS.get(
        sort_by, _LEADERBOARD_SORT_COLUMNS["profit_total"])
    sort_order = "ASC" if filters.get("sort_order") == "asc" else "DESC"
    return sort_column, sort_order


def _leaderboard_limit(
        filters: dict[str, Any]) -> tuple[str, tuple[object, ...]]:
    page_size = filters.get("page_size")
    if page_size is None:
        return "", ()
    size = int(page_size)
    if size <= 0:
        return "", ()
    page = max(int(filters.get("page") or 1), 1)
    offset = (page - 1) * size
    return "LIMIT %s OFFSET %s", (size, offset)


def _leaderboard_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": int(row["user_id"]),
        "username": str(row["username"]),
        "display_name": row["display_name"],
        "is_system": int(row["is_system"]),
        "currency": str(row["currency"]),
        "bets_count": int(row["bets_count"] or 0),
        "won_count": int(row["won_count"] or 0),
        "accuracy_pct": _as_optional_float(row["accuracy_pct"]),
        "legs_count": int(row["legs_count"] or 0),
        "legs_won": int(row["legs_won"] or 0),
        "legs_won_on_lost_coupons": int(
            row["legs_won_on_lost_coupons"] or 0),
        "stake_total": float(row["stake_total"] or 0),
        "profit_total": float(row["profit_total"] or 0),
        "avg_profit": _as_optional_float(row["avg_profit"]),
        "avg_odds": _as_optional_float(row["avg_odds"]),
        "roi_pct": _as_optional_float(row["roi_pct"]),
        "current_balance": float(row["current_balance"])}


def _aggregate_dimension(
        rows: list[dict[str, Any]],
        key_fields: tuple[str, ...],
        skip_none: bool,
        extra_fields: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    groups: dict[tuple[object, ...], dict[str, Any]] = {}
    seen: dict[tuple[object, ...], set[int]] = {}
    seen_legs: dict[tuple[object, ...], set[int]] = {}
    stored_fields = key_fields + extra_fields
    for row in rows:
        if skip_none and any(
                row[field] is None for field in key_fields):
            continue
        key = tuple(row[field] for field in key_fields)
        coupon_id = int(row["coupon_id"])
        if key not in groups:
            groups[key] = _empty_performance_bucket(row, stored_fields)
            seen[key] = set()
            seen_legs[key] = set()
        _add_leg_hit(groups[key], seen_legs[key], row)
        if coupon_id in seen[key]:
            continue
        # combined ma kilka eventów — kupon w rodzinie liczymy raz
        seen[key].add(coupon_id)
        _add_coupon_to_bucket(groups[key], row)
    items = [
        _performance_item(bucket, stored_fields)
        for bucket in groups.values()]
    items.sort(
        key=lambda item: (-item["profit_total"], -item["count"]))
    return items


def _empty_performance_bucket(
        row: dict[str, Any],
        key_fields: tuple[str, ...]) -> dict[str, Any]:
    bucket: dict[str, Any] = {
        "count": 0,
        "won": 0,
        "legs_count": 0,
        "legs_won": 0,
        "legs_won_on_lost_coupons": 0,
        "stake_total": 0.0,
        "profit_total": 0.0,
        "leg_odds_sum": 0.0}
    for field in key_fields:
        bucket[field] = row[field]
    return bucket


def _add_coupon_to_bucket(
        bucket: dict[str, Any], row: dict[str, Any]) -> None:
    bucket["count"] += 1
    if int(row["outcome"] or 0) == 1:
        bucket["won"] += 1
    bucket["stake_total"] += float(row["stake_amount"] or 0)
    bucket["profit_total"] += float(row["profit"] or 0)


def _add_leg_hit(
        bucket: dict[str, Any],
        seen_legs: set[int],
        row: dict[str, Any]) -> None:
    """Count each leg once; a win on a lost coupon stays visible."""
    leg_id = row.get("leg_id")
    if leg_id is None or int(leg_id) in seen_legs:
        return
    seen_legs.add(int(leg_id))
    bucket["legs_count"] += 1
    bucket["leg_odds_sum"] += float(row.get("leg_odds") or 0)
    if int(row.get("leg_outcome") or 0) != 1:
        return
    bucket["legs_won"] += 1
    if int(row["outcome"] or 0) != 1:
        bucket["legs_won_on_lost_coupons"] += 1


def _dimension_value(field: str, value: object) -> object:
    if value is None:
        return None
    if field in _INT_DIMENSION_FIELDS:
        return int(value)
    return value


def _performance_item(
        bucket: dict[str, Any],
        key_fields: tuple[str, ...]) -> dict[str, Any]:
    count = int(bucket["count"])
    won = int(bucket["won"])
    legs_count = int(bucket["legs_count"])
    legs_won = int(bucket["legs_won"])
    stake_total = float(bucket["stake_total"])
    profit_total = round(float(bucket["profit_total"]), 2)
    item = {
        field: _dimension_value(field, bucket[field])
        for field in key_fields}
    item.update({
        "count": count,
        "won": won,
        "accuracy": round(won * 100 / count, 2) if count else None,
        "legs_count": legs_count,
        "legs_won": legs_won,
        "legs_accuracy": (
            round(legs_won * 100 / legs_count, 2)
            if legs_count else None),
        "legs_won_on_lost_coupons": int(
            bucket["legs_won_on_lost_coupons"]),
        "stake_total": round(stake_total, 2),
        "profit_total": profit_total,
        "avg_profit": round(profit_total / count, 2) if count else None,
        "avg_odds": (
            round(bucket["leg_odds_sum"] / legs_count, 4)
            if legs_count else None),
        "roi_pct": (
            round(profit_total * 100 / stake_total, 2)
            if stake_total else None)})
    return item


def _best_worst(
        items: list[dict[str, Any]]
        ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not items:
        return None, None
    best = max(
        items, key=lambda item: (item["profit_total"], item["count"]))
    worst = min(
        items, key=lambda item: (item["profit_total"], -item["count"]))
    return best, worst


def _catalog_matches_query(
        date_from: date | None,
        date_to: date | None,
        league_ids: list[int] | None
        ) -> tuple[str, tuple[object, ...]]:
    conditions = [
        "(m.result IS NULL OR m.result NOT IN (%s, %s, %s))",
        "m.sport_id = %s",
        "m.game_date >= CURRENT_TIMESTAMP"]
    # hokej bez boxscore z rejestru; przeszłe result=0 zawsze odpadają
    params: list[object] = [*_FINISHED_RESULTS, FOOTBALL_SPORT_ID]
    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)
    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)
    if league_ids:
        placeholders = ", ".join(["%s"] * len(league_ids))
        conditions.append(f"m.league IN ({placeholders})")
        params.extend(int(league_id) for league_id in league_ids)
    where_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            {_CATALOG_MATCH_COLUMNS}
        FROM matches m
        INNER JOIN teams t1 ON m.home_team = t1.id
        INNER JOIN teams t2 ON m.away_team = t2.id
        INNER JOIN leagues l ON l.id = m.league
        WHERE {where_sql}
        ORDER BY m.game_date ASC, m.id ASC
    """
    return query, tuple(params)


def _catalog_match_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "league_id": int(row["league_id"]),
        "league_name": row["league_name"],
        "league_tier": _as_optional_int(row["league_tier"]),
        "game_date": row["game_date"],
        "result": (
            str(row["result"]) if row["result"] is not None else None),
        "home_id": int(row["home_id"]),
        "home_name": str(row["home_name"]),
        "home_shortcut": row["home_shortcut"],
        "away_id": int(row["away_id"]),
        "away_name": str(row["away_name"]),
        "away_shortcut": row["away_shortcut"]}


def _catalog_event_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": str(row["name"] or "")}


def _fetch_one(query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
        finally:
            cursor.close()
    return dict(row) if row else None


def _fetch_all(
        query: str, params: tuple[object, ...]) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall() or []
        finally:
            cursor.close()
    return [dict(row) for row in rows]


def _execute_write(query: str, params: tuple[object, ...]) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            updated = int(cursor.rowcount or 0)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
            return updated
        finally:
            cursor.close()
