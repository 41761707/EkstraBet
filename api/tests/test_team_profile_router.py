"""API tests for team profile endpoint."""

from __future__ import annotations
import os
import unittest
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app


class TestTeamProfileRouter(unittest.TestCase):
    """HTTP contract tests for team profile endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_team_profile_accepts_optional_season_id(self) -> None:
        with patch(
            "api.routers.teams.team_service.get_team_profile",
            return_value={
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
                "season_id": None,
                "league_id": None,
                "form": [],
                "recent_matches": [],
                "overall_stats": {
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_conceded": 0,
                    "goal_difference": 0,
                    "points": 0,
                },
                "home_stats": {
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_conceded": 0,
                    "goal_difference": 0,
                    "points": 0,
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
                "season_matches": [],
                "head_to_head": None,
            }) as _mock_get_profile:
            response = self.client.get("/teams/10/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["team"]["name"], "Legia")

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
                "round_label": "5",
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
            "season_matches": [],
            "head_to_head": None,
        }
        response = self.client.get(
            "/teams/10/profile?season_id=12&league_id=1&limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team"]["name"], "Legia")
        self.assertEqual(payload["form"], ["W"])
        self.assertEqual(payload["overall_stats"]["points"], 3)

    @patch("api.routers.teams.team_service.get_team_profile")
    def test_team_profile_season_matches_include_foul_fields(
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
            "recent_matches": [],
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
            "season_matches": [{
                "match_id": 101,
                "match_date": datetime(2025, 4, 1, 18, 0),
                "opponent_shortcut": "LPO",
                "opponent_name": "Lech",
                "total_goals": 3,
                "btts": True,
                "result": "W",
                "home_team_name": "Legia",
                "away_team_name": "Lech",
                "home_goals": 2,
                "away_goals": 1,
                "is_home": True,
                "team_cards": 2,
                "opponent_cards": 2,
                "total_cards": 4,
                "team_offsides": 2,
                "opponent_offsides": 1,
                "total_offsides": 3,
                "team_corners": 7,
                "opponent_corners": 4,
                "total_corners": 11,
                "team_shots": 14,
                "opponent_shots": 9,
                "total_shots": 23,
                "team_shots_on_target": 6,
                "opponent_shots_on_target": 3,
                "total_shots_on_target": 9,
                "team_fouls": 11,
                "opponent_fouls": 14,
                "total_fouls": 25,
            }],
            "head_to_head": None,
        }
        response = self.client.get("/teams/10/profile?season_id=12")
        self.assertEqual(response.status_code, 200)
        match_point = response.json()["season_matches"][0]
        self.assertEqual(match_point["team_fouls"], 11)
        self.assertEqual(match_point["opponent_fouls"], 14)
        self.assertEqual(match_point["total_fouls"], 25)


if __name__ == "__main__":
    unittest.main()
