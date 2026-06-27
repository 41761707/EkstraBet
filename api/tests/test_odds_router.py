"""API tests for odds endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestOddsRouter(unittest.TestCase):
    """HTTP contract tests for odds endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch(
        "api.routers.odds.odds_service.get_match_odds",
        return_value=None)
    def test_get_match_odds_returns_404_for_missing_match(
        self,
        _mock_get_odds: unittest.mock.MagicMock) -> None:
        response = self.client.get("/odds/match/999999")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.odds.odds_service.get_match_odds")
    def test_get_match_odds_returns_unified_payload(
        self,
        mock_get_odds: unittest.mock.MagicMock) -> None:
        mock_get_odds.return_value = {
            "odds": [{
                "id": 1,
                "match_id": 100,
                "bookmaker_id": 4,
                "bookmaker_name": "STS",
                "event_id": 5,
                "event_name": "1",
                "event_family": {"id": 2, "name": "REZULTAT"},
                "odds": 1.95,
            }],
            "total_count": 1,
            "match_id": 100,
        }
        response = self.client.get("/odds/match/100")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["odds"][0]["bookmaker_id"], 4)
        self.assertEqual(payload["odds"][0]["event_id"], 5)


if __name__ == "__main__":
    unittest.main()
