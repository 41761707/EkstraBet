"""API tests for match schedule and detail endpoints."""

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


def _season_match_point(
    *,
    match_id: int,
    team_fouls: int,
    opponent_fouls: int,
    total_fouls: int,
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "match_date": datetime(2025, 3, 15, 18, 0),
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
        "team_fouls": team_fouls,
        "opponent_fouls": opponent_fouls,
        "total_fouls": total_fouls,
    }


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
            "sport_id": 1,
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
            "sport_id": 1,
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
                "home_goals": 2,
                "away_goals": 1,
                "home_xg": 1.8,
                "away_xg": 1.1,
                "home_possession": 55,
                "away_possession": 45,
                "home_shots": 12,
                "away_shots": 8,
                "home_shots_on_goal": 5,
                "away_shots_on_goal": 3,
                "home_free_kicks": 6,
                "away_free_kicks": 8,
                "home_corners": 6,
                "away_corners": 4,
                "home_offsides": 2,
                "away_offsides": 1,
                "home_fouls": 11,
                "away_fouls": 14,
                "home_yellow_cards": 2,
                "away_yellow_cards": 3,
                "home_red_cards": 0,
                "away_red_cards": 1,
            },
            "hockey_stats": None,
            "hockey_boxscore": None,
            "has_player_stats": False,
            "head_to_head": {
                "team_id": 10,
                "opponent_id": 20,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_conceded": 0,
                "btts_count": 0,
                "btts_percentage": 0.0,
                "avg_goals_per_match": 0.0,
                "meetings": [],
            },
            "home_team_history": [
                _season_match_point(
                    match_id=101,
                    team_fouls=11,
                    opponent_fouls=14,
                    total_fouls=25,
                ),
            ],
            "away_team_history": [
                _season_match_point(
                    match_id=102,
                    team_fouls=9,
                    opponent_fouls=13,
                    total_fouls=22,
                ),
            ],
            "boxscore": None,
            "model_assessments": [],
        }
        response = self.client.get("/matches/100/details")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], 100)
        self.assertEqual(payload["home_team"]["name"], "Legia")
        self.assertEqual(len(payload["final_predictions"]), 1)
        home_history = payload["home_team_history"][0]
        self.assertEqual(home_history["team_fouls"], 11)
        self.assertEqual(home_history["opponent_fouls"], 14)
        self.assertEqual(home_history["total_fouls"], 25)
        away_history = payload["away_team_history"][0]
        self.assertEqual(away_history["team_fouls"], 9)
        self.assertEqual(away_history["opponent_fouls"], 13)
        self.assertEqual(away_history["total_fouls"], 22)

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
