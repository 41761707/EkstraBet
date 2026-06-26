"""API tests for the leagues router."""

from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestLeaguesRouter(unittest.TestCase):
    """HTTP contract tests for league navigation endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch("api.routers.leagues.league_service.get_leagues", return_value=[])
    def test_get_leagues_returns_empty_list(
        self,
        _mock_get_leagues: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 0)
        self.assertEqual(payload["leagues"], [])

    @patch("api.routers.leagues.league_service.get_leagues")
    def test_get_leagues_returns_summaries(
        self,
        mock_get_leagues: unittest.mock.MagicMock) -> None:
        mock_get_leagues.return_value = [{
            "id": 1,
            "name": "Ekstraklasa",
            "country_id": 10,
            "country_name": "Polska",
            "country_emoji": "🇵🇱",
            "sport_id": 1,
            "sport_name": "Football",
            "active": True,
            "last_update": date(2025, 6, 1),
            "slug": "ekstraklasa",
        }]
        response = self.client.get("/leagues?active=true&sport_id=1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["leagues"][0]["slug"], "ekstraklasa")

    @patch(
        "api.routers.leagues.league_service.get_league_details",
        return_value=None)
    def test_get_league_details_returns_404_for_missing_league(
        self,
        _mock_get_details: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999")
        self.assertEqual(response.status_code, 404)

    @patch(
        "api.routers.leagues.league_service.get_league_seasons",
        return_value=None)
    def test_get_league_seasons_returns_404_for_missing_league(
        self,
        _mock_get_seasons: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999/seasons")
        self.assertEqual(response.status_code, 404)

    @patch(
        "api.routers.leagues.league_service.get_league_seasons",
        return_value=[])
    def test_get_league_seasons_returns_empty_list(
        self,
        _mock_get_seasons: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/1/seasons")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 0)
        self.assertEqual(payload["seasons"], [])

    @patch(
        "api.routers.leagues.league_service.get_league_rounds",
        return_value=None)
    def test_get_league_rounds_returns_404_for_missing_league(
        self,
        _mock_get_rounds: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999/rounds/1")
        self.assertEqual(response.status_code, 404)

    def test_invalid_league_id_is_rejected(self) -> None:
        response = self.client.get("/leagues/0")
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
