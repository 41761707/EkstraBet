"""Unit tests for team profile service."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from backend.services.team_service import get_team_profile


class TestTeamService(unittest.TestCase):
    """Tests for team profile aggregation."""

    def _team_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "id": 10,
            "name": "Legia",
            "shortcut": "LEG",
            "country_id": 1,
            "country_name": "Polska",
            "country_emoji": "🇵🇱",
            "sport_id": 1,
            "sport_name": "Football",
        }])

    def _matches_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "id": 101,
                "league_id": 1,
                "season_id": 12,
                "round": 10,
                "game_date": datetime(2025, 4, 1, 18, 0),
                "result": "1",
                "home_team_goals": 2,
                "away_team_goals": 1,
                "home_id": 10,
                "home_name": "Legia",
                "home_shortcut": "LEG",
                "away_id": 20,
                "away_name": "Lech",
                "away_shortcut": "LPO",
                "home_team_sc": 14,
                "away_team_sc": 9,
                "home_team_sog": 6,
                "away_team_sog": 3,
                "home_team_ck": 7,
                "away_team_ck": 4,
                "home_team_off": 2,
                "away_team_off": 1,
                "home_team_yc": 2,
                "away_team_yc": 1,
                "home_team_rc": 0,
                "away_team_rc": 1,
                "home_team_fouls": 11,
                "away_team_fouls": 14,
            },
            {
                "id": 95,
                "league_id": 1,
                "season_id": 12,
                "round": 9,
                "game_date": datetime(2025, 3, 20, 20, 0),
                "result": "1",
                "home_team_goals": 3,
                "away_team_goals": 0,
                "home_id": 30,
                "home_name": "Cracovia",
                "home_shortcut": "CRA",
                "away_id": 10,
                "away_name": "Legia",
                "away_shortcut": "LEG",
                "home_team_sc": 10,
                "away_team_sc": 16,
                "home_team_sog": 4,
                "away_team_sog": 7,
                "home_team_ck": 3,
                "away_team_ck": 8,
                "home_team_off": 1,
                "away_team_off": 3,
                "home_team_yc": 1,
                "away_team_yc": 2,
                "home_team_rc": 0,
                "away_team_rc": 0,
                "home_team_fouls": 8,
                "away_team_fouls": 12,
            },
        ])

    @patch(
        "backend.services.team_service.team_repository.fetch_team_by_id",
        return_value=pd.DataFrame())
    def test_get_team_profile_returns_none_for_missing_team(
        self,
        _mock_fetch_team: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_team_profile(999999, 12))

    @patch(
        "backend.services.team_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.team_service.team_repository.fetch_team_played_matches",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.team_service.team_repository.fetch_team_by_id")
    def test_get_team_profile_returns_empty_stats(
        self,
        mock_fetch_team: unittest.mock.MagicMock,
        _mock_fetch_matches: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_team.return_value = self._team_frame()
        profile = get_team_profile(10, 12)
        assert profile is not None
        self.assertEqual(profile["team"]["name"], "Legia")
        self.assertEqual(profile["recent_matches"], [])
        self.assertEqual(profile["overall_stats"]["played"], 0)
        self.assertEqual(profile["season_matches"], [])

    @patch(
        "backend.services.team_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.team_service.team_repository.fetch_team_played_matches")
    @patch(
        "backend.services.team_service.team_repository.fetch_team_by_id")
    def test_get_team_profile_builds_form_and_split_stats(
        self,
        mock_fetch_team: unittest.mock.MagicMock,
        mock_fetch_matches: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_team.return_value = self._team_frame()
        mock_fetch_matches.return_value = self._matches_frame()
        profile = get_team_profile(10, 12, limit=2)
        assert profile is not None
        self.assertEqual(profile["form"], ["L", "W"])
        self.assertEqual(len(profile["recent_matches"]), 2)
        self.assertEqual(len(profile["season_matches"]), 2)
        self.assertEqual(profile["overall_stats"]["played"], 2)
        self.assertEqual(profile["home_stats"]["wins"], 1)
        self.assertEqual(profile["away_stats"]["losses"], 1)
        self.assertEqual(len(profile["season_matches"]), 2)
        self.assertEqual(profile["season_matches"][0]["total_goals"], 3)
        self.assertEqual(profile["season_matches"][0]["result"], "W")
        self.assertTrue(profile["season_matches"][0]["btts"])
        self.assertEqual(profile["season_matches"][1]["total_goals"], 3)
        self.assertEqual(profile["season_matches"][1]["result"], "L")
        self.assertFalse(profile["season_matches"][1]["btts"])
        latest_match = profile["season_matches"][0]
        self.assertEqual(latest_match["team_cards"], 2)
        self.assertEqual(latest_match["opponent_cards"], 2)
        self.assertEqual(latest_match["total_cards"], 4)
        self.assertEqual(latest_match["team_shots"], 14)
        self.assertEqual(latest_match["opponent_shots"], 9)
        self.assertEqual(latest_match["total_shots"], 23)
        self.assertEqual(latest_match["team_fouls"], 11)
        self.assertEqual(latest_match["opponent_fouls"], 14)
        self.assertEqual(latest_match["total_fouls"], 25)
        away_match = profile["season_matches"][1]
        self.assertEqual(away_match["team_fouls"], 12)
        self.assertEqual(away_match["opponent_fouls"], 8)
        self.assertEqual(away_match["total_fouls"], 20)

    @patch(
        "backend.services.team_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.team_service.team_repository.fetch_team_played_matches")
    @patch(
        "backend.services.team_service.team_repository.fetch_team_by_id")
    def test_map_season_match_point_null_fouls_default_to_zero(
        self,
        mock_fetch_team: unittest.mock.MagicMock,
        mock_fetch_matches: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_team.return_value = self._team_frame()
        matches = self._matches_frame().head(1).copy()
        matches["home_team_fouls"] = None
        matches["away_team_fouls"] = None
        mock_fetch_matches.return_value = matches
        profile = get_team_profile(10, 12, limit=1)
        assert profile is not None
        match_point = profile["season_matches"][0]
        self.assertEqual(match_point["team_fouls"], 0)
        self.assertEqual(match_point["opponent_fouls"], 0)
        self.assertEqual(match_point["total_fouls"], 0)

    @patch(
        "backend.services.team_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.team_service.team_repository.fetch_head_to_head_matches")
    @patch(
        "backend.services.team_service.team_repository.team_exists",
        return_value=True)
    @patch(
        "backend.services.team_service.team_repository.fetch_team_played_matches",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.team_service.team_repository.fetch_team_by_id")
    def test_get_team_profile_includes_head_to_head(
        self,
        mock_fetch_team: unittest.mock.MagicMock,
        _mock_fetch_matches: unittest.mock.MagicMock,
        _mock_team_exists: unittest.mock.MagicMock,
        mock_fetch_h2h: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_team.return_value = self._team_frame()
        mock_fetch_h2h.return_value = self._matches_frame().head(1)
        profile = get_team_profile(10, 12, opponent_id=20)
        assert profile is not None
        assert profile["head_to_head"] is not None
        self.assertEqual(profile["head_to_head"]["opponent_id"], 20)
        self.assertEqual(profile["head_to_head"]["wins"], 1)


if __name__ == "__main__":
    unittest.main()
