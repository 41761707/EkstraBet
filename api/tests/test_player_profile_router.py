"""API tests for the player profile endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app
from backend.services.player_profile_service import (
    PlayerProfileNotFoundError)
from backend.services.player_profile_service import (
    PlayerProfileUnavailableError)
from backend.services.player_profile_service import (
    PlayerProfileValidationError)


_UNAVAILABLE = "Player profile is not available for this sport"
_PROFILE = "api.routers.players.player_profile_service.get_player_profile"
_SEARCH = "api.routers.players.player_profile_service.search_players"


def _empty_profile() -> dict[str, object]:
    """Return a valid empty hockey envelope for the router contract."""
    return {
        "player_id": 15,
        "player_name": "Connor McDavid",
        "sport_id": 2,
        "filters": {
            "player_id": 15,
            "season_id": 7,
            "opponent_team_id": 3,
            "own_team_id": 4,
            "teammate_id": 8},
        "match_count": 0,
        "truncated": False,
        "body": {
            "sport_id": 2,
            "player_role": "skater",
            "summary": {
                "is_goalie": False,
                "points": 0,
                "goals": 0,
                "assists": 0,
                "plus_minus": 0,
                "penalty_minutes": 0,
                "average_penalty_minutes": 0.0,
                "average_toi": "0:00",
                "average_sog": 0.0},
            "event_split": {
                "goals": 0,
                "power_play_goals": 0,
                "empty_net_goals": 0,
                "goals_period_1": 0,
                "goals_period_2": 0,
                "goals_period_3": 0,
                "goals_overtime": 0,
                "shootout_goals": 0,
                "minor_penalties": 0,
                "major_penalties": 0,
                "misconduct_penalties": 0,
                "unsportsmanlike_penalties": 0,
                "disallowed_goals": 0},
            "matches": []}}


class TestPlayerProfileRouter(unittest.TestCase):
    """HTTP contract for profile read and teammate search."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch(_PROFILE, return_value=_empty_profile())
    def test_empty_hockey_slice_returns_filters(
            self,
            mock_profile: unittest.mock.MagicMock) -> None:
        response = self.client.get(
            "/players/15/profile"
            "?season_id=7&opponent_team_id=3"
            "&own_team_id=4&teammate_id=8")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["sport_id"], 2)
        self.assertEqual(payload["match_count"], 0)
        self.assertEqual(payload["filters"], _empty_profile()["filters"])
        mock_profile.assert_called_once_with(15, 7, 3, 4, 8)

    @patch(_PROFILE, side_effect=PlayerProfileNotFoundError())
    def test_missing_player_returns_404(
            self,
            _mock_profile: unittest.mock.MagicMock) -> None:
        response = self.client.get("/players/15/profile")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Player not found")

    @patch(_PROFILE, side_effect=PlayerProfileUnavailableError())
    def test_sport_without_source_returns_404(
            self,
            _mock_profile: unittest.mock.MagicMock) -> None:
        response = self.client.get("/players/15/profile")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], _UNAVAILABLE)

    @patch(
        _PROFILE,
        side_effect=PlayerProfileValidationError(
            "teammate_id must differ from player_id"))
    def test_validation_error_returns_422(
            self,
            _mock_profile: unittest.mock.MagicMock) -> None:
        response = self.client.get("/players/15/profile?teammate_id=15")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "teammate_id must differ from player_id")

    @patch(_SEARCH)
    def test_search_registered_sport_returns_hits(
            self,
            mock_search: unittest.mock.MagicMock) -> None:
        mock_search.return_value = {
            "players": [{
                "player_id": 8,
                "player_name": "Leon Draisaitl",
                "position": "C",
                "current_team_name": "Edmonton"}],
            "total_count": 1}
        response = self.client.get("/players/2/search?search=dra")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["players"][0]["player_id"], 8)
        mock_search.assert_called_once_with(2, "dra")

    @patch(_SEARCH, side_effect=PlayerProfileUnavailableError())
    def test_search_unregistered_sport_returns_404(
            self,
            _mock_search: unittest.mock.MagicMock) -> None:
        response = self.client.get("/players/1/search?search=me")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], _UNAVAILABLE)

    @patch(
        _SEARCH,
        side_effect=PlayerProfileValidationError(
            "Search must contain at least 2 characters"))
    def test_short_search_returns_422(
            self,
            _mock_search: unittest.mock.MagicMock) -> None:
        response = self.client.get("/players/2/search?search=a")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Search must contain at least 2 characters")
