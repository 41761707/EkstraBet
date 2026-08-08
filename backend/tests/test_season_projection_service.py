"""Unit tests for season projection read service."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories.season_projection_repository import (
    SeasonProjectionRunRecord)
from backend.repositories.season_projection_repository import (
    SeasonProjectionTeamRowRecord)
from backend.services import season_projection_service as service
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.config import SeasonSimulationInput


def _run(
        *,
        fingerprint: str = "fp-fresh",
        mode: str = "from_now") -> SeasonProjectionRunRecord:
    return SeasonProjectionRunRecord(
        id=7,
        league_id=1,
        season_id=13,
        mode=mode,
        status="SUCCEEDED",
        model_name="FOOTBALL_GOALS_POISSON_V1",
        model_version="1.0.0",
        artifact_hash="abc",
        n_trials=2000,
        seed=42,
        fixed_matches=10,
        simulated_matches=290,
        input_fingerprint=fingerprint,
        started_at=datetime(2026, 8, 1, 10, 0, 0),
        completed_at=datetime(2026, 8, 1, 10, 5, 0))


def _team_row(team_id: int = 10) -> SeasonProjectionTeamRowRecord:
    return SeasonProjectionTeamRowRecord(
        team_id=team_id,
        team_name=f"Team {team_id}",
        current_position=1,
        current_points=12,
        expected_position=1.5,
        most_likely_position=1,
        position_min=1,
        position_max=3,
        expected_points=45.0,
        points_variance=4.0,
        points_stddev=2.0,
        points_p05=40.0,
        points_p50=45.0,
        points_p95=50.0,
        points_min=38.0,
        points_max=52.0,
        expected_goal_difference=8.0,
        position_probabilities=[0.6, 0.3, 0.1])


def _input(fingerprint: str) -> SeasonSimulationInput:
    return SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_NOW,
        team_ids=[10, 20],
        fixtures=[],
        input_fingerprint=fingerprint)


class TestSeasonProjectionService(unittest.TestCase):
    """Service contract for cached season projections."""

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        return_value=_input("fp-fresh"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_team_row()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run(fingerprint="fp-fresh"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_returns_fresh_latest_succeeded_run(
            self,
            mock_league: MagicMock,
            mock_run: MagicMock,
            mock_rows: MagicMock,
            mock_fingerprint: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        payload = service.get_season_projection(1, 13, "from_now")
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.league_id, 1)
        self.assertEqual(payload.season_id, 13)
        self.assertEqual(payload.mode, SimulationMode.FROM_NOW)
        self.assertFalse(payload.is_stale)
        self.assertEqual(payload.n_trials, 2000)
        self.assertEqual(payload.standings[0].team_name, "Team 10")
        mock_run.assert_called_once_with(1, 13, "from_now")
        mock_rows.assert_called_once_with(7)
        mock_fingerprint.assert_called_once_with(
            1, 13, SimulationMode.FROM_NOW)

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        return_value=_input("fp-new"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_team_row()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run(fingerprint="fp-old"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_marks_stale_when_fingerprint_differs(
            self,
            mock_league: MagicMock,
            _mock_run: MagicMock,
            _mock_rows: MagicMock,
            _mock_fingerprint: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        payload = service.get_season_projection(
            1, 13, SimulationMode.FROM_NOW)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload.is_stale)

    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=None)
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_returns_none_when_no_succeeded_run(
            self,
            mock_league: MagicMock,
            mock_run: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        payload = service.get_season_projection(1, 13, "from_now")
        self.assertIsNone(payload)
        mock_run.assert_called_once()

    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_rejects_non_football_league(
            self,
            mock_league: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 5,
            "name": "NHL",
            "sport_id": 2,
            "country_id": 1,
            "country_name": "USA",
            "country_emoji": None,
            "sport_name": "Hockey",
            "active": 1,
            "last_update": None}])
        with self.assertRaises(service.NonFootballLeagueError):
            service.get_season_projection(5, 1, "from_now")

    def test_rejects_unsupported_mode(self) -> None:
        with self.assertRaises(service.UnsupportedSeasonProjectionModeError):
            service.get_season_projection(1, 13, "from_mid_season")

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        side_effect=ValueError("league_id=1 was not found"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_team_row()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run(fingerprint="fp-cached"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_fingerprint_failure_returns_cache_as_stale(
            self,
            mock_league: MagicMock,
            _mock_run: MagicMock,
            _mock_rows: MagicMock,
            _mock_fingerprint: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        payload = service.get_season_projection(1, 13, "from_now")
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload.is_stale)
        self.assertEqual(payload.standings[0].team_id, 10)

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input",
        return_value=_input("fp-fresh"))
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_team_row()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run(fingerprint="fp-fresh"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_read_path_does_not_load_simulator_or_tensorflow(
            self,
            mock_league: MagicMock,
            _mock_run: MagicMock,
            _mock_rows: MagicMock,
            _mock_fingerprint: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        import sys
        # usuwamy ewentualne wczesniejsze importy z innych testow
        for module_name in list(sys.modules):
            if (
                module_name == "tensorflow"
                or module_name.startswith("tensorflow.")
                or module_name == "keras"
                or module_name.startswith("keras.")
                or module_name.endswith("season_simulator")
            ):
                del sys.modules[module_name]
        payload = service.get_season_projection(1, 13, "from_now")
        self.assertIsNotNone(payload)
        loaded = set(sys.modules)
        self.assertNotIn(
            "models.pipeline.simulation.season_simulator", loaded)
        self.assertFalse(any(
            name == "tensorflow" or name.startswith("tensorflow.")
            for name in loaded))
        self.assertFalse(any(
            name == "keras" or name.startswith("keras.")
            for name in loaded))

    @patch(
        "backend.services.season_projection_service"
        ".fetch_season_simulation_input")
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_team_rows_for_run",
        return_value=[_team_row()])
    @patch(
        "backend.services.season_projection_service.repository"
        ".fetch_latest_succeeded_run",
        return_value=_run(
            fingerprint="fp-a",
            mode="from_season_start"))
    @patch(
        "backend.services.season_projection_service.league_repository"
        ".fetch_league_by_id")
    def test_uses_mode_for_run_lookup_and_fingerprint(
            self,
            mock_league: MagicMock,
            mock_run: MagicMock,
            _mock_rows: MagicMock,
            mock_fingerprint: MagicMock) -> None:
        mock_league.return_value = pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "sport_id": 1,
            "country_id": 1,
            "country_name": "Poland",
            "country_emoji": None,
            "sport_name": "Football",
            "active": 1,
            "last_update": None}])
        mock_fingerprint.return_value = SeasonSimulationInput(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_SEASON_START,
            team_ids=[10],
            fixtures=[],
            input_fingerprint="fp-a")
        payload = service.get_season_projection(
            1, 13, SimulationMode.FROM_SEASON_START)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(
            payload.mode, SimulationMode.FROM_SEASON_START)
        mock_run.assert_called_once_with(1, 13, "from_season_start")
        mock_fingerprint.assert_called_once_with(
            1, 13, SimulationMode.FROM_SEASON_START)


if __name__ == "__main__":
    unittest.main()
