"""API tests for league standings endpoint."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

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
                "points_adjustment": -4,
                "adjustment_reason": "Decyzja związku",
                "zone_kind": "champions_league",
                "zone_stage": "qualification"
            }],
            "zones": [{
                "position_from": 1,
                "position_to": 1,
                "zone_kind": "champions_league",
                "stage": "qualification",
                "band": "top",
                "label": "Awans – Liga Mistrzów (Kwalifikacje)",
                "sort_order": 1
            }]
        }
        response = self.client.get(
            "/leagues/1/standings?season_id=12&scope=overall")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        row = payload["standings"][0]
        self.assertEqual(row["points"], 3)
        self.assertEqual(row["points_adjustment"], -4)
        self.assertEqual(row["adjustment_reason"], "Decyzja związku")
        self.assertEqual(row["zone_kind"], "champions_league")
        self.assertEqual(row["zone_stage"], "qualification")
        self.assertEqual(len(payload["zones"]), 1)
        self.assertEqual(payload["zones"][0]["zone_kind"], "champions_league")
        self.assertEqual(payload["zones"][0]["stage"], "qualification")
        self.assertEqual(
            payload["zones"][0]["label"],
            "Awans – Liga Mistrzów (Kwalifikacje)")

    @patch("api.routers.leagues.standings_service.get_league_standings")
    def test_league_standings_home_returns_empty_zones(
        self,
        mock_get_standings: unittest.mock.MagicMock) -> None:
        mock_get_standings.return_value = {
            "league_id": 8,
            "season_id": 13,
            "scope": "home",
            "total_count": 1,
            "standings": [{
                "position": 1,
                "team_id": 73,
                "team_name": "Southampton",
                "played": 5,
                "wins": 3,
                "draws": 1,
                "losses": 1,
                "goals_for": 8,
                "goals_against": 4,
                "goal_difference": 4,
                "points": 10,
                "points_adjustment": 0,
                "adjustment_reason": None,
                "zone_kind": None,
                "zone_stage": None
            }]
        }
        response = self.client.get(
            "/leagues/8/standings?season_id=13&scope=home")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        row = payload["standings"][0]
        self.assertEqual(payload["zones"], [])
        self.assertEqual(row["points"], 10)
        self.assertEqual(row["points_adjustment"], 0)
        self.assertIsNone(row["adjustment_reason"])
        self.assertIsNone(row["zone_kind"])
        self.assertIsNone(row["zone_stage"])

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
