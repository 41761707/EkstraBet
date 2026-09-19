"""SQL queries for tipster bankrolls keyed by users.id."""

from __future__ import annotations

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
