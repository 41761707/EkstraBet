"""Unit tests for match repository daily query bounds."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.repositories import match_repository


class TestFetchDailyMatches(unittest.TestCase):
    """Verify half-open day range and indexed date filter."""

    @patch("backend.repositories.match_repository.pd.read_sql")
    @patch("backend.repositories.match_repository.get_db_connection")
    def test_fetch_daily_matches_uses_half_open_range_without_cast(
        self,
        mock_get_conn: MagicMock,
        mock_read_sql: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm
        mock_read_sql.return_value = pd.DataFrame()

        frame = match_repository.fetch_daily_matches(date(2026, 7, 26))

        self.assertTrue(frame.empty)
        args = mock_read_sql.call_args
        query = args.args[0]
        self.assertNotIn("CAST(m.game_date AS DATE)", query)
        self.assertIn("m.game_date >= %s", query)
        self.assertIn("m.game_date < %s", query)
        self.assertIn("l.active = 1", query)
        self.assertIn("ORDER BY s.id ASC, l.name ASC, m.game_date ASC", query)
        self.assertEqual(
            args.kwargs["params"],
            (datetime(2026, 7, 26, 0, 0), datetime(2026, 7, 27, 0, 0)))


class TestFetchTeamMatchesBeforeDate(unittest.TestCase):
    """Verify season filter and optional limit for team history."""

    def _mock_connection(self, mock_get_conn: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm

    @patch("backend.repositories.match_repository.pd.read_sql")
    @patch("backend.repositories.match_repository.get_db_connection")
    def test_filters_by_season_and_omits_limit_when_unlimited(
        self,
        mock_get_conn: MagicMock,
        mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()
        kickoff = datetime(2026, 3, 15, 18, 0)

        frame = match_repository.fetch_team_matches_before_date(
            team_id=490,
            before_game_date=kickoff,
            exclude_match_id=100,
            season_id=12,
            limit=None)

        self.assertTrue(frame.empty)
        args = mock_read_sql.call_args
        query = args.args[0]
        self.assertIn("m.season = %s", query)
        self.assertNotIn("LIMIT", query)
        self.assertEqual(
            args.kwargs["params"],
            (490, 490, kickoff, 100, 12))

    @patch("backend.repositories.match_repository.pd.read_sql")
    @patch("backend.repositories.match_repository.get_db_connection")
    def test_keeps_default_limit_without_season_filter(
        self,
        mock_get_conn: MagicMock,
        mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()
        kickoff = datetime(2026, 3, 15, 18, 0)

        match_repository.fetch_team_matches_before_date(
            team_id=490,
            before_game_date=kickoff,
            exclude_match_id=100)

        args = mock_read_sql.call_args
        query = args.args[0]
        self.assertNotIn("m.season = %s", query)
        self.assertIn("LIMIT %s", query)
        self.assertEqual(
            args.kwargs["params"],
            (490, 490, kickoff, 100, match_repository.MAX_MATCH_HISTORY))


if __name__ == "__main__":
    unittest.main()
