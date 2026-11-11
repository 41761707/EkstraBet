"""SQL contract for the player-prop recommendation page."""

from __future__ import annotations

import unittest
from datetime import date, datetime
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


def _history_frame() -> pd.DataFrame:
    """Return one history row, newest match first."""
    return pd.DataFrame([{
        "player_id": 4,
        "anchor_match_id": 40,
        "match_id": 8,
        "game_date": datetime(2026, 11, 1, 18, 0),
        "stat_value": 3}])


class TestFetchRecentPlayerStats(unittest.TestCase):
    """History is one lateral query per stat column."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_empty_anchors_do_not_open_connection(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        frame = repo.fetch_recent_player_stats([], 10)

        self.assertTrue(frame.empty)
        mock_get_conn.assert_not_called()
        mock_read_sql.assert_not_called()

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_shots_use_one_lateral_query(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = _history_frame()
        kickoff = datetime(2026, 11, 11, 18, 0)
        later = datetime(2026, 11, 12, 1, 0)

        frame = repo.fetch_recent_player_stats(
            [
                (4, 40, kickoff, "sog"),
                (5, 50, later, "sog")],
            10)

        self.assertEqual(int(frame.iloc[0]["stat_value"]), 3)
        self.assertEqual(mock_read_sql.call_count, 1)
        mock_get_conn.assert_called_once()
        sql = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertIn("JOIN LATERAL", sql)
        self.assertIn("m.game_date < anchor.before_ts", sql)
        self.assertIn("s.match_id <> anchor.match_id", sql)
        self.assertIn("s.sog IS NOT NULL", sql)
        self.assertIn("s.sog AS stat_value", sql)
        self.assertIn(
            "ORDER BY m.game_date DESC, s.match_id DESC", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(sql.count("UNION ALL"), 1)
        self.assertNotIn("s.points", sql)
        self.assertNotIn("s.assists", sql)
        self.assertNotIn("s.goals", sql)
        self.assertNotIn("FROM bets", sql)
        self.assertEqual(
            params,
            (4, 40, kickoff, 5, 50, later, 10))
        self.assertEqual(frame["stat_column"].tolist(), ["sog"])
        self.assertNotIn("stat_column", sql)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_single_anchor_has_no_union(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = _history_frame()
        kickoff = datetime(2026, 11, 11, 18, 0)

        repo.fetch_recent_player_stats([(4, 40, kickoff, "sog")], 5)

        sql = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertNotIn("UNION ALL", sql)
        self.assertEqual(params, (4, 40, kickoff, 5))
        self.assertEqual(mock_read_sql.call_count, 1)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_each_column_is_one_query(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = [
            _history_frame(), _history_frame()]
        kickoff = datetime(2026, 11, 11, 18, 0)
        later = datetime(2026, 11, 12, 1, 0)

        frame = repo.fetch_recent_player_stats(
            [
                (4, 40, kickoff, "goals"),
                (5, 50, later, "sog"),
                (6, 60, kickoff, "goals")],
            5)

        self.assertEqual(len(frame), 2)
        self.assertEqual(mock_read_sql.call_count, 2)
        mock_get_conn.assert_called_once()
        goals_sql = mock_read_sql.call_args_list[0].args[0]
        shots_sql = mock_read_sql.call_args_list[1].args[0]
        self.assertIn("s.goals IS NOT NULL", goals_sql)
        self.assertNotIn("s.sog", goals_sql)
        self.assertEqual(goals_sql.count("UNION ALL"), 1)
        self.assertIn("s.sog IS NOT NULL", shots_sql)
        self.assertNotIn("s.goals", shots_sql)
        self.assertNotIn("UNION ALL", shots_sql)
        self.assertEqual(
            mock_read_sql.call_args_list[0].kwargs["params"],
            (4, 40, kickoff, 6, 60, kickoff, 5))
        self.assertEqual(
            mock_read_sql.call_args_list[1].kwargs["params"],
            (5, 50, later, 5))
        self.assertEqual(
            frame["stat_column"].tolist(), ["goals", "sog"])
        keys = list(zip(
            frame["player_id"],
            frame["anchor_match_id"],
            frame["stat_column"],
            frame["match_id"]))
        self.assertEqual(len(keys), len(set(keys)))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_repeated_model_anchor_is_queried_once(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.side_effect = [_history_frame(), _history_frame()]
        kickoff = datetime(2026, 11, 11, 18, 0)
        later = datetime(2026, 11, 12, 1, 0)

        frame = repo.fetch_recent_player_stats(
            [
                (4, 40, kickoff, "sog"),
                (4, 40, later, "sog"),
                (4, 40, kickoff, "goals")],
            5)

        self.assertEqual(len(frame), 2)
        self.assertEqual(mock_read_sql.call_count, 2)
        shots_sql = mock_read_sql.call_args_list[0].args[0]
        goals_sql = mock_read_sql.call_args_list[1].args[0]
        self.assertNotIn("UNION ALL", shots_sql)
        self.assertNotIn("UNION ALL", goals_sql)
        self.assertEqual(
            mock_read_sql.call_args_list[0].kwargs["params"],
            (4, 40, kickoff, 5))
        self.assertEqual(
            mock_read_sql.call_args_list[1].kwargs["params"],
            (4, 40, kickoff, 5))
        self.assertEqual(
            frame["stat_column"].tolist(), ["sog", "goals"])
        keys = list(zip(
            frame["player_id"],
            frame["anchor_match_id"],
            frame["stat_column"],
            frame["match_id"]))
        self.assertEqual(len(keys), len(set(keys)))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_unknown_column_raises(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        column = "sog; DROP TABLE matches"
        kickoff = datetime(2026, 11, 11, 18, 0)

        with self.assertRaises(ValueError) as caught:
            repo.fetch_recent_player_stats(
                [(4, 40, kickoff, column)], 10)

        self.assertEqual(
            str(caught.exception),
            f"Unknown player prop stat column: {column}")
        mock_get_conn.assert_not_called()
        mock_read_sql.assert_not_called()


class TestFetchMatchPlayerStats(unittest.TestCase):
    """Settlement reads the four prop columns for page pairs."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_empty_pairs_do_not_open_connection(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        frame = repo.fetch_match_player_stats([])

        self.assertTrue(frame.empty)
        mock_get_conn.assert_not_called()
        mock_read_sql.assert_not_called()

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_reads_four_columns_in_one_query(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "player_id": 4,
            "match_id": 40,
            "sog": 3,
            "points": 1,
            "assists": 1,
            "goals": 0}])

        frame = repo.fetch_match_player_stats([(4, 40), (5, 50)])

        self.assertEqual(int(frame.iloc[0]["sog"]), 3)
        self.assertEqual(mock_read_sql.call_count, 1)
        sql = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertIn("hockey_match_player_stats", sql)
        self.assertIn("s.sog", sql)
        self.assertIn("s.points", sql)
        self.assertIn("s.assists", sql)
        self.assertIn("s.goals", sql)
        self.assertEqual(sql.count("UNION ALL"), 1)
        self.assertNotIn("JOIN LATERAL", sql)
        self.assertNotIn("FROM bets", sql)
        self.assertEqual(params, (4, 40, 5, 50))

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_repeated_pair_is_read_once(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "player_id": 4,
            "match_id": 40,
            "sog": 3,
            "points": 1,
            "assists": 1,
            "goals": 0}])

        repo.fetch_match_player_stats([(4, 40), (5, 50), (4, 40)])

        self.assertEqual(mock_read_sql.call_count, 1)
        sql = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertEqual(sql.count("UNION ALL"), 1)
        self.assertEqual(params, (4, 40, 5, 50))
