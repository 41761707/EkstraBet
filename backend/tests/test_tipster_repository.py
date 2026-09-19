"""Unit tests for tipster bankroll and coupon repository SQL contracts."""

from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError
from mysql.connector.errors import IntegrityError

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

_CREATED_AT = datetime(2026, 9, 19, 12, 0, 0)


def _coupon_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": 10,
        "user_id": 7,
        "stake_amount": Decimal("20.00"),
        "stake_units": Decimal("2.0000"),
        "stake_input_mode": "units",
        "combined_odds": Decimal("1.9000"),
        "settled": 0,
        "outcome": None,
        "profit": None,
        "created_at": _CREATED_AT}
    row.update(overrides)
    return row


def _leg_payload(
        match_id: int,
        event_ids: list[int],
        odds: float,
        *,
        bookmaker_id: int | None = 1,
        source: str = "catalog") -> dict[str, object]:
    return {
        "match_id": match_id,
        "event_ids": event_ids,
        "odds": odds,
        "bookmaker_id": bookmaker_id,
        "source": source}


def _leg_sql_row(
        *,
        leg_id: int,
        coupon_id: int,
        match_id: int,
        event_id: int | None,
        odds: Decimal = Decimal("1.9000"),
        bookmaker_id: int | None = 1,
        source: str = "catalog",
        outcome: int | None = None) -> dict[str, object]:
    return {
        "leg_id": leg_id,
        "coupon_id": coupon_id,
        "match_id": match_id,
        "odds": odds,
        "bookmaker_id": bookmaker_id,
        "source": source,
        "outcome": outcome,
        "event_id": event_id}


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        rowcount: int = 1,
        lastrowid: int = 1,
        fetchall_results: list[list[dict[str, object]]] | None = None
        ) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    if fetchall_results is None:
        cursor.fetchall.return_value = []
    else:
        cursor.fetchall.side_effect = fetchall_results
    cursor.rowcount = rowcount
    cursor.lastrowid = lastrowid
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


def _script_coupon_inserts(
        cursor: MagicMock,
        *,
        coupon_id: int = 10,
        leg_ids: list[int] | None = None,
        fail_on: str | None = None,
        fail_at: int = 1,
        error: Exception | None = None) -> None:
    """Set lastrowid per INSERT and optionally fail a later statement."""
    remaining_legs = iter(leg_ids or [20])
    seen = {"coupon": 0, "leg": 0, "event": 0}
    failure = error or MySQLError("insert failed")

    def execute(query: str, params: object = None) -> None:
        if "INSERT INTO tipster_coupons" in query:
            seen["coupon"] += 1
            if fail_on == "coupon" and seen["coupon"] >= fail_at:
                raise failure
            cursor.lastrowid = coupon_id
            return
        if "INSERT INTO tipster_coupon_legs" in query:
            seen["leg"] += 1
            if fail_on == "leg" and seen["leg"] >= fail_at:
                raise failure
            cursor.lastrowid = next(remaining_legs)
            return
        if "INSERT INTO tipster_coupon_leg_events" in query:
            seen["event"] += 1
            if fail_on == "event" and seen["event"] >= fail_at:
                raise failure
            return

    cursor.execute.side_effect = execute


def _sql_calls(
        cursor: MagicMock, snippet: str) -> list[tuple[object, ...]]:
    return [
        call.args
        for call in cursor.execute.call_args_list
        if snippet in call.args[0]]


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


class TestInsertCoupon(unittest.TestCase):
    """Coupon + legs + events share one transaction and combined_odds snapshot."""

    def _insert_combined(self) -> dict[str, object]:
        return repo.insert_coupon(
            7,
            20.0,
            2.0,
            "units",
            [_leg_payload(100, [6, 12], 1.9, source="custom_odds")])

    def _insert_two_legs(self) -> dict[str, object]:
        return repo.insert_coupon(
            7,
            20.0,
            2.0,
            "units",
            [
                _leg_payload(100, [1], 1.8),
                _leg_payload(101, [6], 2.0)])

    @patch(_GET_CONN)
    def test_combined_leg_stores_one_odds_and_two_events(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, row=_coupon_row())
        _script_coupon_inserts(cursor)
        document = self._insert_combined()
        coupon_calls = _sql_calls(cursor, "INSERT INTO tipster_coupons")
        self.assertEqual(len(coupon_calls), 1)
        self.assertEqual(
            coupon_calls[0][1], (7, 20.0, 2.0, "units", 1.9))
        leg_calls = _sql_calls(cursor, "INSERT INTO tipster_coupon_legs")
        self.assertEqual(len(leg_calls), 1)
        self.assertEqual(
            leg_calls[0][1], (10, 100, 1.9, 1, "custom_odds"))
        event_calls = _sql_calls(
            cursor, "INSERT INTO tipster_coupon_leg_events")
        self.assertEqual(
            [call[1] for call in event_calls], [(20, 6), (20, 12)])
        self.assertEqual(document["id"], 10)
        self.assertEqual(document["combined_odds"], 1.9)
        self.assertEqual(len(document["legs"]), 1)
        self.assertEqual(document["legs"][0]["event_ids"], [6, 12])
        self.assertEqual(document["legs"][0]["odds"], 1.9)
        self.assertIsInstance(document["combined_odds"], float)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_combined_odds_is_product_of_leg_odds(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            row=_coupon_row(combined_odds=Decimal("3.6000")))
        _script_coupon_inserts(cursor, leg_ids=[20, 21])
        document = self._insert_two_legs()
        coupon_params = _sql_calls(
            cursor, "INSERT INTO tipster_coupons")[0][1]
        self.assertEqual(coupon_params[4], 3.6)
        self.assertEqual(len(_sql_calls(
            cursor, "INSERT INTO tipster_coupon_legs")), 2)
        self.assertEqual(document["combined_odds"], 3.6)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch(_GET_CONN)
    def test_second_leg_error_rolls_back_without_commit(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("second leg failed")
        _script_coupon_inserts(
            cursor, leg_ids=[20, 21], fail_on="leg", fail_at=2, error=error)
        with self.assertRaises(MySQLError) as ctx:
            self._insert_two_legs()
        self.assertIs(ctx.exception, error)
        self.assertEqual(
            len(_sql_calls(cursor, "INSERT INTO tipster_coupons")), 1)
        self.assertEqual(
            len(_sql_calls(cursor, "INSERT INTO tipster_coupon_legs")), 2)
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_leg_event_error_rolls_back_and_leaves_no_coupon(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("leg event insert failed")
        _script_coupon_inserts(
            cursor, fail_on="event", fail_at=2, error=error)
        with self.assertRaises(MySQLError) as ctx:
            self._insert_combined()
        self.assertIs(ctx.exception, error)
        self.assertEqual(
            len(_sql_calls(cursor, "INSERT INTO tipster_coupons")), 1)
        self.assertEqual(
            len(_sql_calls(
                cursor, "INSERT INTO tipster_coupon_leg_events")), 2)
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_duplicate_match_integrity_error_rolls_back(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        error = IntegrityError(
            "Duplicate entry for key 'coupon_id'", 1062)
        _script_coupon_inserts(
            cursor, leg_ids=[20, 21], fail_on="leg", fail_at=2, error=error)
        with self.assertRaises(IntegrityError) as ctx:
            repo.insert_coupon(
                7,
                20.0,
                2.0,
                "units",
                [
                    _leg_payload(100, [1], 1.8),
                    _leg_payload(100, [6], 2.0)])
        self.assertIs(ctx.exception, error)
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        cursor.close.assert_called_once()


class TestFetchCoupons(unittest.TestCase):
    """History is paginated; nested event_ids reconstruct a combined leg."""

    @patch(_GET_CONN)
    def test_paginates_and_nests_combined_events(
            self,
            mock_get_conn: MagicMock) -> None:
        coupon = _coupon_row(combined_odds=Decimal("2.5000"))
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 3},
            fetchall_results=[
                [coupon],
                [
                    _leg_sql_row(
                        leg_id=20,
                        coupon_id=10,
                        match_id=100,
                        event_id=6,
                        odds=Decimal("2.5000"),
                        source="custom_odds"),
                    _leg_sql_row(
                        leg_id=20,
                        coupon_id=10,
                        match_id=100,
                        event_id=12,
                        odds=Decimal("2.5000"),
                        source="custom_odds")]])
        items, total = repo.fetch_coupons(7, 0, 2, 10)
        self.assertEqual(total, 3)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], 10)
        self.assertEqual(items[0]["combined_odds"], 2.5)
        self.assertEqual(len(items[0]["legs"]), 1)
        self.assertEqual(items[0]["legs"][0]["event_ids"], [6, 12])
        self.assertIsInstance(items[0]["stake_amount"], float)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("SELECT COUNT(*) AS total", count_query)
        self.assertIn("FROM tipster_coupons", count_query)
        self.assertIn("user_id = %s", count_query)
        self.assertIn("settled = %s", count_query)
        self.assertNotIn("is_system", count_query)
        self.assertEqual(count_params, (7, 0))
        list_query, list_params = cursor.execute.call_args_list[1].args
        self.assertIn("ORDER BY created_at DESC, id DESC", list_query)
        self.assertIn("LIMIT %s OFFSET %s", list_query)
        self.assertEqual(list_params, (7, 0, 10, 10))
        legs_query, legs_params = cursor.execute.call_args_list[2].args
        self.assertIn("FROM tipster_coupon_legs l", legs_query)
        self.assertIn("LEFT JOIN tipster_coupon_leg_events e", legs_query)
        self.assertIn("WHERE l.coupon_id IN (%s)", legs_query)
        self.assertEqual(legs_params, (10,))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_settled_none_omits_settled_filter(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 0},
            fetchall_results=[[]])
        items, total = repo.fetch_coupons(7, None, 1, 20)
        self.assertEqual(items, [])
        self.assertEqual(total, 0)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertNotIn("settled = %s", count_query)
        self.assertEqual(count_params, (7,))
        list_query, list_params = cursor.execute.call_args_list[1].args
        self.assertEqual(list_params, (7, 20, 0))
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertIn("LIMIT %s OFFSET %s", list_query)

    @patch(_GET_CONN)
    def test_empty_page_skips_legs_query(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 0},
            fetchall_results=[[]])
        items, total = repo.fetch_coupons(7, 1, 1, 10)
        self.assertEqual(items, [])
        self.assertEqual(total, 0)
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertEqual(
            _sql_calls(cursor, "tipster_coupon_legs"), [])

    @patch(_GET_CONN)
    def test_groups_legs_per_coupon_on_the_page(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 2},
            fetchall_results=[
                [
                    _coupon_row(id=11, combined_odds=Decimal("2.0000")),
                    _coupon_row(id=10)],
                [
                    _leg_sql_row(
                        leg_id=21,
                        coupon_id=11,
                        match_id=200,
                        event_id=1,
                        odds=Decimal("2.0000")),
                    _leg_sql_row(
                        leg_id=20,
                        coupon_id=10,
                        match_id=100,
                        event_id=6)]])
        items, total = repo.fetch_coupons(7, None, 1, 10)
        self.assertEqual(total, 2)
        self.assertEqual([item["id"] for item in items], [11, 10])
        self.assertEqual(items[0]["legs"][0]["event_ids"], [1])
        self.assertEqual(items[1]["legs"][0]["event_ids"], [6])
        legs_query, legs_params = cursor.execute.call_args_list[2].args
        self.assertIn("WHERE l.coupon_id IN (%s, %s)", legs_query)
        self.assertEqual(legs_params, (11, 10))

    @patch(_GET_CONN)
    def test_db_error_closes_cursor_and_propagates(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn)
        error = MySQLError("connection lost")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.fetch_coupons(7, None, 1, 10)
        self.assertIs(ctx.exception, error)
        cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
