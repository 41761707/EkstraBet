"""Unit tests for hockey boxscore mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.sports.hockey.boxscore import map_hockey_boxscore


class TestHockeyBoxscore(unittest.TestCase):
    """Tests for hockey player boxscore mapping."""

    def test_map_hockey_boxscore_splits_goalies_and_skaters(self) -> None:
        goalies = pd.DataFrame([{
            "player_id": 1,
            "player_name": "Goalie A",
            "team_id": 10,
            "team_name": "Home",
            "points": 0,
            "penalty_minutes": 0,
            "toi": "60:00",
            "shots_against": 30,
            "shots_saved": 28,
            "saves_acc": 93.33
        }])
        skaters = pd.DataFrame([{
            "player_id": 2,
            "player_name": "Skater A",
            "team_id": 10,
            "team_name": "Home",
            "goals": 2,
            "assists": 1,
            "points": 3,
            "plus_minus": 2,
            "penalty_minutes": 4,
            "sog": 5,
            "toi": "18:32"
        }])

        payload = map_hockey_boxscore(goalies, skaters)

        self.assertEqual(len(payload["goalies"]), 1)
        self.assertEqual(payload["goalies"][0]["saves_accuracy"], 93.33)
        self.assertEqual(len(payload["skaters"]), 1)
        self.assertEqual(payload["skaters"][0]["plus_minus"], 2)

    def test_map_hockey_boxscore_preserves_negative_plus_minus(self) -> None:
        skaters = pd.DataFrame([{
            "player_id": 244,
            "player_name": "Monahan S.",
            "team_id": 870,
            "team_name": "Columbus Blue Jackets",
            "goals": 1,
            "assists": 0,
            "points": 1,
            "plus_minus": -1,
            "penalty_minutes": 0,
            "sog": 3,
            "toi": "16:42"
        }])

        payload = map_hockey_boxscore(pd.DataFrame(), skaters)

        self.assertEqual(payload["skaters"][0]["plus_minus"], -1)


if __name__ == "__main__":
    unittest.main()
