"""Unit tests for bet recommendation service helpers."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from backend.services.bet_service import (
    BETTING_TAX_RATE,
    _compute_ev_after_tax,
    _map_settlement_status,
    get_bet_recommendations)


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

    @patch(
        "backend.services.bet_service.bet_repository.search_bet_recommendations")
    def test_get_bet_recommendations_maps_rows(
        self,
        mock_search: unittest.mock.MagicMock) -> None:
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
            "probability": 0.55,
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
            positive_ev_only=True,
            apply_tax=True)
        recommendation = payload["recommendations"][0]
        self.assertEqual(recommendation["settlement_status"], "pending")
        self.assertEqual(recommendation["bookmaker_name"], "STS")
        self.assertAlmostEqual(
            recommendation["ev_after_tax"],
            0.55 * 2.0 * (1 - BETTING_TAX_RATE) - 1)
        self.assertEqual(payload["total_count"], 1)


if __name__ == "__main__":
    unittest.main()
