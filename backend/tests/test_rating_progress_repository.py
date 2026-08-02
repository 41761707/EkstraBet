"""Unit tests for rating progress repository context loading."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories import rating_progress_repository as repo


class TestFetchRatingProgressContext(unittest.TestCase):
    """Verify context assembly, missing rows and finished-match filters."""

    def _mock_connection(self, mock_get_conn: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_returns_none_when_league_missing(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()

        result = repo.fetch_rating_progress_context(999, 12)

        self.assertIsNone(result)
        self.assertEqual(mock_read_sql.call_count, 1)

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_returns_none_when_season_missing(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.side_effect = [
            pd.DataFrame([{
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "country_id": 1,
                "country_name": "Polska",
                "sport_id": 1,
                "tier": 1
            }]),
            pd.DataFrame()
        ]

        result = repo.fetch_rating_progress_context(1, 999)

        self.assertIsNone(result)
        self.assertEqual(mock_read_sql.call_count, 2)

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_returns_empty_matches_when_season_has_no_finished_games(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        participants = pd.DataFrame([{
            "team_id": 3,
            "team_name": "Lech Poznań",
            "team_shortcut": "LPO"
        }])
        mock_read_sql.side_effect = [
            pd.DataFrame([{
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "country_id": 1,
                "country_name": "Polska",
                "sport_id": 1,
                "tier": 1
            }]),
            pd.DataFrame([{"years": "2025/26"}]),
            participants,
            pd.DataFrame()
        ]

        result = repo.fetch_rating_progress_context(1, 12)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.league_id, 1)
        self.assertEqual(result.season_years, "2025/26")
        self.assertEqual(len(result.participants), 1)
        self.assertTrue(result.matches.empty)
        self.assertIsNone(result.last_played_match_id)
        self.assertIsNone(result.last_played_at)
        self.assertEqual(mock_read_sql.call_count, 4)

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_loads_country_matches_with_cutoff_and_order(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        cutoff = datetime(2025, 8, 10, 18, 0)
        matches = pd.DataFrame([{
            "id": 10,
            "league": 1,
            "season": 12,
            "round": 1,
            "game_date": datetime(2025, 7, 20, 18, 0),
            "home_team": 3,
            "away_team": 5,
            "home_team_goals": 2,
            "away_team_goals": 1,
            "result": "1",
            "sport_id": 1,
            "tier": 1
        }, {
            "id": 20,
            "league": 21,
            "season": 12,
            "round": 1,
            "game_date": datetime(2025, 8, 10, 18, 0),
            "home_team": 100,
            "away_team": 101,
            "home_team_goals": 0,
            "away_team_goals": 0,
            "result": "X",
            "sport_id": 1,
            "tier": 2
        }])
        mock_read_sql.side_effect = [
            pd.DataFrame([{
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "country_id": 1,
                "country_name": "Polska",
                "sport_id": 1,
                "tier": 1
            }]),
            pd.DataFrame([{"years": "2025/26"}]),
            pd.DataFrame([{
                "team_id": 3,
                "team_name": "Lech Poznań",
                "team_shortcut": "LPO"
            }, {
                "team_id": 5,
                "team_name": "Legia Warszawa",
                "team_shortcut": "LEG"
            }]),
            pd.DataFrame([{
                "id": 50,
                "game_date": cutoff
            }]),
            matches
        ]

        result = repo.fetch_rating_progress_context(1, 12)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.last_played_match_id, 50)
        self.assertEqual(result.last_played_at, cutoff)
        self.assertEqual(len(result.matches), 2)
        self.assertEqual(result.matches.iloc[0]["id"], 10)
        self.assertEqual(result.tier, 1)
        self.assertEqual(result.sport_id, 1)

        last_query = mock_read_sql.call_args_list[-1].args[0]
        last_params = mock_read_sql.call_args_list[-1].kwargs["params"]
        self.assertIn("l.country = %s", last_query)
        self.assertIn("m.result IN (%s, %s, %s)", last_query)
        self.assertIn("m.home_team IS NOT NULL", last_query)
        self.assertIn("m.game_date IS NOT NULL", last_query)
        self.assertIn("ORDER BY m.game_date ASC, m.id ASC", last_query)
        self.assertIn("m.game_date < %s", last_query)
        self.assertIn("m.game_date = %s AND m.id <= %s", last_query)
        self.assertNotIn(f"l.country = {1}", last_query)
        self.assertEqual(
            last_params,
            (1, 1, 1, "1", "X", "2", cutoff, cutoff, 50))

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_rejects_league_with_null_country(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "league_id": 1,
            "league_name": "Broken",
            "country_id": None,
            "country_name": None,
            "sport_id": 1,
            "tier": 1
        }])

        result = repo.fetch_rating_progress_context(1, 12)

        self.assertIsNone(result)


class TestFetchCountryRatingProgressContext(unittest.TestCase):
    """Country-wide context assembly."""

    def _mock_connection(self, mock_get_conn: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_returns_none_when_country_missing(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame()
        self.assertIsNone(
            repo.fetch_country_rating_progress_context(999, 12))

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_builds_country_label_and_cutoff_matches(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        cutoff = datetime(2025, 8, 10, 18, 0, 0)
        participants = pd.DataFrame([{
            "team_id": 1,
            "team_name": "Alpha",
            "team_shortcut": "ALP"
        }])
        matches = pd.DataFrame([{
            "id": 10,
            "league": 1,
            "season": 12,
            "round": 1,
            "game_date": cutoff,
            "home_team": 1,
            "away_team": 2,
            "home_team_goals": 1,
            "away_team_goals": 0,
            "result": "1",
            "sport_id": 1,
            "tier": 1
        }])
        mock_read_sql.side_effect = [
            pd.DataFrame([{
                "country_id": 1,
                "country_name": "Polska"
            }]),
            pd.DataFrame([{"years": "2025/26"}]),
            participants,
            pd.DataFrame([{
                "id": 50,
                "game_date": cutoff
            }]),
            matches
        ]

        result = repo.fetch_country_rating_progress_context(1, 12)

        assert result is not None
        self.assertEqual(result.league_id, 1)
        self.assertEqual(result.league_name, "Polska — wszystkie ligi")
        self.assertEqual(result.country_id, 1)
        self.assertEqual(result.last_played_match_id, 50)
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(len(result.participants), 1)


class TestFetchHelpers(unittest.TestCase):
    """Cover helper edge cases for NULL and empty frames."""

    def _mock_connection(self, mock_get_conn: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_last_finished_match_returns_none_for_null_date(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{
            "id": 7,
            "game_date": None
        }])

        result = repo._fetch_last_finished_match(1, 12)

        self.assertIsNone(result)

    @patch("backend.repositories.rating_progress_repository.pd.read_sql")
    @patch(
        "backend.repositories.rating_progress_repository.get_db_connection")
    def test_season_years_returns_none_for_null_label(
            self,
            mock_get_conn: MagicMock,
            mock_read_sql: MagicMock) -> None:
        self._mock_connection(mock_get_conn)
        mock_read_sql.return_value = pd.DataFrame([{"years": None}])

        result = repo._fetch_season_years(12)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
