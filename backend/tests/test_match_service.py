"""Unit tests for match service helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import patch

import pandas as pd

from backend.services.match_service import (
    get_league_matches,
    get_match_details,
    search_matches)


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
        ".get_match_prediction_analysis",
        return_value=None)
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions")
    @patch(
        "backend.services.match_service.match_assessment_repository"
        ".fetch_match_assessments",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_includes_predictions_odds_and_stats(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        _mock_fetch_assessments: unittest.mock.MagicMock,
        mock_fetch_predictions: unittest.mock.MagicMock,
        _mock_fetch_analysis: unittest.mock.MagicMock,
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
        self.assertIsNone(details["prediction_analysis"])
        self.assertEqual(len(details["odds"]), 1)
        self.assertIsNotNone(details["stats"])
        self.assertEqual(details["stats"]["home_xg"], 1.8)
        self.assertEqual(details["head_to_head"]["played"], 0)
        self.assertEqual(details["model_assessments"], [])

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
        ".get_match_prediction_analysis",
        return_value=None)
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions")
    @patch(
        "backend.services.match_service.match_assessment_repository"
        ".fetch_match_assessments",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_marks_unplayed_match(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        _mock_fetch_assessments: unittest.mock.MagicMock,
        mock_fetch_predictions: unittest.mock.MagicMock,
        _mock_fetch_analysis: unittest.mock.MagicMock,
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
        self.assertEqual(details["model_assessments"], [])

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
        ".get_match_prediction_analysis",
        return_value=None)
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions",
        return_value=[])
    @patch(
        "backend.services.match_service.match_assessment_repository"
        ".fetch_match_assessments")
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_maps_model_assessments(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        mock_fetch_assessments: unittest.mock.MagicMock,
        _mock_fetch_predictions: unittest.mock.MagicMock,
        _mock_fetch_analysis: unittest.mock.MagicMock,
        _mock_fetch_odds: unittest.mock.MagicMock,
        _mock_has_player_stats: unittest.mock.MagicMock,
        _mock_fetch_h2h: unittest.mock.MagicMock,
        _mock_fetch_history: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_match.return_value = self._sample_match_frame()
        mock_fetch_assessments.return_value = pd.DataFrame([{
            "model_id": 6,
            "model_name": "FOOTBALL_PLAYED_BETTER_V1",
            "model_version": "1.0.0",
            "assessment_type": "PLAYED_BETTER",
            "home_played_better_probability": 0.55,
            "draw_probability": 0.25,
            "away_played_better_probability": 0.20,
            "final_assessment": "HOME_PLAYED_BETTER",
            "confidence": 0.30,
            "dominance_score": 0.8,
            "feature_snapshot": '{"xg_diff": 1.2, "possession_diff": 10}',
            "updated_at": datetime(2025, 3, 16, 12, 0),
        }])
        details = get_match_details(100)
        assert details is not None
        self.assertEqual(len(details["model_assessments"]), 1)
        assessment = details["model_assessments"][0]
        self.assertEqual(assessment["model_id"], 6)
        self.assertEqual(assessment["assessment_type"], "PLAYED_BETTER")
        self.assertEqual(assessment["final_assessment"], "HOME_PLAYED_BETTER")
        self.assertEqual(assessment["feature_snapshot"]["xg_diff"], 1.2)

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
        ".get_match_prediction_analysis",
        return_value=None)
    @patch(
        "backend.services.match_service.prediction_service"
        ".get_match_final_predictions",
        return_value=[])
    @patch(
        "backend.services.match_service.match_assessment_repository"
        ".fetch_match_assessments",
        side_effect=RuntimeError("db down"))
    @patch(
        "backend.services.match_service.match_repository.fetch_match_by_id")
    def test_get_match_details_returns_empty_assessments_on_error(
        self,
        mock_fetch_match: unittest.mock.MagicMock,
        _mock_fetch_assessments: unittest.mock.MagicMock,
        _mock_fetch_predictions: unittest.mock.MagicMock,
        _mock_fetch_analysis: unittest.mock.MagicMock,
        _mock_fetch_odds: unittest.mock.MagicMock,
        _mock_has_player_stats: unittest.mock.MagicMock,
        _mock_fetch_h2h: unittest.mock.MagicMock,
        _mock_fetch_history: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_fetch_match.return_value = self._sample_match_frame()
        details = get_match_details(100)
        assert details is not None
        self.assertEqual(details["model_assessments"], [])
        self.assertIsNotNone(details["stats"])


class TestMatchSearchService(unittest.TestCase):
    """Tests for match search by team name queries."""

    def _upcoming_match_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "id": 119435,
            "league_id": 1,
            "season_id": 12,
            "sport_id": 1,
            "round": 8,
            "game_date": datetime(2026, 7, 28, 18, 0),
            "result": "0",
            "home_team_goals": None,
            "away_team_goals": None,
            "home_id": 10,
            "home_name": "Górnik Zabrze",
            "home_shortcut": "GOR",
            "away_id": 20,
            "away_name": "Śląsk Wrocław",
            "away_shortcut": "SLA"
        }])

    def test_search_matches_requires_at_least_one_query(self) -> None:
        with self.assertRaises(ValueError):
            search_matches(team_a_query="  ", team_b_query=None)

    @patch(
        "backend.services.match_service.team_repository.search_teams_by_name",
        return_value=pd.DataFrame())
    def test_search_matches_returns_empty_when_team_missing(
        self,
        mock_search_teams: unittest.mock.MagicMock) -> None:
        payload = search_matches(
            team_a_query="Nieistniejaca",
            from_now=True)
        self.assertEqual(payload["matches"], [])
        self.assertEqual(payload["total_count"], 0)
        self.assertIsNone(payload["filters_applied"]["team_a_id"])
        self.assertTrue(payload["filters_applied"]["warnings"])
        mock_search_teams.assert_called_once()

    @patch(
        "backend.services.match_service.match_repository.search_matches")
    @patch(
        "backend.services.match_service.team_repository.search_teams_by_name")
    def test_search_matches_pair_returns_empty_when_one_team_missing(
        self,
        mock_search_teams: unittest.mock.MagicMock,
        mock_search_matches: unittest.mock.MagicMock) -> None:
        mock_search_teams.side_effect = [
            pd.DataFrame([{
                "id": 10,
                "name": "Górnik Zabrze",
                "shortcut": "GOR",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": None,
                "sport_id": 1,
                "sport_name": "Piłka nożna"
            }]),
            pd.DataFrame()
        ]
        payload = search_matches(
            team_a_query="Górnik",
            team_b_query="Nieistniejaca",
            from_now=True)
        self.assertEqual(payload["matches"], [])
        self.assertEqual(payload["total_count"], 0)
        self.assertEqual(payload["filters_applied"]["team_a_id"], 10)
        self.assertIsNone(payload["filters_applied"]["team_b_id"])
        self.assertTrue(payload["filters_applied"]["warnings"])
        mock_search_matches.assert_not_called()

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.match_service.match_repository.search_matches")
    @patch(
        "backend.services.match_service.team_repository.search_teams_by_name")
    def test_search_matches_both_teams_maps_summary(
        self,
        mock_search_teams: unittest.mock.MagicMock,
        mock_search_matches: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_search_teams.side_effect = [
            pd.DataFrame([{
                "id": 10,
                "name": "Górnik Zabrze",
                "shortcut": "GOR",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": None,
                "sport_id": 1,
                "sport_name": "Piłka nożna"
            }]),
            pd.DataFrame([{
                "id": 20,
                "name": "Śląsk Wrocław",
                "shortcut": "SLA",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": None,
                "sport_id": 1,
                "sport_name": "Piłka nożna"
            }])
        ]
        mock_search_matches.return_value = self._upcoming_match_frame()

        payload = search_matches(
            team_a_query="Górnik",
            team_b_query="Śląsk",
            sport_id=1,
            from_now=True,
            played=False,
            page_size=10)

        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["matches"][0]["id"], 119435)
        self.assertEqual(
            payload["matches"][0]["home_team"]["name"],
            "Górnik Zabrze")
        self.assertFalse(payload["matches"][0]["is_played"])
        self.assertEqual(payload["filters_applied"]["team_a_id"], 10)
        self.assertEqual(payload["filters_applied"]["team_b_id"], 20)
        mock_search_matches.assert_called_once_with(
            team_a_id=10,
            team_b_id=20,
            sport_id=1,
            date_from=None,
            date_to=None,
            from_now=True,
            played=False,
            limit=10)

    @patch(
        "backend.services.match_service.league_repository"
        ".fetch_special_round_names",
        return_value={})
    @patch(
        "backend.services.match_service.match_repository.search_matches",
        return_value=pd.DataFrame())
    @patch(
        "backend.services.match_service.team_repository.search_teams_by_name")
    def test_search_matches_single_team_from_now(
        self,
        mock_search_teams: unittest.mock.MagicMock,
        mock_search_matches: unittest.mock.MagicMock,
        _mock_special_rounds: unittest.mock.MagicMock) -> None:
        mock_search_teams.return_value = pd.DataFrame([{
            "id": 10,
            "name": "Górnik Zabrze",
            "shortcut": "GOR",
            "country_id": 1,
            "country_name": "Polska",
            "country_emoji": None,
            "sport_id": 1,
            "sport_name": "Piłka nożna"
        }])

        payload = search_matches(
            team_a_query="Górnik",
            from_now=True,
            page_size=5)

        self.assertEqual(payload["matches"], [])
        self.assertEqual(payload["total_count"], 0)
        mock_search_matches.assert_called_once_with(
            team_a_id=10,
            team_b_id=None,
            sport_id=None,
            date_from=None,
            date_to=None,
            from_now=True,
            played=None,
            limit=5)

    @patch(
        "backend.services.match_service.team_repository.search_teams_by_name")
    def test_search_matches_warns_on_ambiguous_team(
        self,
        mock_search_teams: unittest.mock.MagicMock) -> None:
        mock_search_teams.return_value = pd.DataFrame([
            {
                "id": 10,
                "name": "Górnik Zabrze",
                "shortcut": "GOR",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": None,
                "sport_id": 1,
                "sport_name": "Piłka nożna"
            },
            {
                "id": 11,
                "name": "Górnik Łęczna",
                "shortcut": "LEC",
                "country_id": 1,
                "country_name": "Polska",
                "country_emoji": None,
                "sport_id": 1,
                "sport_name": "Piłka nożna"
            }
        ])
        with patch(
            "backend.services.match_service.match_repository.search_matches",
            return_value=pd.DataFrame()):
            payload = search_matches(team_a_query="Górnik")
        warnings = payload["filters_applied"]["warnings"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("Multiple teams matched", warnings[0])
        self.assertEqual(payload["filters_applied"]["team_a_id"], 10)


if __name__ == "__main__":
    unittest.main()
