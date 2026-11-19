"""Unit tests for bet recommendation service helpers."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.repositories.bet_repository import _build_filters
from backend.services.bet_service import (
    _compute_ev_after_tax,
    _map_settlement_status,
    get_bet_recommendations,
    get_market_opportunities)


class TestBetService(unittest.TestCase):
    """Tests for bet recommendation mapping and filters."""

    def test_compute_ev_after_tax_returns_none_when_disabled(self) -> None:
        self.assertIsNone(_compute_ev_after_tax(0.5, 2.0, False, 0.12))

    def test_compute_ev_after_tax_applies_polish_tax(self) -> None:
        value = _compute_ev_after_tax(0.5, 2.0, True, BETTING_TAX_RATE)
        self.assertAlmostEqual(value, 0.5 * 2.0 * (1 - 0.12) - 1)

    def test_map_settlement_status_handles_pending_and_results(self) -> None:
        self.assertEqual(_map_settlement_status(None), "pending")
        self.assertEqual(_map_settlement_status(1), "won")
        self.assertEqual(_map_settlement_status(0), "lost")

    def test_build_filters_includes_match_id(self) -> None:
        conditions, params = _build_filters(
            league_ids=None,
            season_id=None,
            event_ids=None,
            model_ids=None,
            bookmaker_ids=None,
            match_id=119435,
            match_date=None,
            date_from=None,
            date_to=None,
            from_now=False,
            min_odds=None,
            positive_ev_only=False,
            apply_tax=False,
            tax_rate=0.12,
            settlement_status=None)
        self.assertIn("b.match_id = %s", conditions)
        self.assertEqual(params, [119435])

    def test_build_filters_positive_ev_uses_normalized_probability(self) -> None:
        conditions, params = _build_filters(
            league_ids=None,
            season_id=None,
            event_ids=None,
            model_ids=None,
            bookmaker_ids=None,
            match_id=None,
            match_date=None,
            date_from=None,
            date_to=None,
            from_now=False,
            min_odds=None,
            positive_ev_only=True,
            apply_tax=True,
            tax_rate=0.12,
            settlement_status=None)
        self.assertTrue(
            any("p.value / 100.0" in condition for condition in conditions))
        self.assertEqual(params, [0.12])
        self.assertFalse(any("b.EV > 0" in condition for condition in conditions))

    def test_build_filters_positive_ev_without_tax_recalculates(self) -> None:
        conditions, params = _build_filters(
            league_ids=None,
            season_id=None,
            event_ids=None,
            model_ids=None,
            bookmaker_ids=None,
            match_id=None,
            match_date=None,
            date_from=None,
            date_to=None,
            from_now=False,
            min_odds=None,
            positive_ev_only=True,
            apply_tax=False,
            tax_rate=0.12,
            settlement_status=None)
        self.assertTrue(
            any("p.value / 100.0" in condition for condition in conditions))
        self.assertEqual(params, [])
        self.assertFalse(any("b.EV > 0" in condition for condition in conditions))

    @patch(
        "backend.services.bet_service.bet_repository.search_bet_recommendations")
    def test_get_bet_recommendations_maps_db_percentage(
        self,
        mock_search: MagicMock) -> None:
        mock_search.return_value = (pd.DataFrame([{
            "bet_id": 10,
            "match_id": 100,
            "event_id": 1,
            "odds": 2.0,
            "ev": 0.1,
            "bet_outcome": None,
            "custom_bet": 0,
            "bookmaker_id": 4,
            "bookmaker_name": "STS",
            "prediction_id": 50,
            "probability": 55.0,
            "model_id": 2,
            "model_name": "Model A",
            "game_date": datetime(2026, 6, 27, 18, 0, 0),
            "league_id": 1,
            "league_name": "Ekstraklasa",
            "season_id": 5,
            "home_team_id": 11,
            "home_team_name": "Legia",
            "home_team_shortcut": "LEG",
            "away_team_id": 12,
            "away_team_name": "Lech",
            "away_team_shortcut": "LPO",
            "event_name": "1",
            "event_family_id": 2,
            "event_family_name": "REZULTAT",
        }]), 1)
        payload = get_bet_recommendations(
            match_id=100,
            positive_ev_only=True,
            apply_tax=True)
        recommendation = payload["recommendations"][0]
        self.assertEqual(recommendation["settlement_status"], "pending")
        self.assertEqual(recommendation["bookmaker_name"], "STS")
        self.assertAlmostEqual(recommendation["probability"], 0.55)
        self.assertAlmostEqual(recommendation["probability_pct"], 55.0)
        self.assertAlmostEqual(recommendation["ev"], 0.55 * 2.0 - 1)
        self.assertAlmostEqual(
            recommendation["ev_after_tax"],
            0.55 * 2.0 * (1 - BETTING_TAX_RATE) - 1)
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["filters_applied"]["match_id"], 100)
        self.assertIsNone(recommendation["history"])
        mock_search.assert_called_once()
        self.assertEqual(mock_search.call_args.kwargs["match_id"], 100)

    @patch(
        "backend.services.bet_service.fetch_team_recent_matches")
    @patch(
        "backend.services.bet_service.bet_repository.search_bet_recommendations")
    def test_history_is_oldest_first_for_an_under_market(
        self,
        mock_search: MagicMock,
        mock_history: MagicMock) -> None:
        mock_search.return_value = (pd.DataFrame([{
            "bet_id": 10,
            "match_id": 100,
            "event_id": 12,
            "odds": 2.4,
            "ev": 0.1,
            "bet_outcome": 0,
            "custom_bet": 0,
            "bookmaker_id": 4,
            "bookmaker_name": "STS",
            "prediction_id": 50,
            "probability": 62.0,
            "model_id": 2,
            "model_name": "Model A",
            "game_date": datetime(2026, 11, 8, 1, 30),
            "sport_id": 1,
            "league_id": 1,
            "league_name": "Serie B Brasil",
            "season_id": 5,
            "home_team_id": 11,
            "home_team_name": "Nautico",
            "home_team_shortcut": "NAU",
            "away_team_id": 12,
            "away_team_name": "CRB",
            "away_team_shortcut": "CRB",
            "event_name": "Poniżej 2.5 gola",
            "event_family_id": 3,
            "event_family_name": "OU",
        }]), 1)
        mock_history.return_value = pd.DataFrame([
            _history_row(
                match_id=90,
                game_date=datetime(2026, 11, 1, 20, 0),
                home_team_id=11,
                away_team_id=30,
                home_goals=3,
                away_goals=2,
                result="1"),
            _history_row(
                match_id=80,
                game_date=datetime(2026, 10, 20, 20, 0),
                home_team_id=40,
                away_team_id=11,
                home_goals=0,
                away_goals=1,
                result="2"),
        ])
        payload = get_bet_recommendations(history_window=10)
        history = payload["recommendations"][0]["history"]
        self.assertEqual(history["line"], 2.5)
        self.assertEqual(history["side"], "under")
        home, away = history["series"]
        self.assertEqual(home["sample"], "home")
        self.assertEqual(home["played"], 2)
        self.assertEqual(home["hits"], 1)
        self.assertEqual(
            home["points"],
            [{"value": 1.0}, {"value": 5.0}])
        self.assertEqual(home["subject_name"], "Nautico")
        self.assertEqual(home["subject_shortcut"], "NAU")
        self.assertEqual(away["sample"], "away")
        self.assertEqual(away["played"], 0)
        self.assertEqual(away["hits"], 0)
        self.assertEqual(away["points"], [])
        self.assertEqual(away["subject_name"], "CRB")
        self.assertEqual(away["subject_shortcut"], "CRB")
        anchors = mock_history.call_args.args[0]
        self.assertEqual([anchor[0] for anchor in anchors], [11, 12])
        self.assertEqual(anchors[0][1], 100)
        self.assertEqual(anchors[0][4], "goals")
        self.assertEqual(anchors[1][4], "goals")

    @patch(
        "backend.services.bet_service.fetch_team_recent_matches")
    @patch(
        "backend.services.bet_service.bet_repository.search_bet_recommendations")
    def test_history_sort_uses_both_teams_then_slices_the_page(
        self,
        mock_search: MagicMock,
        mock_history: MagicMock) -> None:
        mock_search.return_value = (pd.DataFrame([
            _under_row(bet_id=1, match_id=100, home_team_id=11, away_team_id=12),
            _under_row(bet_id=2, match_id=200, home_team_id=21, away_team_id=22),
        ]), 2)
        mock_history.return_value = pd.DataFrame([
            _counted_match(11, 100, 90, 1, 0),
            _counted_match(12, 100, 91, 3, 3),
            _counted_match(21, 200, 80, 0, 0),
            _counted_match(22, 200, 81, 1, 0),
        ])
        payload = get_bet_recommendations(
            sort_by="history", sort_order="desc", page=1, page_size=1)
        self.assertEqual(
            payload["recommendations"][0]["bet_id"], 2)
        self.assertEqual(len(payload["recommendations"]), 1)
        self.assertEqual(payload["total_count"], 2)
        self.assertTrue(mock_search.call_args.kwargs["unbounded"])
        self.assertEqual(mock_search.call_args.kwargs["sort_by"], "ev")
        self.assertEqual(mock_search.call_args.kwargs["page"], 1)

    @patch(
        "backend.services.bet_service.bet_repository"
        ".search_market_opportunities")
    def test_get_market_opportunities_maps_tiers(
        self,
        mock_search: MagicMock) -> None:
        mock_search.return_value = (
            pd.DataFrame([
                {
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
                    "ev": 0.155,
                    "ev_after_tax": 0.0164,
                    "source": "bet",
                    "ranking_basis": "ev_after_tax",
                },
                {
                    "match_id": 101,
                    "sport_id": 1,
                    "league_id": 2,
                    "league_name": "1. Liga",
                    "game_date": datetime(2026, 7, 26, 20, 0, 0),
                    "home_team": "Gornik",
                    "away_team": "Slask",
                    "event_id": 12,
                    "event_name": "Ponizej 2.5 gola",
                    "model_id": 3,
                    "model_name": "Model B",
                    "probability": 0.62,
                    "probability_pct": 62.0,
                    "odds": None,
                    "bookmaker_id": None,
                    "bookmaker_name": None,
                    "ev": None,
                    "ev_after_tax": None,
                    "source": "prediction",
                    "ranking_basis": "probability",
                },
            ]),
            2,
            {"bet": 1, "prediction": 1})
        payload = get_market_opportunities(
            sport_id=1,
            match_date=datetime(2026, 7, 26).date(),
            limit=10)
        self.assertEqual(payload["total_count"], 2)
        self.assertEqual(payload["source_counts"]["bet"], 1)
        self.assertEqual(payload["source_counts"]["prediction"], 1)
        self.assertEqual(len(payload["opportunities"]), 2)
        self.assertIsNone(payload["opportunities"][1]["odds"])
        self.assertTrue(any("no odds" in warning for warning in payload["warnings"]))
        mock_search.assert_called_once()
        self.assertEqual(mock_search.call_args.kwargs["sport_id"], 1)
        self.assertTrue(mock_search.call_args.kwargs["one_per_match"])


def _history_row(
        *,
        match_id: int,
        game_date: datetime,
        home_team_id: int,
        away_team_id: int,
        home_goals: int,
        away_goals: int,
        result: str) -> dict[str, object]:
    """One raw history query row for the home team of fixture 100."""
    return {
        "team_id": 11,
        "anchor_match_id": 100,
        "match_id": match_id,
        "game_date": game_date,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": result,
        "home_corners": None,
        "away_corners": None,
        "home_fouls": None,
        "away_fouls": None,
        "home_yellows": None,
        "away_yellows": None,
        "home_offsides": None,
        "away_offsides": None,
        "ot_winner": None,
        "so_winner": None,
        "stat_filter": "goals"}


def _under_row(
        *,
        bet_id: int,
        match_id: int,
        home_team_id: int,
        away_team_id: int) -> dict[str, object]:
    """One under-2.5 recommendation. History is filled by the mock."""
    return {
        "bet_id": bet_id,
        "match_id": match_id,
        "event_id": 12,
        "odds": 2.4,
        "ev": 0.1,
        "bet_outcome": None,
        "custom_bet": 0,
        "bookmaker_id": 4,
        "bookmaker_name": "STS",
        "prediction_id": 50,
        "probability": 62.0,
        "model_id": 2,
        "model_name": "Model A",
        "game_date": datetime(2026, 11, 8, 1, 30),
        "sport_id": 1,
        "league_id": 1,
        "league_name": "Serie B Brasil",
        "season_id": 5,
        "home_team_id": home_team_id,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": away_team_id,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "event_name": "Poniżej 2.5 gola",
        "event_family_id": 3,
        "event_family_name": "OU"}


def _counted_match(
        team_id: int,
        anchor_match_id: int,
        match_id: int,
        home_goals: int,
        away_goals: int) -> dict[str, object]:
    """One past match already attributed to a team anchor."""
    row = _history_row(
        match_id=match_id,
        game_date=datetime(2026, 10, 1, 20, 0),
        home_team_id=team_id,
        away_team_id=99,
        home_goals=home_goals,
        away_goals=away_goals,
        result="1")
    row["team_id"] = team_id
    row["anchor_match_id"] = anchor_match_id
    return row


if __name__ == "__main__":
    unittest.main()
