"""Unit tests for standings service calculation."""

from __future__ import annotations
import unittest
from unittest.mock import patch
import pandas as pd
from backend.services.standings_service import get_league_standings


class TestStandingsService(unittest.TestCase):
    """Tests for league standings mapping and sorting."""

    def _teams_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team_id": 1, "team_name": "Alpha"},
            {"team_id": 2, "team_name": "Beta"},
        ])

    def _results_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "home_team_id": 1,
                "home_team_name": "Alpha",
                "away_team_id": 2,
                "away_team_name": "Beta",
                "home_team_goals": 2,
                "away_team_goals": 1,
                "result": "1",
            },
            {
                "home_team_id": 2,
                "home_team_name": "Beta",
                "away_team_id": 1,
                "away_team_name": "Alpha",
                "home_team_goals": 1,
                "away_team_goals": 1,
                "result": "X",
            },
        ])

    @patch(
        "backend.services.standings_service.league_repository.league_exists",
        return_value=False)
    def test_get_league_standings_returns_none_for_missing_league(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_league_standings(999999, 1))

    @patch(
        "backend.services.standings_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_league_results",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_teams_in_season",
        return_value=pd.DataFrame())
    def test_get_league_standings_returns_empty_table(
        self,
        _mock_teams: unittest.mock.MagicMock,
        _mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        payload = get_league_standings(1, 12)
        assert payload is not None
        self.assertEqual(payload["standings"], [])
        self.assertEqual(payload["scope"], "overall")

    @patch(
        "backend.services.standings_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_league_results")
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_teams_in_season")
    def test_get_league_standings_sorts_by_points(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="overall")
        assert payload is not None
        standings = payload["standings"]
        self.assertEqual(len(standings), 2)
        self.assertEqual(standings[0]["team_name"], "Alpha")
        self.assertEqual(standings[0]["points"], 4)
        self.assertEqual(standings[0]["position"], 1)

    @patch(
        "backend.services.standings_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_league_results")
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_teams_in_season")
    def test_get_league_standings_home_scope_counts_home_matches_only(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="home")
        assert payload is not None
        alpha = next(
            row for row in payload["standings"]
            if row["team_id"] == 1)
        beta = next(
            row for row in payload["standings"]
            if row["team_id"] == 2)
        self.assertEqual(alpha["played"], 1)
        self.assertEqual(beta["played"], 1)
        self.assertEqual(alpha["points"], 3)
        self.assertEqual(beta["points"], 1)

    @patch(
        "backend.services.standings_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_league_results")
    @patch(
        "backend.services.standings_service.standings_repository"
        ".fetch_teams_in_season")
    def test_get_league_standings_ou_btts_scope(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="ou_btts")
        assert payload is not None
        alpha = payload["standings"][0]
        self.assertEqual(alpha["team_name"], "Alpha")
        self.assertEqual(alpha["played"], 2)
        self.assertEqual(alpha["btts_count"], 2)
        self.assertEqual(alpha["over_2_5_count"], 1)


if __name__ == "__main__":
    unittest.main()
