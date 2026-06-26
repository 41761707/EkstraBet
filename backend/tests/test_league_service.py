"""Unit tests for league service helpers."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from backend.services.league_service import (
    build_league_slug,
    get_league_details,
    get_league_rounds,
    get_league_seasons,
    get_leagues)


class TestBuildLeagueSlug(unittest.TestCase):
    """Tests for league slug generation."""

    def test_simple_name_is_lowercased(self) -> None:
        self.assertEqual(build_league_slug("Ekstraklasa"), "ekstraklasa")

    def test_spaces_are_replaced_with_underscores(self) -> None:
        self.assertEqual(build_league_slug("La Liga"), "la_liga")

    def test_special_characters_are_removed(self) -> None:
        self.assertEqual(
            build_league_slug("2. Liga Austria"),
            "2._liga_austria")


class TestLeagueService(unittest.TestCase):
    """Tests for league service mapping and edge cases."""

    def _sample_league_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "id": 1,
            "name": "Ekstraklasa",
            "country_id": 10,
            "country_name": "Polska",
            "country_emoji": "🇵🇱",
            "sport_id": 1,
            "sport_name": "Football",
            "active": 1,
            "last_update": date(2025, 6, 1),
            "current_season_id": 12,
            "tier": 1,
            "has_player_stats": 1,
        }])

    @patch("backend.services.league_service.league_repository.fetch_leagues")
    def test_get_leagues_returns_empty_list(
        self,
        mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame()
        self.assertEqual(get_leagues(), [])

    @patch("backend.services.league_service.league_repository.fetch_leagues")
    def test_get_leagues_maps_summary_fields(
        self,
        mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = self._sample_league_frame()
        leagues = get_leagues(active=True, sport_id=1)
        self.assertEqual(len(leagues), 1)
        self.assertEqual(leagues[0]["slug"], "ekstraklasa")
        self.assertTrue(leagues[0]["active"])

    @patch(
        "backend.services.league_service.league_repository"
        ".fetch_league_match_count")
    @patch(
        "backend.services.league_service.league_repository"
        ".fetch_seasons_for_league")
    @patch(
        "backend.services.league_service.league_repository.fetch_league_by_id")
    def test_get_league_details_returns_none_for_missing_league(
        self,
        mock_fetch_league: unittest.mock.MagicMock,
        mock_fetch_seasons: unittest.mock.MagicMock,
        mock_fetch_match_count: unittest.mock.MagicMock) -> None:
        mock_fetch_league.return_value = pd.DataFrame()
        self.assertIsNone(get_league_details(999999))
        mock_fetch_seasons.assert_not_called()
        mock_fetch_match_count.assert_not_called()

    @patch(
        "backend.services.league_service.league_repository"
        ".fetch_league_match_count",
        return_value=380)
    @patch(
        "backend.services.league_service.league_repository"
        ".fetch_seasons_for_league")
    @patch(
        "backend.services.league_service.league_repository.fetch_league_by_id")
    def test_get_league_details_includes_seasons_and_match_count(
        self,
        mock_fetch_league: unittest.mock.MagicMock,
        mock_fetch_seasons: unittest.mock.MagicMock,
        _mock_fetch_match_count: unittest.mock.MagicMock) -> None:
        mock_fetch_league.return_value = self._sample_league_frame()
        mock_fetch_seasons.return_value = pd.DataFrame([{
            "season_id": 12,
            "years": "2024/25",
            "match_count": 306,
        }])
        details = get_league_details(1)
        assert details is not None
        self.assertEqual(details["match_count"], 380)
        self.assertEqual(len(details["seasons"]), 1)
        self.assertEqual(details["seasons"][0]["years"], "2024/25")

    @patch(
        "backend.services.league_service.league_repository.league_exists",
        return_value=False)
    def test_get_league_seasons_returns_none_for_missing_league(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_league_seasons(999999))

    @patch(
        "backend.services.league_service.league_repository.league_exists",
        return_value=True)
    @patch(
        "backend.services.league_service.league_repository"
        ".fetch_seasons_for_league",
        return_value=pd.DataFrame())
    def test_get_league_seasons_returns_empty_list(
        self,
        _mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        seasons = get_league_seasons(1)
        self.assertEqual(seasons, [])

    @patch(
        "backend.services.league_service.league_repository.league_exists",
        return_value=False)
    def test_get_league_rounds_returns_none_for_missing_league(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_league_rounds(999999, 1))


if __name__ == "__main__":
    unittest.main()
