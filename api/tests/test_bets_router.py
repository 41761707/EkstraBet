"""API tests for bet recommendation endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

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
        mock_get_recommendations: MagicMock) -> None:
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
                "match_id": 100,
                "match_date": date(2026, 6, 27).isoformat(),
                "positive_ev_only": True,
                "apply_tax": False,
            },
        }
        response = self.client.get(
            "/bets/recommendations",
            params={
                "match_id": 100,
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
        self.assertEqual(
            mock_get_recommendations.call_args.kwargs["match_id"], 100)

    def test_get_opportunities_rejects_match_date_with_range(self) -> None:
        response = self.client.get(
            "/bets/opportunities",
            params={
                "sport_id": 1,
                "match_date": "2026-07-26",
                "date_from": "2026-07-26",
            })
        self.assertEqual(response.status_code, 422)

    def test_get_opportunities_requires_sport_id(self) -> None:
        response = self.client.get("/bets/opportunities")
        self.assertEqual(response.status_code, 422)

    @patch("api.routers.bets.bet_service.get_market_opportunities")
    def test_get_opportunities_returns_payload(
        self,
        mock_get_opportunities: MagicMock) -> None:
        mock_get_opportunities.return_value = {
            "opportunities": [{
                "match_id": 100,
                "sport_id": 1,
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "game_date": datetime(2026, 7, 26, 18, 0, 0),
                "home_team": "Legia",
                "away_team": "Lech",
                "event_id": 8,
                "event_name": "Powyzej 2.5 gola",
                "model_id": 2,
                "model_name": "Model A",
                "probability": 0.55,
                "probability_pct": 55.0,
                "odds": 2.1,
                "bookmaker_id": 4,
                "bookmaker_name": "STS",
                "implied_probability": 1 / 2.1,
                "ev": 0.155,
                "ev_after_tax": 0.0164,
                "source": "bet",
                "ranking_basis": "ev_after_tax",
            }],
            "total_count": 1,
            "filters_applied": {
                "sport_id": 1,
                "match_date": "2026-07-26",
                "from_now": True,
                "one_per_match": True,
                "limit": 10,
            },
            "source_counts": {"bet": 1, "prediction": 0},
            "warnings": [],
        }
        response = self.client.get(
            "/bets/opportunities",
            params={
                "sport_id": 1,
                "match_date": "2026-07-26",
                "from_now": "true",
                "limit": 10,
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["opportunities"][0]["source"], "bet")
        self.assertEqual(
            mock_get_opportunities.call_args.kwargs["sport_id"], 1)
        self.assertTrue(
            mock_get_opportunities.call_args.kwargs["one_per_match"])


if __name__ == "__main__":
    unittest.main()
