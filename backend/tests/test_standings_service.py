"""Unit tests for standings service calculation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.repositories.football_point_adjustments_repository import (
    PointAdjustment)
from backend.services.standings_service import get_league_standings
from backend.sports.football.table_zones import TableZone
from backend.sports.football.table_zones import TableZoneSet


_FETCH_ADJUSTMENTS = (
    "backend.services.standings_service.fetch_point_adjustments")
_FETCH_ZONES = "backend.services.standings_service.fetch_table_zones"
_LEAGUE_EXISTS = (
    "backend.services.standings_service.league_repository.league_exists")
_FETCH_RESULTS = (
    "backend.services.standings_service.standings_repository"
    ".fetch_league_results")
_FETCH_TEAMS = (
    "backend.services.standings_service.standings_repository"
    ".fetch_teams_in_season")


class TestStandingsService(unittest.TestCase):
    """Tests for league standings mapping and sorting."""

    def _teams_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team_id": 1, "team_name": "Alpha"},
            {"team_id": 2, "team_name": "Beta"},
        ])

    def _results_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "home_team_id": 1,
                "home_team_name": "Alpha",
                "away_team_id": 2,
                "away_team_name": "Beta",
                "home_team_goals": 2,
                "away_team_goals": 1,
                "result": "1",
            },
            {
                "home_team_id": 2,
                "home_team_name": "Beta",
                "away_team_id": 1,
                "away_team_name": "Alpha",
                "home_team_goals": 1,
                "away_team_goals": 1,
                "result": "X",
            },
        ])

    @patch(_LEAGUE_EXISTS, return_value=False)
    def test_get_league_standings_returns_none_for_missing_league(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_league_standings(999999, 1))

    @patch(_FETCH_ZONES, return_value=None)
    @patch(_FETCH_ADJUSTMENTS, return_value={})
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS, return_value=pd.DataFrame())
    @patch(_FETCH_TEAMS, return_value=pd.DataFrame())
    def test_get_league_standings_returns_empty_table(
        self,
        _mock_teams: unittest.mock.MagicMock,
        _mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        payload = get_league_standings(1, 12)
        assert payload is not None
        self.assertEqual(payload["standings"], [])
        self.assertEqual(payload["zones"], [])
        self.assertEqual(payload["scope"], "overall")
        mock_adjustments.assert_called_once_with(1, 12)
        mock_zones.assert_called_once_with(1, 12, 0)

    @patch(_FETCH_ZONES, return_value=None)
    @patch(_FETCH_ADJUSTMENTS, return_value={})
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_get_league_standings_sorts_by_points(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        _mock_adjustments: unittest.mock.MagicMock,
        _mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="overall")
        assert payload is not None
        standings = payload["standings"]
        self.assertEqual(len(standings), 2)
        self.assertEqual(standings[0]["team_name"], "Alpha")
        self.assertEqual(standings[0]["points"], 4)
        self.assertEqual(standings[0]["position"], 1)
        self.assertEqual(standings[0]["points_adjustment"], 0)
        self.assertIsNone(standings[0]["adjustment_reason"])
        self.assertIsNone(standings[0]["zone_kind"])
        self.assertEqual(payload["zones"], [])

    @patch(_FETCH_ZONES)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_get_league_standings_home_scope_counts_home_matches_only(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="home")
        assert payload is not None
        alpha = next(
            row for row in payload["standings"]
            if row["team_id"] == 1)
        beta = next(
            row for row in payload["standings"]
            if row["team_id"] == 2)
        self.assertEqual(alpha["played"], 1)
        self.assertEqual(beta["played"], 1)
        self.assertEqual(alpha["points"], 3)
        self.assertEqual(beta["points"], 1)
        self.assertEqual(alpha["points_adjustment"], 0)
        self.assertIsNone(alpha["adjustment_reason"])
        self.assertIsNone(alpha["zone_kind"])
        self.assertEqual(payload["zones"], [])
        mock_adjustments.assert_not_called()
        mock_zones.assert_not_called()

    @patch(_FETCH_ZONES)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_get_league_standings_ou_btts_scope(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams_frame()
        mock_results.return_value = self._results_frame()
        payload = get_league_standings(1, 12, scope="ou_btts")
        assert payload is not None
        alpha = payload["standings"][0]
        self.assertEqual(alpha["team_name"], "Alpha")
        self.assertEqual(alpha["played"], 2)
        self.assertEqual(alpha["btts_count"], 2)
        self.assertEqual(alpha["over_2_5_count"], 1)
        self.assertEqual(payload["zones"], [])
        self.assertNotIn("points_adjustment", alpha)
        mock_adjustments.assert_not_called()
        mock_zones.assert_not_called()


class TestOfficialPointsAndZones(unittest.TestCase):
    """Penalties reorder the overall table; zones describe positions."""

    def _teams(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team_id": 73, "team_name": "Southampton"},
            {"team_id": 2, "team_name": "Rival"},
            {"team_id": 3, "team_name": "Filler"},
        ])

    def _results(self) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for _ in range(6):
            rows.append(self._match(73, 3, 2, 0, "1"))
        for _ in range(2):
            rows.append(self._match(73, 3, 1, 1, "X"))
        for _ in range(6):
            rows.append(self._match(2, 3, 3, 0, "1"))
        return pd.DataFrame(rows)

    def _match(
        self,
        home_id: int,
        away_id: int,
        home_goals: int,
        away_goals: int,
        result: str) -> dict[str, object]:
        return {
            "home_team_id": home_id,
            "home_team_name": "home",
            "away_team_id": away_id,
            "away_team_name": "away",
            "home_team_goals": home_goals,
            "away_team_goals": away_goals,
            "result": result,
        }

    def _southampton_adjustment(self) -> dict[int, PointAdjustment]:
        return {
            73: PointAdjustment(
                team_id=73,
                points_delta=-4,
                reason="Decyzja związku"),
        }

    @patch(_FETCH_ZONES, return_value=None)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_overall_ranks_southampton_on_points_after_penalty(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams()
        mock_results.return_value = self._results()
        mock_adjustments.return_value = self._southampton_adjustment()
        payload = get_league_standings(8, 13, scope="overall")
        assert payload is not None
        by_id = {row["team_id"]: row for row in payload["standings"]}
        southampton = by_id[73]
        rival = by_id[2]
        self.assertEqual(southampton["points"], 16)
        self.assertEqual(southampton["points_adjustment"], -4)
        self.assertEqual(southampton["adjustment_reason"], "Decyzja związku")
        self.assertEqual(southampton["wins"], 6)
        self.assertEqual(southampton["draws"], 2)
        self.assertEqual(southampton["losses"], 0)
        self.assertEqual(southampton["goals_for"], 14)
        self.assertEqual(southampton["goals_against"], 2)
        self.assertEqual(rival["points"], 18)
        self.assertEqual(rival["points_adjustment"], 0)
        self.assertIsNone(rival["adjustment_reason"])
        self.assertLess(rival["position"], southampton["position"])
        self.assertEqual(payload["zones"], [])
        mock_adjustments.assert_called_once_with(8, 13)
        mock_zones.assert_called_once_with(8, 13, 3)

    @patch(_FETCH_ZONES)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_home_scope_keeps_match_points(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams()
        mock_results.return_value = self._results()
        payload = get_league_standings(8, 13, scope="home")
        assert payload is not None
        southampton = next(
            row for row in payload["standings"]
            if row["team_id"] == 73)
        self.assertEqual(southampton["points"], 20)
        self.assertEqual(southampton["points_adjustment"], 0)
        self.assertIsNone(southampton["adjustment_reason"])
        self.assertIsNone(southampton["zone_kind"])
        self.assertEqual(southampton["wins"], 6)
        self.assertEqual(southampton["draws"], 2)
        self.assertEqual(payload["zones"], [])
        mock_adjustments.assert_not_called()
        mock_zones.assert_not_called()

    @patch(_FETCH_ZONES)
    @patch(_FETCH_ADJUSTMENTS, return_value={})
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_overall_zone_follows_position(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        _mock_adjustments: unittest.mock.MagicMock,
        mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._five_team_frame()
        mock_results.return_value = self._five_team_results()
        mock_zones.return_value = self._champions_league_set()
        payload = get_league_standings(1, 13, scope="overall")
        assert payload is not None
        standings = payload["standings"]
        self.assertEqual(standings[0]["position"], 1)
        self.assertEqual(standings[0]["team_id"], 1)
        self.assertEqual(standings[0]["zone_kind"], "champions_league")
        fifth = next(row for row in standings if row["position"] == 5)
        self.assertIsNone(fifth["zone_kind"])
        self.assertEqual(payload["zones"], [{
            "position_from": 1,
            "position_to": 1,
            "zone_kind": "champions_league",
            "band": "top",
            "label": "Awans – Liga Mistrzów (Kwalifikacje)",
            "sort_order": 1,
        }])
        mock_zones.assert_called_once_with(1, 13, 5)

    @patch(_FETCH_ZONES, return_value=None)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_invalid_zones_keep_adjusted_points(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        _mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = self._teams()
        mock_results.return_value = self._results()
        mock_adjustments.return_value = self._southampton_adjustment()
        payload = get_league_standings(8, 13, scope="overall")
        assert payload is not None
        southampton = next(
            row for row in payload["standings"]
            if row["team_id"] == 73)
        self.assertEqual(southampton["points"], 16)
        self.assertIsNone(southampton["zone_kind"])
        self.assertEqual(payload["zones"], [])

    @patch(_FETCH_ZONES, return_value=None)
    @patch(_FETCH_ADJUSTMENTS)
    @patch(_LEAGUE_EXISTS, return_value=True)
    @patch(_FETCH_RESULTS)
    @patch(_FETCH_TEAMS)
    def test_tied_official_points_use_goal_difference(
        self,
        mock_teams: unittest.mock.MagicMock,
        mock_results: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        mock_adjustments: unittest.mock.MagicMock,
        _mock_zones: unittest.mock.MagicMock) -> None:
        mock_teams.return_value = pd.DataFrame([
            {"team_id": 1, "team_name": "Alpha"},
            {"team_id": 2, "team_name": "Beta"},
            {"team_id": 3, "team_name": "Filler"},
        ])
        mock_results.return_value = pd.DataFrame([
            self._match(1, 3, 1, 0, "1"),
            self._match(1, 3, 1, 0, "1"),
            self._match(2, 3, 3, 0, "1"),
        ])
        mock_adjustments.return_value = {
            1: PointAdjustment(
                team_id=1,
                points_delta=-3,
                reason="Korekta"),
        }
        payload = get_league_standings(8, 13, scope="overall")
        assert payload is not None
        self.assertEqual(payload["standings"][0]["team_id"], 2)
        self.assertEqual(payload["standings"][0]["points"], 3)
        self.assertEqual(payload["standings"][1]["team_id"], 1)
        self.assertEqual(payload["standings"][1]["points"], 3)

    def _five_team_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team_id": team_id, "team_name": f"Team {team_id}"}
            for team_id in range(1, 6)
        ])

    def _five_team_results(self) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for home_id in range(1, 5):
            for away_id in range(home_id + 1, 6):
                rows.append(self._match(home_id, away_id, 1, 0, "1"))
        return pd.DataFrame(rows)

    def _champions_league_set(self) -> TableZoneSet:
        zone = TableZone(
            position_from=1,
            position_to=1,
            zone_kind="champions_league",
            band="top",
            stage="qualification",
            target_league_id=42,
            target_league_name="Liga Mistrzów",
            sort_order=1,
            label="Awans – Liga Mistrzów (Kwalifikacje)")
        return TableZoneSet(zones=(zone,), top_slots=1, bot_slots=0)


if __name__ == "__main__":
    unittest.main()
