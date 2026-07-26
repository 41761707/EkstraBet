"""Unit tests for bet recommendation service helpers."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.repositories.bet_repository import _build_filters
from backend.services.bet_service import (
    BETTING_TAX_RATE,
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
        mock_search.assert_called_once()
        self.assertEqual(mock_search.call_args.kwargs["match_id"], 100)

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


if __name__ == "__main__":
    unittest.main()
