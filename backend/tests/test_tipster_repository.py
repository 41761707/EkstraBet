"""Unit tests for tipster bankroll repository SQL contracts."""

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError

from backend.repositories import tipster_repository as repo


_GET_CONN = "backend.repositories.tipster_repository.get_db_connection"

# mysql-connector oddaje DECIMAL jako Decimal — dokument musi zejść do float
_BANKROLL_ROW = {
    "user_id": 7,
    "currency": "PLN",
    "initial_capital": Decimal("1000.00"),
    "unit_size": Decimal("10.00"),
    "current_balance": Decimal("850.00"),
    "open_stake": Decimal("20.00"),
    "realized_pnl": Decimal("-150.00")}

_JOINED_ROW = {
    **_BANKROLL_ROW,
    "username": "alice",
    "display_name": "Alice",
    "is_system": 0}


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        rowcount: int = 1) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


def _assert_balance_sql(test: unittest.TestCase, query: str) -> None:
    normalized = " ".join(query.split())
    test.assertIn("SUM(c.profit)", normalized)
    test.assertIn("c.settled = 1", normalized)
    test.assertIn("SUM(c.stake_amount)", normalized)
    test.assertIn("c.settled = 0", normalized)
    test.assertIn("AS current_balance", normalized)
    test.assertIn("AS open_stake", normalized)
    test.assertIn("AS realized_pnl", normalized)


class TestGetByUsername(unittest.TestCase):
    """SELECT joins users with bankrolls and computes balances in SQL."""

    @patch(_GET_CONN)
    def test_joins_users_and_returns_bankroll_document(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn, row=_JOINED_ROW)
        document = repo.get_by_username("alice")
        self.assertIsNotNone(document)
        self.assertEqual(document, {
            "user_id": 7,
            "username": "alice",
            "display_name": "Alice",
            "is_system": 0,
            "currency": "PLN",
            "initial_capital": 1000.00,
            "unit_size": 10.00,
            "current_balance": 850.00,
            "open_stake": 20.00,
            "realized_pnl": -150.00})
        for key in (
                "initial_capital",
                "unit_size",
                "current_balance",
                "open_stake",
                "realized_pnl"):
            self.assertIsInstance(document[key], float)
        query, params = cursor.execute.call_args.args
        self.assertIn("FROM users u", query)
        self.assertIn("INNER JOIN tipster_bankrolls tb", query)
        self.assertIn("ON tb.user_id = u.id", query)
        self.assertIn("WHERE u.username = %s", query)
        _assert_balance_sql(self, query)
        self.assertEqual(params, ("alice",))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_missing_row_returns_none(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row=None)
        self.assertIsNone(repo.get_by_username("missing"))

    @patch(_GET_CONN)
    def test_db_error_closes_cursor_and_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("connection lost")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.get_by_username("alice")
        self.assertIs(ctx.exception, error)
        cursor.close.assert_called_once()


class TestGetBankroll(unittest.TestCase):
    """SELECT by user_id returns BankrollSettings with SQL balances."""

    @patch(_GET_CONN)
    def test_filters_user_id_and_computes_balances(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn, row=_BANKROLL_ROW)
        document = repo.get_bankroll(7)
        self.assertIsNotNone(document)
        self.assertEqual(document, {
            "user_id": 7,
            "currency": "PLN",
            "initial_capital": 1000.00,
            "unit_size": 10.00,
            "current_balance": 850.00,
            "open_stake": 20.00,
            "realized_pnl": -150.00})
        self.assertIsInstance(document["initial_capital"], float)
        self.assertIsInstance(document["realized_pnl"], float)
        query, params = cursor.execute.call_args.args
        self.assertIn("FROM tipster_bankrolls tb", query)
        self.assertIn("WHERE tb.user_id = %s", query)
        _assert_balance_sql(self, query)
        self.assertEqual(params, (7,))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_missing_row_returns_none(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row=None)
        self.assertIsNone(repo.get_bankroll(7))


class TestUpsertBankroll(unittest.TestCase):
    """INSERT is idempotent on users.id primary key."""

    def _assert_upsert_sql(self, query: str) -> None:
        self.assertIn("INSERT INTO tipster_bankrolls", query)
        self.assertIn("user_id, currency, initial_capital, unit_size", query)
        self.assertIn("VALUES (%s, %s, %s, %s)", query)
        self.assertIn("ON DUPLICATE KEY UPDATE", query)
        self.assertIn("currency = VALUES(currency)", query)
        self.assertIn("initial_capital = VALUES(initial_capital)", query)
        self.assertIn("unit_size = VALUES(unit_size)", query)

    @patch(_GET_CONN)
    def test_inserts_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        repo.upsert_bankroll(7, "PLN", 1000.00, 10.00)
        query, params = cursor.execute.call_args.args
        self._assert_upsert_sql(query)
        self.assertEqual(params, (7, "PLN", 1000.00, 10.00))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_second_upsert_does_not_duplicate_pk(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        repo.upsert_bankroll(7, "PLN", 1000.00, 10.00)
        repo.upsert_bankroll(7, "EUR", 500.00, 5.00)
        self.assertEqual(cursor.execute.call_count, 2)
        for call in cursor.execute.call_args_list:
            self._assert_upsert_sql(call.args[0])
        second_params = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(second_params, (7, "EUR", 500.00, 5.00))
        self.assertEqual(conn.commit.call_count, 2)

    @patch(_GET_CONN)
    def test_db_error_does_not_commit_and_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("deadlock")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.upsert_bankroll(7, "PLN", 1000.00, 10.00)
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


class TestAddToInitialCapital(unittest.TestCase):
    """Top-up adds to initial_capital and returns SQL balances."""

    @patch(_GET_CONN)
    def test_updates_capital_and_returns_bankroll(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            row={
                **_BANKROLL_ROW,
                "initial_capital": Decimal("1100.00"),
                "current_balance": Decimal("950.00")})
        document = repo.add_to_initial_capital(7, 100.00)
        self.assertIsNotNone(document)
        self.assertEqual(document["initial_capital"], 1100.00)
        self.assertEqual(document["current_balance"], 950.00)
        self.assertEqual(document["user_id"], 7)
        self.assertIsInstance(document["initial_capital"], float)
        update_query, update_params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE tipster_bankrolls", update_query)
        self.assertIn(
            "SET initial_capital = initial_capital + %s",
            update_query)
        self.assertIn("WHERE user_id = %s", update_query)
        self.assertEqual(update_params, (100.00, 7))
        select_query, select_params = cursor.execute.call_args_list[1].args
        self.assertIn("FROM tipster_bankrolls tb", select_query)
        _assert_balance_sql(self, select_query)
        self.assertEqual(select_params, (7,))
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_missing_row_returns_none_without_commit(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=None, rowcount=0)
        document = repo.add_to_initial_capital(7, 100.00)
        self.assertIsNone(document)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        self.assertEqual(cursor.execute.call_count, 1)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_db_error_does_not_commit_and_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("lock wait timeout")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.add_to_initial_capital(7, 100.00)
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
