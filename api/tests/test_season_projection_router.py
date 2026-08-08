"""API tests for league season-projection endpoint."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app
from backend.repositories.season_projection_repository import (
    SeasonProjectionRunRecord)
from backend.repositories.season_projection_repository import (
    SeasonProjectionTeamRowRecord)
from backend.services.season_projection_service import NonFootballLeagueError
from backend.services.season_projection_service import SeasonProjectionPayload
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode


def _standing() -> SeasonProjectionTeamRowRecord:
    return SeasonProjectionTeamRowRecord(
        team_id=10,
        team_name="Legia",
        current_position=1,
        current_points=15,
        expected_position=1.2,
        most_likely_position=1,
        position_min=1,
        position_max=2,
        expected_points=48.5,
        points_variance=3.0,
        points_stddev=1.73,
        points_p05=45.0,
        points_p50=48.0,
        points_p95=52.0,
        points_min=44.0,
        points_max=54.0,
        expected_goal_difference=12.0,
        position_probabilities=[0.8, 0.2])


def _payload(
        *,
        is_stale: bool = False,
        mode: SimulationMode = SimulationMode.FROM_NOW
) -> SeasonProjectionPayload:
    return SeasonProjectionPayload(
        league_id=1,
        season_id=13,
        mode=mode,
        generated_at=datetime(2026, 8, 1, 12, 0, 0),
        model_name="FOOTBALL_GOALS_POISSON_V1",
        model_version="1.0.0",
        n_trials=2000,
        fixed_matches=12,
        simulated_matches=294,
        is_stale=is_stale,
        standings=[_standing()])


def _football_league_frame() -> pd.DataFrame:
    return pd.DataFrame([{
        "id": 1,
        "name": "Ekstraklasa",
        "sport_id": 1,
        "country_id": 1,
        "country_name": "Poland",
        "country_emoji": None,
        "sport_name": "Football",
        "active": 1,
        "last_update": None}])


def _run_record(
        *,
        fingerprint: str = "fp-fresh") -> SeasonProjectionRunRecord:
    return SeasonProjectionRunRecord(
        id=7,
        league_id=1,
        season_id=13,
        mode="from_now",
        status="SUCCEEDED",
        model_name="FOOTBALL_GOALS_POISSON_V1",
        model_version="1.0.0",
        artifact_hash="abc",
        n_trials=2000,
        seed=42,
        fixed_matches=12,
        simulated_matches=294,
        input_fingerprint=fingerprint,
        started_at=datetime(2026, 8, 1, 10, 0, 0),
        completed_at=datetime(2026, 8, 1, 12, 0, 0))


class TestSeasonProjectionRouter(unittest.TestCase):
    """HTTP contract tests for season-projection endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_requires_season_id(self) -> None:
        response = self.client.get("/leagues/1/season-projection")
        self.assertEqual(response.status_code, 422)

    def test_rejects_invalid_mode(self) -> None:
        response = self.client.get(
            "/leagues/1/season-projection"
            "?season_id=13&mode=from_mid_season")
        self.assertEqual(response.status_code, 422)

    @patch(
        "api.routers.leagues.get_season_projection",
        return_value=_payload())
    def test_returns_200_with_mapped_payload(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/season-projection?season_id=13")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["league_id"], 1)
        self.assertEqual(body["season_id"], 13)
        self.assertEqual(body["mode"], "from_now")
        self.assertEqual(body["model_name"], "FOOTBALL_GOALS_POISSON_V1")
        self.assertEqual(body["n_trials"], 2000)
        self.assertEqual(body["fixed_matches"], 12)
        self.assertEqual(body["simulated_matches"], 294)
        self.assertFalse(body["is_stale"])
        self.assertEqual(body["standings"][0]["team_name"], "Legia")
        self.assertEqual(
            body["standings"][0]["position_probabilities"], [0.8, 0.2])
        mock_get.assert_called_once_with(
            league_id=1,
            season_id=13,
            mode="from_now")

    @patch(
        "api.routers.leagues.get_season_projection",
        return_value=_payload(is_stale=True))
    def test_returns_stale_flag(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/season-projection?season_id=13&mode=from_now")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_stale"])
        mock_get.assert_called_once()

    @patch(
        "api.routers.leagues.get_season_projection",
        return_value=_payload(mode=SimulationMode.FROM_SEASON_START))
    def test_accepts_from_season_start_mode(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/season-projection"
            "?season_id=13&mode=from_season_start")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "from_season_start")
        mock_get.assert_called_once_with(
            league_id=1,
            season_id=13,
            mode="from_season_start")

    @patch(
        "api.routers.leagues.get_season_projection",
        return_value=None)
    def test_returns_404_when_no_run(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/season-projection?season_id=13")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No season projection", response.json()["detail"])
        mock_get.assert_called_once()

    @patch(
        "api.routers.leagues.get_season_projection",
        side_effect=NonFootballLeagueError(
            "League 5 is not a football league"))
    def test_returns_400_for_non_football_league(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/5/season-projection?season_id=1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not a football league", response.json()["detail"])
        mock_get.assert_called_once()

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        side_effect=ValueError("league_id=1 was not found"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_standing()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run_record(fingerprint="fp-cached"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id",
        return_value=_football_league_frame())
    def test_fingerprint_failure_returns_200_stale_not_422(
            self,
            _mock_league: MagicMock,
            _mock_run: MagicMock,
            _mock_rows: MagicMock,
            _mock_fingerprint: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/season-projection?season_id=13")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_stale"])

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        return_value=SeasonSimulationInput(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_NOW,
            team_ids=[10],
            fixtures=[],
            input_fingerprint="fp-fresh"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_standing()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run_record(fingerprint="fp-fresh"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id",
        return_value=_football_league_frame())
    def test_read_path_does_not_invoke_simulator(
            self,
            _mock_league: MagicMock,
            _mock_run: MagicMock,
            _mock_rows: MagicMock,
            _mock_fingerprint: MagicMock) -> None:
        for module_name in list(sys.modules):
            if (
                module_name == "tensorflow"
                or module_name.startswith("tensorflow.")
                or module_name == "keras"
                or module_name.startswith("keras.")
                or module_name.endswith("season_simulator")
            ):
                del sys.modules[module_name]
        response = self.client.get(
            "/leagues/1/season-projection?season_id=13")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_stale"])
        loaded = set(sys.modules)
        self.assertNotIn(
            "models.pipeline.simulation.season_simulator", loaded)
        self.assertFalse(any(
            name == "tensorflow" or name.startswith("tensorflow.")
            for name in loaded))


if __name__ == "__main__":
    unittest.main()
