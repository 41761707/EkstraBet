"""Unit tests for odds service helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services.odds_service import get_match_odds


class TestOddsService(unittest.TestCase):
    """Tests for unified odds mapping."""

    @patch(
        "backend.services.odds_service.match_repository.match_exists",
        return_value=False)
    def test_get_match_odds_returns_none_for_missing_match(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_match_odds(999999))

    @patch(
        "backend.services.odds_service.match_repository.match_exists",
        return_value=True)
    @patch("backend.services.odds_service.odds_repository.fetch_match_odds")
    def test_get_match_odds_maps_unified_structure(
        self,
        mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame([{
            "id": 1,
            "match_id": 100,
            "bookmaker_id": 4,
            "bookmaker_name": "STS",
            "event_id": 5,
            "event_name": "1",
            "event_family_id": 2,
            "event_family_name": "REZULTAT",
            "odds": 1.95,
        }])
        payload = get_match_odds(100)
        assert payload is not None
        odds = payload["odds"][0]
        self.assertEqual(odds["bookmaker_id"], 4)
        self.assertEqual(odds["event_id"], 5)
        self.assertEqual(odds["event_family"]["name"], "REZULTAT")


if __name__ == "__main__":
    unittest.main()
