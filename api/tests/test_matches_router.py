"""API tests for match schedule and detail endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestMatchesRouter(unittest.TestCase):
    """HTTP contract tests for match detail endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch(
        "api.routers.matches.match_service.get_match_details",
        return_value=None)
    def test_get_match_details_returns_404_for_missing_match(
        self,
        _mock_get_details: unittest.mock.MagicMock) -> None:
        response = self.client.get("/matches/999999/details")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.matches.match_service.get_match_details")
    def test_get_match_details_returns_payload(
        self,
        mock_get_details: unittest.mock.MagicMock) -> None:
        mock_get_details.return_value = {
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
            "final_predictions": [{
                "prediction_id": 10,
                "event_id": 1,
                "event_name": "1",
                "event_family": {"id": 2, "name": "REZULTAT"},
                "model_id": 3,
                "model_name": "Model A",
                "value": 0.55,
                "outcome": 1,
            }],
            "odds": [{
                "id": 1,
                "match_id": 100,
                "bookmaker_id": 4,
                "bookmaker_name": "STS",
                "event_id": 1,
                "event_name": "1",
                "event_family": {"id": 2, "name": "REZULTAT"},
                "odds": 1.95,
            }],
            "stats": {
                "home_xg": 1.8,
                "away_xg": 1.1,
                "home_possession": 55,
                "away_possession": 45,
                "home_shots": 12,
                "away_shots": 8,
                "home_shots_on_goal": 5,
                "away_shots_on_goal": 3,
                "home_corners": 6,
                "away_corners": 4,
                "home_fouls": 11,
                "away_fouls": 14,
                "home_yellow_cards": 2,
                "away_yellow_cards": 3,
                "home_red_cards": 0,
                "away_red_cards": 1,
            },
        }
        response = self.client.get("/matches/100/details")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], 100)
        self.assertEqual(payload["home_team"]["name"], "Legia")
        self.assertEqual(len(payload["final_predictions"]), 1)

    def test_invalid_match_id_is_rejected(self) -> None:
        response = self.client.get("/matches/0/details")
        self.assertEqual(response.status_code, 422)

    def test_invalid_model_ids_format_returns_400(self) -> None:
        response = self.client.get("/matches/100/details?model_ids=abc")
        self.assertEqual(response.status_code, 400)


class TestLeagueMatchesRouter(unittest.TestCase):
    """HTTP contract tests for league match schedule endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_league_matches_requires_season_id(self) -> None:
        response = self.client.get("/leagues/1/matches")
        self.assertEqual(response.status_code, 422)

    @patch(
        "api.routers.leagues.match_service.get_league_matches",
        return_value=None)
    def test_league_matches_returns_404_for_missing_league(
        self,
        _mock_get_matches: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999/matches?season_id=1")
        self.assertEqual(response.status_code, 404)

    @patch(
        "api.routers.leagues.match_service.get_league_matches",
        return_value=[])
    def test_league_matches_returns_empty_list(
        self,
        _mock_get_matches: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/1/matches?season_id=12")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 0)
        self.assertEqual(payload["matches"], [])

    def test_league_matches_rejects_invalid_date_range(self) -> None:
        response = self.client.get(
            "/leagues/1/matches"
            "?season_id=12&date_from=2025-06-10&date_to=2025-06-01")
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
