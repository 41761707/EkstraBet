"""SQL queries for tipster bankrolls and coupons keyed by users.id."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.database import get_db_connection


# saldo: initial_capital + SUM(profit) settled; open_stake osobno, bez
# pomniejszania current_balance o otwarte kupony
_BALANCE_COLUMNS = """
    tb.user_id,
    tb.currency,
    tb.initial_capital,
    tb.unit_size,
    tb.initial_capital + COALESCE((
        SELECT SUM(c.profit)
        FROM tipster_coupons c
        WHERE c.user_id = tb.user_id AND c.settled = 1
    ), 0) AS current_balance,
    COALESCE((
        SELECT SUM(c.stake_amount)
        FROM tipster_coupons c
        WHERE c.user_id = tb.user_id AND c.settled = 0
    ), 0) AS open_stake,
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
        initial_capital = VALUES(initial_capital),
        unit_size = VALUES(unit_size)
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
        e.event_id
    FROM tipster_coupon_legs l
    LEFT JOIN tipster_coupon_leg_events e ON e.leg_id = l.id
    WHERE l.coupon_id IN ({placeholders})
    ORDER BY l.id ASC, e.id ASC
"""


def get_by_username(username: str) -> dict[str, Any] | None:
    """Return user identity joined with bankroll, or None if missing."""
    row = _fetch_one(_SELECT_BY_USERNAME, (username,))
    if row is None:
        return None
    return _joined_bankroll_document(row)


def get_bankroll(user_id: int) -> dict[str, Any] | None:
    """Return bankroll settings and SQL balances, or None if missing."""
    row = _fetch_one(_SELECT_BANKROLL_BY_USER_ID, (user_id,))
    if row is None:
        return None
    return _bankroll_document(row)


def upsert_bankroll(
        user_id: int,
        currency: str,
        initial_capital: float,
        unit_size: float) -> None:
    """Insert or replace bankroll settings for the given user."""
    _execute_write(
        _UPSERT_BANKROLL,
        (user_id, currency, initial_capital, unit_size))


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
        legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Insert a coupon, legs and events in one transaction.

    ``combined_odds`` is the product of per-leg odds. A combined leg still
    contributes a single bookmaker price, not a product of its events.
    """
    combined_odds = _combined_odds(legs)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            document = _write_coupon_graph(
                cursor,
                user_id,
                stake_amount,
                stake_units,
                stake_input_mode,
                combined_odds,
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
        page_size: int) -> tuple[list[dict[str, Any]], int]:
    """Return a coupon page with nested legs; visibility is a service concern."""
    where_sql, where_params = _coupon_list_filters(user_id, settled)
    offset = (page - 1) * page_size
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM tipster_coupons
        {where_sql}
    """
    list_sql = f"""
        SELECT {_COUPON_COLUMNS}
        FROM tipster_coupons
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
                row["outcome"])
            order_by_coupon.setdefault(coupon_id, []).append(leg_id)
        event_id = row.get("event_id")
        if event_id is not None:
            legs_by_id[leg_id]["event_ids"].append(int(event_id))
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
        outcome: object) -> dict[str, Any]:
    return {
        "id": leg_id,
        "match_id": match_id,
        "event_ids": event_ids,
        "odds": float(odds),
        "bookmaker_id": _as_optional_int(bookmaker_id),
        "source": source,
        "outcome": _as_optional_int(outcome)}


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


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


def _fetch_one(query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
        finally:
            cursor.close()
    return dict(row) if row else None


def _execute_write(query: str, params: tuple[object, ...]) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
        finally:
            cursor.close()
