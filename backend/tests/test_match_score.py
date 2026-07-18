"""Unit tests for match score resolution mapping and formatting."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.services.match_score import (
    map_hockey_score_resolution,
    map_score_resolution)


class TestMapScoreResolution(unittest.TestCase):
    """Tests for cup knockout score metadata mapping."""

    def test_returns_none_without_special_round_row(self) -> None:
        row = pd.Series({"fsr_ot": None})
        self.assertIsNone(map_score_resolution(row))

    def test_maps_extra_time_without_penalties(self) -> None:
        row = pd.Series({
            "fsr_ot": 1,
            "fsr_pen": 0,
            "fsr_regulation_home_goals": 2,
            "fsr_regulation_away_goals": 2,
            "fsr_penalties_home_goals": 0,
            "fsr_penalties_away_goals": 0,
        })
        resolution = map_score_resolution(row)
        assert resolution is not None
        self.assertTrue(resolution["has_extra_time"])
        self.assertFalse(resolution["has_penalties"])
        self.assertEqual(resolution["regulation_home_goals"], 2)
        self.assertIsNone(resolution["penalties_home_goals"])

    def test_maps_penalty_shootout(self) -> None:
        row = pd.Series({
            "fsr_ot": 1,
            "fsr_pen": 1,
            "fsr_regulation_home_goals": 2,
            "fsr_regulation_away_goals": 2,
            "fsr_penalties_home_goals": 4,
            "fsr_penalties_away_goals": 3,
        })
        resolution = map_score_resolution(row)
        assert resolution is not None
        self.assertTrue(resolution["has_penalties"])
        self.assertEqual(resolution["penalties_home_goals"], 4)


class TestMapHockeyScoreResolution(unittest.TestCase):
    """Tests for NHL overtime and shootout metadata."""

    def test_maps_overtime_without_shootout(self) -> None:
        row = pd.Series({
            "hma_ot": 1,
            "hma_so": 0,
            "hma_ot_winner": 1,
            "hma_so_winner": 0,
            "home_team_goals": 4,
            "away_team_goals": 4,
        })
        resolution = map_hockey_score_resolution(row)
        assert resolution is not None
        self.assertTrue(resolution["has_extra_time"])
        self.assertFalse(resolution["has_penalties"])
        self.assertEqual(resolution["regulation_home_goals"], 4)

    def test_maps_shootout_from_so_flag(self) -> None:
        row = pd.Series({
            "hma_ot": 1,
            "hma_so": 1,
            "hma_ot_winner": 3,
            "hma_so_winner": 2,
            "home_team_goals": 2,
            "away_team_goals": 2,
        })
        resolution = map_hockey_score_resolution(row)
        assert resolution is not None
        self.assertFalse(resolution["has_extra_time"])
        self.assertTrue(resolution["has_penalties"])
        self.assertEqual(resolution["shootout_winner"], 2)

    def test_hockey_resolution_used_for_sport_id_two(self) -> None:
        row = pd.Series({
            "sport_id": 2,
            "hma_ot": 1,
            "hma_so": 0,
            "hma_ot_winner": 2,
            "hma_so_winner": 0,
            "home_team_goals": 3,
            "away_team_goals": 3,
        })
        resolution = map_score_resolution(row)
        assert resolution is not None
        self.assertTrue(resolution["has_extra_time"])


if __name__ == "__main__":
    unittest.main()
