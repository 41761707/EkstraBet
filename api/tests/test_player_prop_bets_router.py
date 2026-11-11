"""API tests for hockey player-prop recommendation endpoints."""

from __future__ import annotations

import inspect
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app
from api.routers.bets import get_bet_recommendations


def _recommendation() -> dict[str, object]:
    """One valid player-prop row returned by the mocked service."""
    return {
        "line_id": 20,
        "player_id": 7,
        "player_name": "Connor McDavid",
        "line": 2.5,
        "match_id": 100,
        "league_id": 45,
        "league_name": "NHL",
        "season_id": 9,
        "game_date": datetime(2026, 11, 5, 19, 0, 0),
        "home_team": {"id": 11, "name": "Edmonton", "shortcut": "EDM"},
        "away_team": {"id": 12, "name": "Toronto", "shortcut": "TOR"},
        "event_id": 190,
        "event_name": "Powyżej 2.5 strzałów na bramkę (zawodnik)",
        "odds": 1.85,
        "probability": 0.55,
        "probability_pct": 55.0,
        "ev": 0.0175,
        "ev_after_tax": None,
        "bookmaker_id": 1,
        "bookmaker_name": "Superbet",
        "model_id": 13,
        "model_name": "HOCKEY_PLAYER_PROPS_V1",
        "settlement_status": "pending",
        "history": {
            "window": 5,
            "played": 3,
            "hits": 2,
            "points": [{"value": 1}, {"value": 3}, {"value": 4}],
        },
    }


class TestPlayerPropBetsRouter(unittest.TestCase):
    """HTTP contract tests for player-prop recommendations."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_rejects_history_window_outside_catalog(self) -> None:
        response = self.client.get(
            "/bets/player-recommendations",
            params={"history_window": 7})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "history_window must be 5 or 10")

    def test_rejects_date_from_after_date_to(self) -> None:
        response = self.client.get(
            "/bets/player-recommendations",
            params={
                "date_from": "2026-11-10",
                "date_to": "2026-11-01",
            })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "date_from cannot be later than date_to")

    @patch(
        "api.routers.bets.player_prop_bet_service"
        ".get_player_prop_recommendations")
    def test_returns_history_hits_and_played(
            self,
            mock_get_recommendations: MagicMock) -> None:
        mock_get_recommendations.return_value = {
            "recommendations": [_recommendation()],
            "total_count": 1,
            "filters_applied": {"history_window": 5},
        }
        response = self.client.get(
            "/bets/player-recommendations",
            params={"history_window": 5, "league_ids": "45"})
        self.assertEqual(response.status_code, 200)
        history = response.json()["recommendations"][0]["history"]
        self.assertEqual(history["hits"], 2)
        self.assertEqual(history["played"], 3)
        self.assertEqual(
            mock_get_recommendations.call_args.kwargs["history_window"],
            5)
        self.assertEqual(
            mock_get_recommendations.call_args.kwargs["league_ids"],
            [45])
        self.assertNotIn(
            "season_id",
            mock_get_recommendations.call_args.kwargs)

    def test_team_recommendations_have_no_history_window(self) -> None:
        signature = inspect.signature(get_bet_recommendations)
        self.assertNotIn("history_window", signature.parameters)

    def test_bets_info_lists_player_recommendations(self) -> None:
        response = self.client.get("/bets/")
        self.assertEqual(response.status_code, 200)
        endpoints = response.json()["endpoints"]
        self.assertIn(
            "GET /bets/player-recommendations - Player prop recommendations",
            endpoints)


if __name__ == "__main__":
    unittest.main()
