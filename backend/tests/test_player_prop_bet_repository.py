"""SQL contract for the player-prop recommendation page."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories import player_prop_bet_repository as repo


_GET_CONN = (
    "backend.repositories.player_prop_bet_repository"
    ".get_db_connection")
_READ_SQL = (
    "backend.repositories.player_prop_bet_repository.pd.read_sql")


def _mock_connection(mock_get_conn: MagicMock) -> None:
    """Wire get_db_connection as a context manager."""
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm


def _page(mock_read_sql: MagicMock, total: int = 1) -> None:
    """Return a count frame and one recommendation row."""
    mock_read_sql.side_effect = [
        pd.DataFrame([{"total": total}]),
        pd.DataFrame([{"line_id": 7}])]


def _sql_calls(mock_read_sql: MagicMock) -> tuple[str, str]:
    """Return the count SQL and the page SQL."""
    count_sql = mock_read_sql.call_args_list[0].args[0]
    page_sql = mock_read_sql.call_args_list[1].args[0]
    return count_sql, page_sql


class TestSearchPlayerPropRecommendations(unittest.TestCase):
    """Page SQL pairs lines with predictions and filters before LIMIT."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_page_sql_reads_lines_and_predictions(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        frame, total = repo.search_player_prop_recommendations()

        self.assertEqual(total, 1)
        self.assertEqual(int(frame.iloc[0]["line_id"]), 7)
        count_sql, page_sql = _sql_calls(mock_read_sql)
        for query in (count_sql, page_sql):
            self.assertIn("player_props_lines", query)
            self.assertIn("player_predictions", query)
            self.assertIn("ABS(", query)
            self.assertIn("hockey_match_player_stats", query)
            self.assertIn(
                "LEFT JOIN hockey_match_player_stats", query)
            self.assertIn(
                "ppl.event_id IN (190, 192, 194, 196)", query)
            self.assertNotIn("FROM bets", query)
            self.assertNotIn("JOIN bets", query)
            self.assertNotRegex(query, r"\b(FROM|JOIN)\s+odds\b")
        self.assertNotIn("ORDER BY", count_sql)
        self.assertNotIn("LIMIT", count_sql)
        self.assertIn("AS settlement_status", page_sql)
        self.assertIn("LIMIT %s OFFSET %s", page_sql)
        self.assertEqual(mock_read_sql.call_count, 2)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_events_outside_catalog_skip_the_query(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        frame, total = repo.search_player_prop_recommendations(
            event_ids=[191, 193, 195])

        self.assertTrue(frame.empty)
        self.assertEqual(total, 0)
        mock_get_conn.assert_not_called()
        mock_read_sql.assert_not_called()

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_outside_event_does_not_replace_catalog(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        repo.search_player_prop_recommendations(event_ids=[190, 191])

        count_sql, page_sql = _sql_calls(mock_read_sql)
        count_params = mock_read_sql.call_args_list[0].kwargs["params"]
        for query in (count_sql, page_sql):
            self.assertIn(
                "ppl.event_id IN (190, 192, 194, 196)", query)
            self.assertEqual(query.count("ppl.event_id IN"), 2)
            self.assertNotIn("191", query)
        self.assertEqual(count_params, (190,))
        self.assertNotIn(191, count_params)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_settlement_status_is_bound(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        repo.search_player_prop_recommendations(settlement_status="won")

        count_sql, _page_sql = _sql_calls(mock_read_sql)
        params = mock_read_sql.call_args_list[0].kwargs["params"]
        self.assertIn("= %s", count_sql)
        self.assertNotIn("= 'won'", count_sql)
        self.assertEqual(params, ("won",))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_settled_means_not_pending(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        repo.search_player_prop_recommendations(
            settlement_status="settled")

        count_sql, _page_sql = _sql_calls(mock_read_sql)
        params = mock_read_sql.call_args_list[0].kwargs["params"]
        self.assertIn("<> 'pending'", count_sql)
        self.assertNotIn("settled", count_sql)
        self.assertEqual(params, ())

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_filters_sort_and_page_params(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql, total=4)
        match_day = date(2026, 11, 11)

        frame, total = repo.search_player_prop_recommendations(
            league_ids=[45],
            event_ids=[196, 191],
            model_ids=[13],
            match_date=match_day,
            min_odds=1.5,
            positive_ev_only=True,
            apply_tax=True,
            tax_rate=0.12,
            settlement_status="lost",
            sort_by="probability",
            sort_order="asc",
            page=2,
            page_size=50)

        self.assertEqual(total, 4)
        self.assertEqual(len(frame), 1)
        count_sql, page_sql = _sql_calls(mock_read_sql)
        expected = (45, 196, 13, match_day, 1.5, 0.12, "lost")
        self.assertEqual(
            mock_read_sql.call_args_list[0].kwargs["params"],
            expected)
        self.assertEqual(
            mock_read_sql.call_args_list[1].kwargs["params"],
            expected + (50, 50))
        self.assertIn("m.league IN (%s)", count_sql)
        self.assertIn("pp.model_id IN (%s)", count_sql)
        self.assertIn("ppl.odds >= %s", count_sql)
        self.assertIn("(1 - %s)", count_sql)
        self.assertIn("CAST(m.game_date AS DATE) = %s", count_sql)
        self.assertIn("ORDER BY pp.probability ASC", page_sql)
        self.assertIn("ppl.id ASC, pp.model_id ASC", page_sql)
        self.assertNotIn("191", count_sql)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_from_now_ignores_exact_date(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        repo.search_player_prop_recommendations(
            match_date=date(2026, 11, 11),
            from_now=True)

        count_sql, page_sql = _sql_calls(mock_read_sql)
        params = mock_read_sql.call_args_list[0].kwargs["params"]
        self.assertIn("m.game_date >= CURRENT_TIMESTAMP", count_sql)
        self.assertNotIn("CAST(m.game_date AS DATE)", count_sql)
        self.assertEqual(params, ())
        self.assertIn(
            "ORDER BY (pp.probability / 100.0) * ppl.odds - 1 DESC",
            page_sql)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_unknown_sort_falls_back_to_ev_desc(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)

        repo.search_player_prop_recommendations(
            sort_by="odds; DROP TABLE",
            sort_order="asc; DROP TABLE")

        _count_sql, page_sql = _sql_calls(mock_read_sql)
        self.assertIn(
            "ORDER BY (pp.probability / 100.0) * ppl.odds - 1 DESC",
            page_sql)
        self.assertNotIn("DROP", page_sql)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_date_range_and_raw_positive_ev(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        _page(mock_read_sql)
        start = date(2026, 11, 1)
        end = date(2026, 11, 10)

        repo.search_player_prop_recommendations(
            date_from=start,
            date_to=end,
            positive_ev_only=True,
            apply_tax=False,
            sort_by="game_date",
            sort_order="asc")

        count_sql, page_sql = _sql_calls(mock_read_sql)
        self.assertEqual(
            mock_read_sql.call_args_list[0].kwargs["params"],
            (start, end))
        self.assertIn("CAST(m.game_date AS DATE) >= %s", count_sql)
        self.assertIn("CAST(m.game_date AS DATE) <= %s", count_sql)
        self.assertIn(
            "(pp.probability / 100.0) * ppl.odds - 1 > 0",
            count_sql)
        self.assertNotIn("(1 - %s)", count_sql)
        self.assertIn("ORDER BY m.game_date ASC", page_sql)
