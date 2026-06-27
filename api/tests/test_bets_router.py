"""API tests for bet recommendation endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import date, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestBetsRouter(unittest.TestCase):
    """HTTP contract tests for bets endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_get_recommendations_rejects_invalid_date_range(self) -> None:
        response = self.client.get(
            "/bets/recommendations",
            params={
                "date_from": "2026-06-10",
                "date_to": "2026-06-01",
            })
        self.assertEqual(response.status_code, 422)

    def test_get_recommendations_rejects_invalid_id_list(self) -> None:
        response = self.client.get(
            "/bets/recommendations",
            params={"league_ids": "1,abc"})
        self.assertEqual(response.status_code, 400)

    @patch("api.routers.bets.bet_service.get_bet_recommendations")
    def test_get_recommendations_returns_payload(
        self,
        mock_get_recommendations: unittest.mock.MagicMock) -> None:
        mock_get_recommendations.return_value = {
            "recommendations": [{
                "bet_id": 10,
                "match_id": 100,
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "season_id": 5,
                "game_date": datetime(2026, 6, 27, 18, 0, 0),
                "home_team": {
                    "id": 11,
                    "name": "Legia",
                    "shortcut": "LEG",
                },
                "away_team": {
                    "id": 12,
                    "name": "Lech",
                    "shortcut": "LPO",
                },
                "event_id": 1,
                "event_name": "1",
                "event_family": {"id": 2, "name": "REZULTAT"},
                "odds": 2.1,
                "probability": 0.55,
                "probability_pct": 55.0,
                "ev": 0.08,
                "ev_after_tax": None,
                "bookmaker_id": 4,
                "bookmaker_name": "STS",
                "model_id": 2,
                "model_name": "Model A",
                "settlement_status": "pending",
                "custom_bet": False,
            }],
            "total_count": 1,
            "filters_applied": {
                "match_date": date(2026, 6, 27).isoformat(),
                "positive_ev_only": True,
                "apply_tax": False,
            },
        }
        response = self.client.get(
            "/bets/recommendations",
            params={
                "match_date": "2026-06-27",
                "positive_ev_only": "true",
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["recommendations"][0]["ev"], 0.08)
        self.assertEqual(
            payload["recommendations"][0]["bookmaker_name"],
            "STS")


if __name__ == "__main__":
    unittest.main()
