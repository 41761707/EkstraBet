"""SQL contract for event-advisor history, slip leagues and the pool."""

from __future__ import annotations

import ast
import re
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError

from backend.repositories import event_advisor_repository as repo
from backend.repositories.tipster_repository import FOOTBALL_SPORT_ID
from backend.services.tipster_service import MIN_ODDS


_NOW = datetime(2026, 10, 30, 12, 0)
_HORIZON = datetime(2026, 11, 6, 12, 0)
_SINCE = datetime(2026, 5, 3, 12, 0)
_FINGERPRINT = "a" * 64
_GET_CONN = (
    "backend.repositories.event_advisor_repository.get_db_connection")
_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "TRUNCATE")


def _sql(query: str) -> str:
    """Collapse whitespace so assertions do not depend on wrapping."""
    return " ".join(query.split())


def _window_params() -> tuple[object, ...]:
    """Shared football window, then the caller-specific tail."""
    return (
        _NOW,
        _HORIZON,
        FOOTBALL_SPORT_ID,
        "1",
        "X",
        "2")


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        rows: list[dict[str, object]] | None = None) -> MagicMock:
    """Wire get_db_connection to one dictionary cursor."""
    cursor = MagicMock()
    cursor.fetchall.return_value = [] if rows is None else rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    mock_get_conn.return_value = context
    return cursor


def _assert_read_only(test: unittest.TestCase, query: str) -> None:
    """Reject a write statement inside a suggestion read."""
    text = _sql(query).upper()
    test.assertNotIn(";", text)
    for word in _WRITE_WORDS:
        test.assertNotIn(word, text)


def _candidate(**overrides: object) -> dict[str, object]:
    """One published pool row before the Python filter."""
    row: dict[str, object] = {
        "match_id": 10,
        "event_id": 1,
        "event_name": "Zwycięstwo gospodarza",
        "league_id": 7,
        "league_name": "K League",
        "home_name": "Seoul",
        "away_name": "Jeonbuk",
        "kickoff": datetime(2026, 10, 31, 12, 0),
        "odds": Decimal("1.85"),
        "bookmaker_id": 3,
        "probability_pct": 55.0}
    row.update(overrides)
    return row


class TestFetchHistory(unittest.TestCase):
    """History is this user's coupons, one row per event on the leg."""

    @patch(_GET_CONN)
    def test_empty_history_returns_empty_list(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(repo.fetch_history(7, _SINCE), [])

    @patch(_GET_CONN)
    def test_query_filters_user_and_created_at(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(mock_get_conn, rows=[])
        repo.fetch_history(7, _SINCE)
        query, params = cursor.execute.call_args.args
        text = _sql(query)
        self.assertIn("tipster_coupons c", text)
        self.assertIn("tipster_coupon_legs l", text)
        self.assertIn("tipster_coupon_leg_events e", text)
        self.assertIn("c.user_id = %s", text)
        self.assertIn("c.created_at >= %s", text)
        self.assertIn(
            "COUNT(*) OVER (PARTITION BY l.id) AS event_count_on_leg",
            text)
        self.assertEqual(params, (7, _SINCE))
        _assert_read_only(self, query)
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_maps_leg_price_and_event_count(
            self,
            mock_get_conn: MagicMock) -> None:
        row = {
            "league_id": 2,
            "event_id": 7,
            "odds": Decimal("1.80"),
            "event_count_on_leg": 2}
        _mock_connection(mock_get_conn, rows=[row])
        found = repo.fetch_history(7, _SINCE)
        self.assertEqual(
            found,
            [{
                "league_id": 2,
                "event_id": 7,
                "odds": 1.80,
                "event_count_on_leg": 2}])

    @patch(_GET_CONN)
    def test_blank_cell_is_omitted(
            self,
            mock_get_conn: MagicMock) -> None:
        row = {
            "league_id": None,
            "event_id": 7,
            "odds": 1.80,
            "event_count_on_leg": 1}
        _mock_connection(mock_get_conn, rows=[row])
        self.assertEqual(repo.fetch_history(7, _SINCE), [])

    @patch(_GET_CONN)
    def test_db_error_closes_cursor(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(mock_get_conn)
        error = MySQLError("connection lost")
        cursor.execute.side_effect = error
        with self.assertRaises(MySQLError) as ctx:
            repo.fetch_history(7, _SINCE)
        self.assertIs(ctx.exception, error)
        cursor.close.assert_called_once()


class TestFetchSlipLeagues(unittest.TestCase):
    """Draft leagues come from matches.league and skip unknown ids."""

    def test_empty_ids_do_not_open_a_connection(self) -> None:
        with patch(_GET_CONN) as connection:
            self.assertEqual(repo.fetch_slip_leagues([]), {})
        connection.assert_not_called()

    @patch(_GET_CONN)
    def test_query_reads_league_for_each_id(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(
            mock_get_conn,
            rows=[
                {"match_id": 10, "league_id": 2},
                {"match_id": 11, "league_id": None}])
        found = repo.fetch_slip_leagues([10, 11, 10])
        query, params = cursor.execute.call_args.args
        text = _sql(query)
        self.assertIn("m.league AS league_id", text)
        self.assertIn("m.id IN (%s, %s)", text)
        self.assertEqual(params, (10, 11))
        self.assertEqual(found, {10: 2})
        _assert_read_only(self, query)


class TestFetchCandidates(unittest.TestCase):
    """The pool is the catalog window plus a published probability."""

    @patch(_GET_CONN)
    def test_query_uses_the_half_open_football_window(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(mock_get_conn, rows=[])
        self.assertEqual(repo.fetch_candidates(_NOW, _HORIZON), [])
        query, params = cursor.execute.call_args.args
        text = _sql(query)
        self.assertIn("mk.game_date >= %s", text)
        self.assertIn("mk.game_date < %s", text)
        self.assertIn("mk.sport_id = %s", text)
        self.assertNotIn("sport_id = 1", text)
        self.assertIn(
            "mk.result IS NULL OR mk.result NOT IN (%s, %s, %s)",
            text)
        self.assertIn("FROM final_predictions fp", text)
        self.assertIn("AVG(p.value) AS probability_pct", text)
        self.assertIn("l.name AS league_name", text)
        self.assertIn("t1.name AS home_name", text)
        self.assertIn("t2.name AS away_name", text)
        self.assertIn("o.odds >= %s", text)
        window = text.split("ROW_NUMBER() OVER (", 1)[1]
        window = window.split(") AS rn", 1)[0]
        self.assertIn("PARTITION BY o.match_id, o.event", window)
        self.assertIn("ORDER BY o.odds DESC, o.id ASC", window)
        self.assertIn("WHERE ranked.rn = 1", text)
        self.assertEqual(params, _window_params() + (MIN_ODDS,))
        self.assertEqual(text.count("%s"), len(params))
        _assert_read_only(self, query)

    @patch(_GET_CONN)
    def test_maps_unit_probability_and_catalog_names(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(mock_get_conn, rows=[_candidate()])
        found = repo.fetch_candidates(_NOW, _HORIZON)
        self.assertEqual(len(found), 1)
        row = found[0]
        self.assertEqual(row["match_id"], 10)
        self.assertEqual(row["event_id"], 1)
        self.assertEqual(row["league_name"], "K League")
        self.assertEqual(row["home_name"], "Seoul")
        self.assertEqual(row["away_name"], "Jeonbuk")
        self.assertAlmostEqual(row["odds"], 1.85)
        self.assertAlmostEqual(row["model_probability"], 0.55)
        self.assertNotIn("has_computer_bet", row)

    @patch(_GET_CONN)
    def test_drops_unsettleable_event(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(
            mock_get_conn,
            rows=[_candidate(
                event_id=173,
                event_name="Dokładna liczba goli")])
        self.assertEqual(repo.fetch_candidates(_NOW, _HORIZON), [])

    @patch(_GET_CONN)
    def test_keeps_endpoint_probabilities(
            self,
            mock_get_conn: MagicMock) -> None:
        _mock_connection(
            mock_get_conn,
            rows=[
                _candidate(event_id=1, probability_pct=0.0),
                _candidate(event_id=2, probability_pct=100.0)])
        found = repo.fetch_candidates(_NOW, _HORIZON)
        self.assertEqual(
            [row["model_probability"] for row in found],
            [0.0, 1.0])


class TestFetchComputerBetPairs(unittest.TestCase):
    """A bet flag is a pair inside the same window, not a model file."""

    @patch(_GET_CONN)
    def test_query_filters_decision_and_fingerprint(
            self,
            mock_get_conn: MagicMock) -> None:
        cursor = _mock_connection(
            mock_get_conn,
            rows=[
                {"match_id": 10, "event_id": 1},
                {"match_id": 10, "event_id": 1}])
        found = repo.fetch_computer_bet_pairs(
            _FINGERPRINT, _NOW, _HORIZON)
        query, params = cursor.execute.call_args.args
        text = _sql(query)
        self.assertIn("betting_recommendations br", text)
        self.assertIn("br.decision = %s", text)
        self.assertIn("br.model_fingerprint = %s", text)
        self.assertIn("mk.game_date >= %s", text)
        self.assertIn("mk.game_date < %s", text)
        self.assertEqual(
            params,
            _window_params() + ("bet", _FINGERPRINT))
        self.assertEqual(found, {(10, 1)})
        _assert_read_only(self, query)
        self.assertNotIn("model.joblib", text.lower())


class TestRepositoryStaysReadOnly(unittest.TestCase):
    """The module does not score, write, or call the coupon selector."""

    def test_source_does_not_score_or_select(self) -> None:
        path = Path(repo.__file__)
        source = path.read_text(encoding="utf-8")
        for word in _WRITE_WORDS:
            self.assertIsNone(
                re.search(rf"\b{word}\b", source, re.IGNORECASE))
        self.assertNotIn("model.joblib", source)
        self.assertNotIn("select_coupon", source)
        self.assertNotIn("publish_daily", source)
        self.assertNotIn("assign_tiers", source)
        self.assertNotIn("ready_model_fingerprint", source)
        tree = ast.parse(source)
        imported = _imported_modules(tree)
        self.assertNotIn(
            "backend.services.event_advisor_math", imported)
        self.assertNotIn(
            "backend.services.coupon_agent_service", imported)


def _imported_modules(tree: ast.AST) -> list[str]:
    """Return every imported module name."""
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


if __name__ == "__main__":
    unittest.main()
