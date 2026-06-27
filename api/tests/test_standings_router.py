"""API tests for league standings endpoint."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestStandingsRouter(unittest.TestCase):
    """HTTP contract tests for league standings endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_league_standings_requires_season_id(self) -> None:
        response = self.client.get("/leagues/1/standings")
        self.assertEqual(response.status_code, 422)

    @patch(
        "api.routers.leagues.standings_service.get_league_standings",
        return_value=None)
    def test_league_standings_returns_404_for_missing_league(
        self,
        _mock_get_standings: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999/standings?season_id=1")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.leagues.standings_service.get_league_standings")
    def test_league_standings_returns_traditional_rows(
        self,
        mock_get_standings: unittest.mock.MagicMock) -> None:
        mock_get_standings.return_value = {
            "league_id": 1,
            "season_id": 12,
            "scope": "overall",
            "total_count": 1,
            "standings": [{
                "position": 1,
                "team_id": 10,
                "team_name": "Legia",
                "played": 1,
                "wins": 1,
                "draws": 0,
                "losses": 0,
                "goals_for": 2,
                "goals_against": 1,
                "goal_difference": 1,
                "points": 3,
            }],
        }
        response = self.client.get(
            "/leagues/1/standings?season_id=12&scope=overall")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["standings"][0]["points"], 3)

    @patch("api.routers.leagues.standings_service.get_league_standings")
    def test_league_standings_returns_ou_btts_rows(
        self,
        mock_get_standings: unittest.mock.MagicMock) -> None:
        mock_get_standings.return_value = {
            "league_id": 1,
            "season_id": 12,
            "scope": "ou_btts",
            "total_count": 1,
            "standings": [{
                "position": 1,
                "team_id": 10,
                "team_name": "Legia",
                "played": 2,
                "btts_count": 1,
                "btts_percentage": 50.0,
                "over_1_5_count": 2,
                "over_1_5_percentage": 100.0,
                "over_2_5_count": 1,
                "over_2_5_percentage": 50.0,
                "over_3_5_count": 0,
                "over_3_5_percentage": 0.0,
            }],
        }
        response = self.client.get(
            "/leagues/1/standings?season_id=12&scope=ou_btts")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scope"], "ou_btts")
        self.assertEqual(payload["standings"][0]["btts_count"], 1)


if __name__ == "__main__":
    unittest.main()
