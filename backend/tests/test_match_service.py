"""Unit tests for match service helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import patch

import pandas as pd

from backend.services.match_service import (
    get_league_matches,
    get_match_details)


class TestMatchService(unittest.TestCase):
    """Tests for match service mapping and edge cases."""

    def _sample_match_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "id": 100,
            "league_id": 1,
            "season_id": 12,
            "round": 5,
            "game_date": datetime(2025, 3, 15, 18, 0),
            "result": "1",
            "home_team_goals": 2,
            "away_team_goals": 1,
            "home_id": 10,
            "home_name": "Legia",
            "home_shortcut": "LEG",
            "away_id": 20,
            "away_name": "Lech",
            "away_shortcut": "LPO",
            "home_team_xg": 1.8,
            "away_team_xg": 1.1,
            "home_team_bp": 55,
            "away_team_bp": 45,
            "home_team_sc": 12,
            "away_team_sc": 8,
            "home_team_sog": 5,
            "away_team_sog": 3,
            "home_team_fk": 6,
            "away_team_fk": 8,
            "home_team_ck": 6,
            "away_team_ck": 4,
            "home_team_off": 2,
            "away_team_off": 1,
            "home_team_fouls": 11,
            "away_team_fouls": 14,
            "home_team_yc": 2,
            "away_team_yc": 3,
            "home_team_rc": 0,
            "away_team_rc": 1,
        }])

    @patch(
        "backend.services.match_service.league_repository.league_exists",
        return_value=False)
    def test_get_league_matches_returns_none_for_missing_league(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_league_matches(999999, 1))

    @patch(
        "backend.services.match_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.match_service.match_repository.fetch_league_matches",
        return_value=pd.DataFrame())
    def test_get_league_matches_returns_empty_list(
        self,
        _mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        matches = get_league_matches(1, 12)
        self.assertEqual(matches, [])

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.match_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.match_service.match_repository.fetch_league_matches")
    def test_get_league_matches_maps_summary_fields(
        self,
        mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = self._sample_match_frame()
        matches = get_league_matches(
            1,
            12,
            round_num=5,
            date_from=date(2025, 3, 1),
            date_to=date(2025, 3, 31))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], 100)
        self.assertTrue(matches[0]["is_played"])
        self.assertEqual(matches[0]["home_team"]["name"], "Legia")
        self.assertEqual(matches[0]["round_label"], "5")

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={973: "Quarter-final"})
    @patch(
        "backend.services.match_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.match_service.match_repository.fetch_league_matches")
    def test_get_league_matches_resolves_special_round_label(
        self,
        mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        frame = self._sample_match_frame()
        frame.loc[0, "round"] = 973
        mock_fetch.return_value = frame
        matches = get_league_matches(1, 12)
        self.assertEqual(matches[0]["round"], 973)
        self.assertEqual(matches[0]["round_label"], "Quarter-final")

    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id",
        return_value=pd.DataFrame())
    def test_get_match_details_returns_none_for_missing_match(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_match_details(999999))

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.match_service.match_repository"
        ".fetch_team_matches_before_date",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service.match_repository"
        ".fetch_head_to_head_for_match",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service._league_has_player_stats",
        return_value=False)
    @patch("backend.services.match_service.odds_service.get_match_odds_items")
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions")
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_includes_predictions_odds_and_stats(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        mock_fetch_predictions: unittest.mock.MagicMock,
        mock_fetch_odds: unittest.mock.MagicMock,
        _mock_has_player_stats: unittest.mock.MagicMock,
        _mock_fetch_h2h: unittest.mock.MagicMock,
        _mock_fetch_history: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_match.return_value = self._sample_match_frame()
        mock_fetch_predictions.return_value = [{
            "prediction_id": 10,
            "event_id": 1,
            "event_name": "1",
            "event_family": {"id": 2, "name": "REZULTAT"},
            "model_id": 3,
            "model_name": "Model A",
            "value": 0.55,
            "outcome": 1,
        }]
        mock_fetch_odds.return_value = [{
            "id": 1,
            "match_id": 100,
            "bookmaker_id": 4,
            "bookmaker_name": "STS",
            "event_id": 1,
            "event_name": "1",
            "event_family": {"id": 2, "name": "REZULTAT"},
            "odds": 1.95,
        }]
        details = get_match_details(100)
        assert details is not None
        self.assertEqual(details["id"], 100)
        self.assertEqual(len(details["final_predictions"]), 1)
        self.assertEqual(len(details["odds"]), 1)
        self.assertIsNotNone(details["stats"])
        self.assertEqual(details["stats"]["home_xg"], 1.8)
        self.assertEqual(details["head_to_head"]["played"], 0)

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.match_service.match_repository"
        ".fetch_team_matches_before_date",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service.match_repository"
        ".fetch_head_to_head_for_match",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service._league_has_player_stats",
        return_value=False)
    @patch(
        "backend.services.match_service.odds_service.get_match_odds_items",
        return_value=[])
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions")
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_marks_unplayed_match(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        mock_fetch_predictions: unittest.mock.MagicMock,
        _mock_fetch_odds: unittest.mock.MagicMock,
        _mock_has_player_stats: unittest.mock.MagicMock,
        _mock_fetch_h2h: unittest.mock.MagicMock,
        _mock_fetch_history: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        frame = self._sample_match_frame()
        frame.loc[0, "result"] = "0"
        frame.loc[0, "home_team_goals"] = None
        frame.loc[0, "away_team_goals"] = None
        mock_fetch_match.return_value = frame
        mock_fetch_predictions.return_value = []
        details = get_match_details(100)
        assert details is not None
        self.assertFalse(details["is_played"])


if __name__ == "__main__":
    unittest.main()
