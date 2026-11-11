"""Unit tests for the shared player profile slice read."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

from backend.repositories.player_profile_repository import fetch_profile_slice
from backend.sports.hockey.player_profile import HOCKEY_GOALIE_STAT_SQL
from backend.sports.hockey.player_profile import HOCKEY_SKATER_STAT_SQL
from backend.sports.hockey.player_profile import HockeyPlayerProfileSource


_UNSUPPORTED_TABLE = "Unsupported player profile stats table"


class TestFetchProfileSliceWhitelist(unittest.TestCase):
    """Stats table names enter SQL only after the whitelist check."""

    def test_unknown_table_raises_before_connection(self) -> None:
        with patch(
                "backend.repositories.player_profile_repository"
                ".get_db_connection") as connection:
            with self.assertRaises(ValueError) as caught:
                fetch_profile_slice(
                    "not_a_stats_table",
                    "stat.goals",
                    1,
                    2,
                    None,
                    None,
                    None,
                    None,
                    10)
        self.assertEqual(str(caught.exception), _UNSUPPORTED_TABLE)
        connection.assert_not_called()

    def test_slice_query_applies_optional_filters(self) -> None:
        query, params = _capture_slice(
            "hockey_match_player_stats",
            "stat.points, stat.goals",
            player_id=5,
            sport_id=2,
            season_id=9,
            opponent_team_id=3,
            own_team_id=4,
            teammate_id=8,
            limit=1000)
        self.assertIn("FROM hockey_match_player_stats stat", query)
        self.assertIn(
            "EXISTS (SELECT 1 FROM hockey_match_player_stats mate ",
            query)
        self.assertIn("m.season = %s", query)
        self.assertIn("m.away_team = %s", query)
        self.assertIn("m.home_team = %s", query)
        self.assertIn("stat.team_id = %s", query)
        self.assertIn("mate.player_id = %s", query)
        self.assertIn("stat.points, stat.goals", query)
        self.assertIn("ORDER BY m.game_date DESC, m.id DESC", query)
        self.assertEqual(params, (5, 2, 9, 3, 3, 4, 8, 1000))
        self.assertEqual(query.count("hockey_match_player_stats"), 2)

    def test_unset_filters_stay_out_of_the_query(self) -> None:
        query, params = _capture_slice(
            "football_player_stats",
            "stat.goals",
            player_id=5,
            sport_id=1,
            season_id=None,
            opponent_team_id=None,
            own_team_id=None,
            teammate_id=None,
            limit=10)
        self.assertIn("FROM football_player_stats stat", query)
        self.assertNotIn("m.season = %s", query)
        self.assertNotIn("m.away_team = %s", query)
        self.assertNotIn("stat.team_id = %s", query)
        self.assertNotIn("EXISTS", query)
        self.assertEqual(params, (5, 1, 10))
        self.assertEqual(query.count("football_player_stats"), 1)


class TestHockeyProfileSlice(unittest.TestCase):
    """Hockey slice picks stat columns from the player position."""

    @patch(
        "backend.repositories.player_profile_repository.fetch_profile_slice")
    @patch(
        "backend.repositories.player_profile_repository.fetch_player",
        return_value={"position": "G"})
    def test_goalie_uses_goalie_columns(
            self,
            _fetch_player: MagicMock,
            fetch_slice: MagicMock) -> None:
        fetch_slice.return_value = pd.DataFrame()
        frame = HockeyPlayerProfileSource().fetch_slice(
            15,
            7,
            None,
            None,
            None,
            1000)
        self.assertTrue(frame.empty)
        fetch_slice.assert_called_once_with(
            "hockey_match_player_stats",
            HOCKEY_GOALIE_STAT_SQL,
            15,
            2,
            7,
            None,
            None,
            None,
            1000)

    @patch(
        "backend.repositories.player_profile_repository.fetch_profile_slice")
    @patch(
        "backend.repositories.player_profile_repository.fetch_player",
        return_value={"position": "C"})
    def test_skater_uses_skater_columns(
            self,
            _fetch_player: MagicMock,
            fetch_slice: MagicMock) -> None:
        fetch_slice.return_value = pd.DataFrame()
        HockeyPlayerProfileSource().fetch_slice(
            15,
            None,
            3,
            4,
            8,
            50)
        fetch_slice.assert_called_once_with(
            "hockey_match_player_stats",
            HOCKEY_SKATER_STAT_SQL,
            15,
            2,
            None,
            3,
            4,
            8,
            50)


def _capture_slice(
        stats_table: str,
        stat_select_sql: str,
        player_id: int,
        sport_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None,
        limit: int) -> tuple[str, tuple[object, ...]]:
    with patch(
            "backend.repositories.player_profile_repository"
            ".get_db_connection") as connection, patch(
            "backend.repositories.player_profile_repository.pd.read_sql"
            ) as read_sql:
        connection.return_value.__enter__.return_value = object()
        read_sql.return_value = pd.DataFrame()
        fetch_profile_slice(
            stats_table,
            stat_select_sql,
            player_id,
            sport_id,
            season_id,
            opponent_team_id,
            own_team_id,
            teammate_id,
            limit)
    query = read_sql.call_args[0][0]
    params = read_sql.call_args[1]["params"]
    return query, params
