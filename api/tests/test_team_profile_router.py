"""API tests for team profile endpoint."""

from __future__ import annotations
import os
import unittest
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestTeamProfileRouter(unittest.TestCase):
    """HTTP contract tests for team profile endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_team_profile_requires_season_id(self) -> None:
        response = self.client.get("/teams/10/profile")
        self.assertEqual(response.status_code, 422)

    @patch(
        "api.routers.teams.team_service.get_team_profile",
        return_value=None)
    def test_team_profile_returns_404_for_missing_team(
        self,
        _mock_get_profile: unittest.mock.MagicMock) -> None:
        response = self.client.get("/teams/999999/profile?season_id=12")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.teams.team_service.get_team_profile")
    def test_team_profile_returns_payload(
        self,
        mock_get_profile: unittest.mock.MagicMock) -> None:
        mock_get_profile.return_value = {
            "team": {
                "id": 10,
                "name": "Legia",
                "shortcut": "LEG",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": "🇵🇱",
                "sport_id": 1,
                "sport_name": "Football",
            },
            "season_id": 12,
            "league_id": 1,
            "form": ["W"],
            "recent_matches": [{
                "id": 100,
                "league_id": 1,
                "season_id": 12,
                "round": 5,
                "game_date": datetime(2025, 3, 15, 18, 0),
                "home_team": {
                    "id": 10,
                    "name": "Legia",
                    "shortcut": "LEG",
                },
                "away_team": {
                    "id": 20,
                    "name": "Lech",
                    "shortcut": "LPO",
                },
                "home_goals": 2,
                "away_goals": 1,
                "result": "1",
                "is_played": True,
            }],
            "overall_stats": {
                "played": 1,
                "wins": 1,
                "draws": 0,
                "losses": 0,
                "goals_for": 2,
                "goals_conceded": 1,
                "goal_difference": 1,
                "points": 3,
            },
            "home_stats": {
                "played": 1,
                "wins": 1,
                "draws": 0,
                "losses": 0,
                "goals_for": 2,
                "goals_conceded": 1,
                "goal_difference": 1,
                "points": 3,
            },
            "away_stats": {
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_conceded": 0,
                "goal_difference": 0,
                "points": 0,
            },
            "head_to_head": None,
        }
        response = self.client.get(
            "/teams/10/profile?season_id=12&league_id=1&limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team"]["name"], "Legia")
        self.assertEqual(payload["form"], ["W"])
        self.assertEqual(payload["overall_stats"]["points"], 3)


if __name__ == "__main__":
    unittest.main()
