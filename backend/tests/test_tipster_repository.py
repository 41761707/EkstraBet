"""Unit tests for tipster bankroll and coupon repository SQL contracts."""

from __future__ import annotations

import unittest
from datetime import date
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
        outcome: int | None = None,
        home_name: str | None = "Legia",
        away_name: str | None = "Lech",
        event_name: str | None = "BTTS tak") -> dict[str, object]:
    return {
        "leg_id": leg_id,
        "coupon_id": coupon_id,
        "match_id": match_id,
        "odds": odds,
        "bookmaker_id": bookmaker_id,
        "source": source,
        "outcome": outcome,
        "event_id": event_id,
        "event_name": event_name,
        "home_name": home_name,
        "away_name": away_name}


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
    # otwarta stawka schodzi z salda, nie tylko z osobnej kolumny
    balance_sql = normalized.split("AS current_balance", 1)[0]
    test.assertIn("SUM(c.stake_amount)", balance_sql)
    test.assertIn("c.settled = 0", balance_sql)


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
        self.assertIn("unit_size = VALUES(unit_size)", query)
        self.assertNotIn(
            "initial_capital = VALUES(initial_capital)", query)

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


class TestUpdateBankrollSettings(unittest.TestCase):
    """Existing-row PUT updates currency and unit, never capital."""

    @patch(_GET_CONN)
    def test_update_omits_initial_capital(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        repo.update_bankroll_settings(7, "EUR", 5.00)
        query, params = cursor.execute.call_args.args
        self.assertIn("UPDATE tipster_bankrolls", query)
        self.assertIn("SET currency = %s, unit_size = %s", query)
        self.assertIn("WHERE user_id = %s", query)
        self.assertNotIn("initial_capital", query)
        self.assertEqual(params, ("EUR", 5.00, 7))
        conn.commit.assert_called_once()
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
                        source="custom_odds",
                        event_name="BTTS tak"),
                    _leg_sql_row(
                        leg_id=20,
                        coupon_id=10,
                        match_id=100,
                        event_id=12,
                        odds=Decimal("2.5000"),
                        source="custom_odds",
                        event_name="Poniżej 2.5 goli")]])
        items, total = repo.fetch_coupons(7, 0, 2, 10)
        self.assertEqual(total, 3)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], 10)
        self.assertEqual(items[0]["combined_odds"], 2.5)
        self.assertEqual(len(items[0]["legs"]), 1)
        self.assertEqual(items[0]["legs"][0]["event_ids"], [6, 12])
        self.assertEqual(
            items[0]["legs"][0]["event_names"],
            ["BTTS tak", "Poniżej 2.5 goli"])
        self.assertEqual(items[0]["legs"][0]["home_name"], "Legia")
        self.assertEqual(items[0]["legs"][0]["away_name"], "Lech")
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
        self.assertIn("LEFT JOIN matches m", legs_query)
        self.assertIn("LEFT JOIN teams t1", legs_query)
        self.assertIn("LEFT JOIN tipster_coupon_leg_events e", legs_query)
        self.assertIn("LEFT JOIN events ev", legs_query)
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


class TestFetchOpenLegsForFinishedMatches(unittest.TestCase):
    """Settlement fetch covers finished open legs and crash-recovery coupons."""

    def _open_leg_row(self) -> dict[str, object]:
        return {
            "leg_id": 10,
            "coupon_id": 1,
            "match_id": 100,
            "leg_outcome": None,
            "event_id": 1,
            "event_name": "Zwycięstwo gospodarza",
            "family": "REZULTAT",
            "result": "1",
            "home_goals": 2,
            "away_goals": 1,
            "home_ck": 5,
            "away_ck": 4,
            "home_fouls": 12,
            "away_fouls": 10,
            "home_yc": 1,
            "away_yc": 1,
            "home_rc": 0,
            "away_rc": 0,
            "home_off": 2,
            "away_off": 1,
            "stake_amount": Decimal("10.00"),
            "combined_odds": Decimal("1.9000")}

    def _assert_settlement_fetch_sql(self, query: str) -> None:
        self.assertIn("FROM tipster_coupon_legs l", query)
        self.assertIn("INNER JOIN tipster_coupons c", query)
        self.assertIn("INNER JOIN tipster_coupon_leg_events e", query)
        self.assertIn("INNER JOIN matches m", query)
        self.assertIn("LEFT JOIN event_families ef", query)
        self.assertIn("c.settled = 0", query)
        self.assertIn("open_leg.outcome IS NULL", query)
        self.assertIn("open_match.result IN (%s, %s, %s)", query)
        self.assertIn("home_team_ck AS home_ck", query)
        self.assertIn("pending_leg.outcome IS NULL", query)

    @patch(_GET_CONN)
    def test_returns_dataframe_with_boxscore_aliases(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[self._open_leg_row()]])
        frame = repo.fetch_open_legs_for_finished_matches()
        self.assertEqual(list(frame["leg_id"]), [10])
        self.assertEqual(list(frame["home_ck"]), [5])
        query, params = cursor.execute.call_args.args
        self._assert_settlement_fetch_sql(query)
        self.assertEqual(params, ("1", "X", "2"))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_empty_result_has_expected_columns(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, fetchall_results=[[]])
        frame = repo.fetch_open_legs_for_finished_matches()
        self.assertTrue(frame.empty)
        self.assertIn("leg_id", frame.columns)
        self.assertIn("home_ck", frame.columns)
        self.assertIn("combined_odds", frame.columns)


class TestWriteLegOutcome(unittest.TestCase):
    """Leg writes are idempotent while outcome is still NULL."""

    @patch(_GET_CONN)
    def test_updates_only_null_outcome_and_commits(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        repo.write_leg_outcome(10, 1)
        query, params = cursor.execute.call_args.args
        self.assertIn("UPDATE tipster_coupon_legs", query)
        self.assertIn("SET outcome = %s", query)
        self.assertIn("WHERE id = %s", query)
        self.assertIn("AND outcome IS NULL", query)
        self.assertEqual(params, (1, 10))
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()


class TestCompleteCoupon(unittest.TestCase):
    """Coupon close is idempotent and refuses open legs."""

    @patch(_GET_CONN)
    def test_sets_settled_outcome_profit_when_all_legs_done(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn)
        updated = repo.complete_coupon(1)
        self.assertEqual(updated, 1)
        query, params = cursor.execute.call_args.args
        self.assertIn("UPDATE tipster_coupons", query)
        self.assertIn(
            "IF(MIN(outcome) = 1 AND MAX(outcome) = 1, 1, 0)",
            query)
        self.assertIn(
            "ROUND(c.stake_amount * (c.combined_odds - 1), 2)",
            query)
        self.assertIn("-c.stake_amount", query)
        self.assertIn("AND c.settled = 0", query)
        self.assertIn("NOT EXISTS", query)
        self.assertEqual(params, (1,))
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_returns_zero_when_update_is_noop(
            self,
            mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(mock_get_conn, rowcount=0)
        updated = repo.complete_coupon(1)
        self.assertEqual(updated, 0)
        conn.commit.assert_called_once()


def _leaderboard_sql_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "user_id": 7,
        "username": "alice",
        "display_name": "Alice",
        "is_system": 0,
        "currency": "PLN",
        "bets_count": 4,
        "won_count": 2,
        "accuracy_pct": Decimal("50.00"),
        "legs_count": 5,
        "legs_won": 3,
        "legs_won_on_lost_coupons": 1,
        "stake_total": Decimal("40.00"),
        "profit_total": Decimal("12.50"),
        "avg_profit": Decimal("3.13"),
        "avg_odds": Decimal("1.9000"),
        "roi_pct": Decimal("31.25"),
        "current_balance": Decimal("1012.50")}
    row.update(overrides)
    return row


class TestFetchLeaderboard(unittest.TestCase):
    """Public ranking joins bankrolls; coupon lists stay out of the payload."""

    def _assert_leaderboard_identity_sql(self, query: str) -> None:
        self.assertIn("FROM users u", query)
        self.assertIn("INNER JOIN tipster_bankrolls tb", query)
        self.assertIn("ON tb.user_id = u.id", query)
        self.assertIn("u.is_system", query)
        self.assertIn("tb.currency", query)
        self.assertIn("AS current_balance", query)
        self.assertIn("LEFT JOIN (", query)
        self.assertIn("ROUND(stats.avg_odds, 4)", query)
        self.assertIn("c.settled = 1", query)
        self.assertIn("tipster_coupon_legs l", query)
        self.assertIn("AVG(c.combined_odds) AS avg_odds", query)
        self.assertIn("coupons.avg_odds AS avg_odds", query)
        self.assertNotIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertNotIn("event_names", query)

    @patch(_GET_CONN)
    def test_empty_ranking_has_leaderboard_columns(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        frame, total = repo.fetch_leaderboard()
        self.assertTrue(frame.empty)
        self.assertEqual(total, 0)
        self.assertEqual(
            list(frame.columns),
            [
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
                "current_balance"])
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("SELECT COUNT(*) AS total", count_query)
        self.assertIn("INNER JOIN tipster_bankrolls tb", count_query)
        self.assertEqual(count_params, ())
        query, params = cursor.execute.call_args_list[1].args
        self._assert_leaderboard_identity_sql(query)
        self.assertNotIn("WHERE u.is_system", query)
        self.assertIn("ORDER BY profit_total DESC, u.id ASC", query)
        self.assertEqual(params, ())
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_includes_human_and_system_in_one_result(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 2},
            fetchall_results=[[
                _leaderboard_sql_row(),
                _leaderboard_sql_row(
                    user_id=8,
                    username="agent",
                    display_name="Agent",
                    is_system=1,
                    currency="EUR",
                    profit_total=Decimal("5.00"),
                    current_balance=Decimal("1005.00"))]])
        frame, total = repo.fetch_leaderboard({})
        self.assertEqual(total, 2)
        self.assertEqual(list(frame["user_id"]), [7, 8])
        self.assertEqual(list(frame["is_system"]), [0, 1])
        self.assertEqual(list(frame["username"]), ["alice", "agent"])
        self.assertEqual(list(frame["currency"]), ["PLN", "EUR"])
        self.assertNotIn("legs", frame.columns)
        self.assertNotIn("coupons", frame.columns)
        query = cursor.execute.call_args_list[1].args[0]
        self.assertNotIn("WHERE u.is_system", query)
        self.assertIsInstance(frame.iloc[0]["profit_total"], float)

    @patch(_GET_CONN)
    def test_sorts_by_profit_total_desc_by_default(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({"sort_by": "profit_total"})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("ORDER BY profit_total DESC, u.id ASC", query)
        self.assertNotIn("ORDER BY profit_total ASC", query)
        self.assertEqual(params, ())

    @patch(_GET_CONN)
    def test_sort_asc_and_page_limit(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({
            "sort_by": "roi_pct",
            "sort_order": "asc",
            "page": 2,
            "page_size": 10})
        count_query = cursor.execute.call_args_list[0].args[0]
        self.assertNotIn("LIMIT %s OFFSET %s", count_query)
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("ORDER BY roi_pct ASC, u.id ASC", query)
        self.assertIn("LIMIT %s OFFSET %s", query)
        self.assertEqual(params, (10, 10))

    @patch(_GET_CONN)
    def test_tier_filter_uses_exists_on_match_league(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({"tier": 1})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("EXISTS", query)
        self.assertIn("INNER JOIN leagues lg ON lg.id = m.league", query)
        self.assertIn("lg.tier = %s", query)
        self.assertIn("l.coupon_id = c.id", query)
        self.assertIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertNotIn("coupons.avg_odds AS avg_odds", query)
        self.assertEqual(params, (1, 1))
        self.assertNotIn("WHERE u.is_system", query)
        self.assertIn("INNER JOIN (", query)
        self.assertNotIn("LEFT JOIN (", query)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("INNER JOIN (", count_query)
        self.assertIn("lg.tier = %s", count_query)
        self.assertEqual(count_params, (1, 1))

    @patch(_GET_CONN)
    def test_is_system_and_league_filters_are_parameterized(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({
            "is_system": 1,
            "league_ids": [13, 16]})
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("WHERE u.is_system = %s", count_query)
        self.assertIn("INNER JOIN (", count_query)
        self.assertIn("m.league IN (%s, %s)", count_query)
        self.assertEqual(count_params, (13, 16, 13, 16, 1))
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("WHERE u.is_system = %s", query)
        self.assertIn("INNER JOIN (", query)
        self.assertNotIn("LEFT JOIN (", query)
        self.assertIn("m.league IN (%s, %s)", query)
        self.assertIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertNotIn("AVG(c.combined_odds)", query)
        self.assertEqual(params, (13, 16, 13, 16, 1))

    @patch(_GET_CONN)
    def test_zero_settled_agent_keeps_optional_metrics_none(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, _cursor = _mock_connection(
            mock_get_conn,
            row={"total": 2},
            fetchall_results=[[
                _leaderboard_sql_row(),
                _leaderboard_sql_row(
                    user_id=8,
                    username="agent",
                    display_name="Agent",
                    is_system=1,
                    bets_count=0,
                    won_count=0,
                    accuracy_pct=None,
                    stake_total=Decimal("0.00"),
                    profit_total=Decimal("0.00"),
                    avg_profit=None,
                    avg_odds=None,
                    legs_count=0,
                    legs_won=0,
                    legs_won_on_lost_coupons=0,
                    roi_pct=None,
                    current_balance=Decimal("1000.00"))]])
        frame, total = repo.fetch_leaderboard({})
        self.assertEqual(total, 2)
        self.assertEqual(list(frame["is_system"]), [0, 1])
        human = frame.iloc[0]
        agent = frame.iloc[1]
        self.assertEqual(human["bets_count"], 4)
        self.assertEqual(human["accuracy_pct"], 50.0)
        self.assertEqual(agent["bets_count"], 0)
        self.assertEqual(agent["legs_count"], 0)
        self.assertEqual(agent["legs_won"], 0)
        for column in (
                "accuracy_pct", "avg_odds", "avg_profit", "roi_pct"):
            self.assertIsNone(agent[column])
            self.assertNotEqual(str(agent[column]), "nan")
        self.assertEqual(str(frame["accuracy_pct"].dtype), "object")

    @patch(_GET_CONN)
    def test_event_family_filter_joins_mappings(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({"event_family": 4})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("EXISTS", query)
        self.assertIn("tipster_coupon_leg_events e", query)
        self.assertIn("efm.event_family_id = %s", query)
        self.assertIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertNotIn("coupons.avg_odds AS avg_odds", query)
        self.assertEqual(params, (4, 4))
        self.assertIn("INNER JOIN (", query)
        self.assertNotIn("LEFT JOIN (", query)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("INNER JOIN (", count_query)
        self.assertIn("efm.event_family_id = %s", count_query)
        self.assertEqual(count_params, (4, 4))

    @patch(_GET_CONN)
    def test_event_family_other_matches_unmapped_legs(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({
            "event_family": repo.UNMAPPED_EVENT_FAMILY_NAME})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("NOT EXISTS", query)
        self.assertIn("tipster_coupon_leg_events e", query)
        self.assertNotIn("efm.event_family_id = %s", query)
        self.assertEqual(params, ())
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("NOT EXISTS", count_query)
        self.assertEqual(count_params, ())

    @patch(_GET_CONN)
    def test_event_family_zero_matches_unmapped_legs(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(mock_get_conn)
        for family in (0, "0"):
            with self.subTest(event_family=family):
                repo.fetch_leaderboard({"event_family": family})
                query, params = cursor.execute.call_args.args
                self.assertIn("NOT EXISTS", query)
                self.assertIn("INNER JOIN (", query)
                self.assertNotIn("LEFT JOIN (", query)
                self.assertNotIn("efm.event_family_id = %s", query)
                self.assertEqual(params, ())
                count_query, count_params = (
                    cursor.execute.call_args_list[-2].args)
                self.assertIn("INNER JOIN (", count_query)
                self.assertIn("NOT EXISTS", count_query)
                self.assertEqual(count_params, ())

    @patch(_GET_CONN)
    def test_event_ids_filter_matching_legs_and_leg_odds(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_leaderboard({"event_ids": [6, 12]})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("tipster_coupon_leg_events e", query)
        self.assertIn("e.event_id IN (%s, %s)", query)
        self.assertIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertNotIn("coupons.avg_odds AS avg_odds", query)
        self.assertEqual(params, (6, 12, 6, 12))
        self.assertIn("INNER JOIN (", query)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("e.event_id IN (%s, %s)", count_query)
        self.assertEqual(count_params, (6, 12, 6, 12))

    @patch(_GET_CONN)
    def test_date_filters_use_coupon_created_at(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        date_from = date(2026, 9, 1)
        date_to = date(2026, 9, 30)
        repo.fetch_leaderboard({
            "date_from": date_from,
            "date_to": date_to})
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("CAST(c.created_at AS DATE) >= %s", query)
        self.assertIn("CAST(c.created_at AS DATE) <= %s", query)
        self.assertIn("coupons.avg_odds AS avg_odds", query)
        self.assertNotIn("leg_stats.avg_odds AS avg_odds", query)
        self.assertEqual(params, (date_from, date_to, date_from, date_to))
        self.assertIn("INNER JOIN (", query)
        self.assertNotIn("LEFT JOIN (", query)
        count_query, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("INNER JOIN (", count_query)
        self.assertIn("CAST(c.created_at AS DATE) >= %s", count_query)
        self.assertEqual(
            count_params, (date_from, date_to, date_from, date_to))


class TestFetchPerformance(unittest.TestCase):
    """Settled coupons roll up into family, league and country buckets."""

    def _fact(
            self,
            *,
            coupon_id: int,
            outcome: int,
            stake: str,
            profit: str,
            odds: str,
            league_id: int,
            league_name: str,
            league_tier: int,
            family_id: int | None,
            family_name: str | None,
            country_id: int | None = 1,
            country_name: str | None = "Polska",
            country_emoji: str | None = "🇵🇱",
            leg_id: int | None = None,
            leg_outcome: int | None = None,
            leg_odds: str | None = None) -> dict[str, object]:
        return {
            "coupon_id": coupon_id,
            "outcome": outcome,
            "stake_amount": Decimal(stake),
            "profit": Decimal(profit),
            "combined_odds": Decimal(odds),
            "leg_id": coupon_id if leg_id is None else leg_id,
            "leg_outcome": outcome if leg_outcome is None else leg_outcome,
            "leg_odds": Decimal(odds if leg_odds is None else leg_odds),
            "league_id": league_id,
            "league_name": league_name,
            "league_tier": league_tier,
            "country_id": country_id,
            "country_name": country_name,
            "country_emoji": country_emoji,
            "event_family_id": family_id,
            "event_family_name": family_name}

    @patch(_GET_CONN)
    def test_empty_history_has_none_best_worst(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        payload = repo.fetch_performance(7)
        self.assertEqual(payload["by_event_family"], [])
        self.assertEqual(payload["by_league"], [])
        self.assertEqual(payload["by_country"], [])
        self.assertIsNone(payload["best_event_family"])
        self.assertIsNone(payload["worst_event_family"])
        self.assertIsNone(payload["best_league"])
        self.assertIsNone(payload["worst_league"])
        self.assertIsNone(payload["best_country"])
        self.assertIsNone(payload["worst_country"])
        query, params = cursor.execute.call_args.args
        self.assertIn("FROM tipster_coupons c", query)
        self.assertIn("c.settled = 1", query)
        self.assertIn("LEFT JOIN event_families ef", query)
        self.assertIn("l.outcome AS leg_outcome", query)
        self.assertIn("l.odds AS leg_odds", query)
        self.assertIn("LEFT JOIN countries ct", query)
        self.assertEqual(params, (7,))

    @patch(_GET_CONN)
    def test_dedupes_combined_events_and_picks_best_worst(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, _cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[
                self._fact(
                    coupon_id=1,
                    outcome=1,
                    stake="10.00",
                    profit="9.00",
                    odds="1.9000",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=4,
                    family_name="BTTS"),
                self._fact(
                    coupon_id=1,
                    outcome=1,
                    stake="10.00",
                    profit="9.00",
                    odds="1.9000",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=3,
                    family_name="OU"),
                self._fact(
                    coupon_id=2,
                    outcome=0,
                    stake="10.00",
                    profit="-10.00",
                    odds="2.0000",
                    league_id=16,
                    league_name="Premier League",
                    league_tier=1,
                    family_id=2,
                    family_name="REZULTAT")]])
        payload = repo.fetch_performance(7)
        families = {
            item["event_family_name"]: item
            for item in payload["by_event_family"]}
        self.assertEqual(families["BTTS"]["count"], 1)
        self.assertEqual(families["BTTS"]["won"], 1)
        self.assertEqual(families["BTTS"]["legs_won"], 1)
        self.assertEqual(families["BTTS"]["legs_won_on_lost_coupons"], 0)
        self.assertEqual(families["BTTS"]["profit_total"], 9.0)
        self.assertEqual(families["OU"]["count"], 1)
        self.assertEqual(families["REZULTAT"]["count"], 1)
        self.assertEqual(families["REZULTAT"]["won"], 0)
        self.assertEqual(len(payload["by_league"]), 2)
        self.assertEqual(len(payload["by_country"]), 1)
        self.assertEqual(payload["by_country"][0]["country_name"], "Polska")
        self.assertEqual(payload["by_country"][0]["country_emoji"], "🇵🇱")
        self.assertEqual(payload["by_country"][0]["count"], 2)
        self.assertEqual(
            payload["best_event_family"]["event_family_name"], "BTTS")
        self.assertEqual(
            payload["worst_event_family"]["event_family_name"],
            "REZULTAT")
        self.assertEqual(payload["best_league"]["league_name"], "Ekstraklasa")
        self.assertEqual(
            payload["worst_league"]["league_name"], "Premier League")
        self.assertEqual(payload["best_country"]["country_name"], "Polska")
        self.assertNotIn("by_league_tier", payload)

    @patch(_GET_CONN)
    def test_two_league_parlay_keeps_full_profit_in_each_league(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, _cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[
                self._fact(
                    coupon_id=1,
                    outcome=0,
                    stake="10.00",
                    profit="-10.00",
                    odds="3.4000",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=2,
                    family_name="REZULTAT",
                    country_id=1,
                    country_name="Polska",
                    country_emoji="🇵🇱"),
                self._fact(
                    coupon_id=1,
                    outcome=0,
                    stake="10.00",
                    profit="-10.00",
                    odds="3.4000",
                    league_id=16,
                    league_name="Premier League",
                    league_tier=1,
                    family_id=4,
                    family_name="BTTS",
                    country_id=2,
                    country_name="Anglia",
                    country_emoji="🇬🇧")]])
        payload = repo.fetch_performance(7)
        leagues = {
            item["league_name"]: item
            for item in payload["by_league"]}
        self.assertEqual(leagues["Ekstraklasa"]["count"], 1)
        self.assertEqual(leagues["Ekstraklasa"]["profit_total"], -10.0)
        self.assertEqual(leagues["Ekstraklasa"]["stake_total"], 10.0)
        self.assertEqual(leagues["Premier League"]["profit_total"], -10.0)
        self.assertEqual(leagues["Premier League"]["stake_total"], 10.0)
        bucket_profit = sum(
            item["profit_total"] for item in payload["by_league"])
        self.assertEqual(bucket_profit, -20.0)
        self.assertNotEqual(bucket_profit, -10.0)
        countries = {
            item["country_name"]: item
            for item in payload["by_country"]}
        self.assertEqual(countries["Polska"]["count"], 1)
        self.assertEqual(countries["Polska"]["profit_total"], -10.0)
        self.assertEqual(countries["Anglia"]["profit_total"], -10.0)
        self.assertEqual(countries["Anglia"]["country_emoji"], "🇬🇧")

    @patch(_GET_CONN)
    def test_unmapped_event_family_uses_other_label(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, _cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[
                self._fact(
                    coupon_id=1,
                    outcome=1,
                    stake="10.00",
                    profit="8.50",
                    odds="1.8500",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=None,
                    family_name=None),
                self._fact(
                    coupon_id=2,
                    outcome=0,
                    stake="10.00",
                    profit="-10.00",
                    odds="1.9000",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=4,
                    family_name="BTTS")]])
        payload = repo.fetch_performance(7)
        families = {
            item["event_family_name"]: item
            for item in payload["by_event_family"]}
        other = families[repo.UNMAPPED_EVENT_FAMILY_NAME]
        self.assertIsNone(other["event_family_id"])
        self.assertEqual(other["count"], 1)
        self.assertEqual(other["profit_total"], 8.5)
        self.assertEqual(families["BTTS"]["count"], 1)
        self.assertEqual(
            payload["best_event_family"]["event_family_name"],
            repo.UNMAPPED_EVENT_FAMILY_NAME)
        self.assertIsNone(payload["best_event_family"]["event_family_id"])
        self.assertNotEqual(
            payload["best_event_family"]["event_family_name"], None)

    @patch(_GET_CONN)
    def test_lost_coupon_keeps_stake_and_counts_winning_leg(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, _cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[
                self._fact(
                    coupon_id=3,
                    outcome=0,
                    stake="2.50",
                    profit="-2.50",
                    odds="3.4200",
                    league_id=13,
                    league_name="Ekstraklasa",
                    league_tier=1,
                    family_id=4,
                    family_name="BTTS",
                    leg_id=4,
                    leg_outcome=1,
                    leg_odds="1.9000"),
                self._fact(
                    coupon_id=3,
                    outcome=0,
                    stake="2.50",
                    profit="-2.50",
                    odds="3.4200",
                    league_id=16,
                    league_name="Premier League",
                    league_tier=1,
                    family_id=3,
                    family_name="OU",
                    leg_id=5,
                    leg_outcome=0,
                    leg_odds="1.8000")]])
        payload = repo.fetch_performance(7)
        families = {
            item["event_family_name"]: item
            for item in payload["by_event_family"]}
        btts = families["BTTS"]
        self.assertEqual(btts["count"], 1)
        self.assertEqual(btts["won"], 0)
        self.assertEqual(btts["profit_total"], -2.5)
        self.assertEqual(btts["stake_total"], 2.5)
        self.assertEqual(btts["legs_count"], 1)
        self.assertEqual(btts["legs_won"], 1)
        self.assertEqual(btts["legs_accuracy"], 100.0)
        self.assertEqual(btts["legs_won_on_lost_coupons"], 1)
        self.assertEqual(btts["avg_odds"], 1.9)
        ou = families["OU"]
        self.assertEqual(ou["won"], 0)
        self.assertEqual(ou["profit_total"], -2.5)
        self.assertEqual(ou["legs_won"], 0)
        self.assertEqual(ou["legs_won_on_lost_coupons"], 0)
        self.assertEqual(ou["avg_odds"], 1.8)
        leagues = {
            item["league_name"]: item
            for item in payload["by_league"]}
        self.assertEqual(leagues["Ekstraklasa"]["avg_odds"], 1.9)
        self.assertEqual(leagues["Ekstraklasa"]["legs_won"], 1)
        self.assertEqual(leagues["Premier League"]["avg_odds"], 1.8)
        self.assertEqual(leagues["Premier League"]["legs_won"], 0)


class TestFetchSuggestedCatalogOdds(unittest.TestCase):
    """Default coupon price is the best odds of a predicted event."""

    @patch(_GET_CONN)
    def test_returns_highest_odds_when_a_prediction_exists(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, row={"odds": 2.2})
        odds = repo.fetch_suggested_catalog_odds(124426, 1, 1.01)
        self.assertEqual(odds, 2.2)
        query, params = cursor.execute.call_args.args
        self.assertIn("FROM odds o", query)
        self.assertIn("FROM predictions p", query)
        self.assertIn("ORDER BY o.odds DESC, o.id ASC", query)
        self.assertEqual(params, (124426, 1, 1.01))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_returns_none_without_a_stored_price(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, row=None)
        self.assertIsNone(
            repo.fetch_suggested_catalog_odds(124426, 8, 1.01))


class TestFetchCatalogMatches(unittest.TestCase):
    """Picker lists unfinished football matches and settleable events."""

    @patch(_GET_CONN)
    def test_excludes_finished_matches_and_unsupported_events(
            self,
            mock_get_conn: MagicMock) -> None:
        game_date = datetime(2026, 9, 20, 18, 0, 0)
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[
                [{
                    "id": 100,
                    "league_id": 13,
                    "league_name": "Ekstraklasa",
                    "league_tier": 1,
                    "game_date": game_date,
                    "result": "0",
                    "home_id": 1,
                    "home_name": "Legia",
                    "home_shortcut": "LEG",
                    "away_id": 2,
                    "away_name": "Lech",
                    "away_shortcut": "LCH"}],
                [
                    {"id": 1, "name": "Zwycięstwo gospodarza"},
                    {"id": 33, "name": "Powyżej 8.5 rożnych"},
                    {"id": 173, "name": "Dokładna liczba goli"},
                    {"id": 181, "name": "Strzelec bramki"}]])
        payload = repo.fetch_catalog_matches(None, None, None)
        self.assertEqual(len(payload["matches"]), 1)
        self.assertEqual(payload["matches"][0]["id"], 100)
        self.assertEqual(payload["matches"][0]["result"], "0")
        event_ids = [event["id"] for event in payload["events"]]
        self.assertIn(1, event_ids)
        self.assertIn(33, event_ids)
        self.assertNotIn(173, event_ids)
        self.assertNotIn(181, event_ids)
        match_query, match_params = cursor.execute.call_args_list[0].args
        self.assertIn("FROM matches m", match_query)
        self.assertIn(
            "m.result IS NULL OR m.result NOT IN (%s, %s, %s)",
            match_query)
        self.assertIn("m.sport_id = %s", match_query)
        self.assertIn("m.game_date >= CURRENT_TIMESTAMP", match_query)
        self.assertNotIn("CAST(m.game_date AS DATE) >= %s", match_query)
        self.assertEqual(
            match_params,
            ("1", "X", "2", repo.FOOTBALL_SPORT_ID))
        events_query = cursor.execute.call_args_list[1].args[0]
        self.assertIn("FROM events", events_query)
        self.assertEqual(cursor.execute.call_count, 2)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_date_and_league_filters_are_parameterized(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[], []])
        date_from = datetime(2026, 9, 19).date()
        date_to = datetime(2026, 9, 21).date()
        payload = repo.fetch_catalog_matches(date_from, date_to, [13, 16])
        self.assertEqual(payload["matches"], [])
        self.assertEqual(payload["events"], [])
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn("CAST(m.game_date AS DATE) >= %s", query)
        self.assertIn("CAST(m.game_date AS DATE) <= %s", query)
        self.assertIn("m.league IN (%s, %s)", query)
        self.assertIn("m.game_date >= CURRENT_TIMESTAMP", query)
        self.assertIn(
            "m.result IS NULL OR m.result NOT IN (%s, %s, %s)",
            query)
        self.assertEqual(
            params,
            ("1", "X", "2", repo.FOOTBALL_SPORT_ID, date_from, date_to, 13, 16))

    @patch(_GET_CONN)
    def test_past_unfinished_match_is_excluded_without_date_from(
            self,
            mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[], []])
        payload = repo.fetch_catalog_matches(None, None, None)
        self.assertEqual(payload["matches"], [])
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn(
            "m.result IS NULL OR m.result NOT IN (%s, %s, %s)",
            query)
        self.assertIn("m.game_date >= CURRENT_TIMESTAMP", query)
        self.assertNotIn("CAST(m.game_date AS DATE) >= %s", query)
        self.assertEqual(
            params, ("1", "X", "2", repo.FOOTBALL_SPORT_ID))


class TestApplyTaxProfitSql(unittest.TestCase):
    """Tax view scales winning payout; stored profit stays untouched."""

    @patch(_GET_CONN)
    def test_bankroll_uses_net_stake_on_wins_only(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, row=_BANKROLL_ROW)
        repo.get_bankroll(7, apply_tax=True)
        query = " ".join(cursor.execute.call_args.args[0].split())
        self.assertIn("combined_odds * 0.88 - 1", query)
        self.assertIn("-c.stake_amount", query)
        self.assertNotIn("SUM(c.profit)", query)
        self.assertIn("SUM(c.stake_amount)", query)
        self.assertIn("c.settled = 0", query)
        balance_sql = query.split("AS current_balance", 1)[0]
        self.assertIn("SUM(c.stake_amount)", balance_sql)
        self.assertIn("c.settled = 0", balance_sql)

    @patch(_GET_CONN)
    def test_default_bankroll_keeps_stored_profit(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, row=_BANKROLL_ROW)
        repo.get_bankroll(7)
        query = cursor.execute.call_args.args[0]
        self.assertIn("SUM(c.profit)", query)
        self.assertNotIn("0.88", query)

    @patch(_GET_CONN)
    def test_coupon_list_leaves_open_profit_null(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 0},
            fetchall_results=[[]])
        repo.fetch_coupons(7, None, 1, 20, apply_tax=True)
        list_query = cursor.execute.call_args_list[1].args[0]
        normalized = " ".join(list_query.split())
        self.assertIn(
            "IF(c.settled = 1, IF(c.outcome = 1,", normalized)
        self.assertIn("combined_odds * 0.88 - 1", normalized)
        self.assertIn("FROM tipster_coupons c", normalized)
        count_query = cursor.execute.call_args_list[0].args[0]
        self.assertNotIn("0.88", count_query)

    @patch(_GET_CONN)
    def test_leaderboard_profit_and_balance_use_the_tax(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            row={"total": 0},
            fetchall_results=[[]])
        repo.fetch_leaderboard({"apply_tax": True})
        list_query = " ".join(
            cursor.execute.call_args_list[1].args[0].split())
        self.assertEqual(list_query.count("combined_odds * 0.88 - 1"), 2)
        self.assertNotIn("SUM(c.profit)", list_query)

    @patch(_GET_CONN)
    def test_performance_facts_replace_stored_profit(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_performance(7, apply_tax=True)
        query = " ".join(cursor.execute.call_args.args[0].split())
        self.assertIn("combined_odds * 0.88 - 1", query)
        self.assertNotIn("c.profit,", query)
        self.assertIn("AS profit", query)


if __name__ == "__main__":
    unittest.main()
