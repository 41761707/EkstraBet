"""Unit tests for sport league match SQL contracts."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.repositories import sport_league_repository


_GET_CONN = "backend.repositories.sport_league_repository.get_db_connection"
_READ_SQL = "backend.repositories.sport_league_repository.pd.read_sql"


def _mock_connection(mock_get_conn: MagicMock) -> None:
    """Wire get_db_connection as a context manager."""
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm


class TestFetchSportMatches(unittest.TestCase):
    """Basketball queries must use FT scores from matches, not bma.ot."""

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_basketball_query_omits_overtime_column(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        sport_league_repository.fetch_sport_matches(
            league_id=46,
            season_id=1,
            sport_id=sport_league_repository.BASKETBALL_SPORT_ID)

        query = mock_read_sql.call_args.args[0]
        self.assertNotIn("bma.ot", query)
        self.assertNotIn("basketball_matches_add", query)
        self.assertIn("m.home_team_goals", query)
        self.assertIn("m.away_team_goals", query)

    @patch(_READ_SQL)
    @patch(_GET_CONN)
    def test_hockey_query_still_joins_overtime_flags(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        _mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        sport_league_repository.fetch_sport_matches(
            league_id=1,
            season_id=1,
            sport_id=sport_league_repository.HOCKEY_SPORT_ID)

        query = mock_read_sql.call_args.args[0]
        self.assertIn("hockey_matches_add", query)
        self.assertIn("hma.OT AS hma_ot", query)


if __name__ == "__main__":
    unittest.main()
