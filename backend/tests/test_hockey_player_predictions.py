"""Unit tests for hockey player-prop mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from api.schemas.match import HockeyPlayerPredictions
from backend.sports.hockey.player_predictions import (
    map_hockey_player_predictions)


class TestHockeyPlayerPredictions(unittest.TestCase):
    """Grouping of stored prop lines by club and skater."""

    def test_groups_lines_per_team_and_drops_other_clubs(self) -> None:
        frame = pd.DataFrame([{
            "player_id": 101,
            "player_name": "Fantilli",
            "team_id": 10,
            "event_id": 190,
            "line": 2.5,
            "expected_value": 2.4,
            "probability": 46.0
        }, {
            "player_id": 101,
            "player_name": "Fantilli",
            "team_id": 10,
            "event_id": 196,
            "line": 0.5,
            "expected_value": 0.3,
            "probability": 26.0
        }, {
            "player_id": 999,
            "player_name": "Other",
            "team_id": 30,
            "event_id": 190,
            "line": 1.5,
            "expected_value": 1.0,
            "probability": 10.0
        }])

        payload = map_hockey_player_predictions(frame, 10, 20)
        assert payload is not None
        HockeyPlayerPredictions.model_validate(payload)
        self.assertEqual(len(payload["home"]), 1)
        self.assertEqual(payload["home"][0]["player_name"], "Fantilli")
        self.assertEqual(len(payload["home"][0]["lines"]), 2)
        self.assertEqual(payload["away"], [])

    def test_empty_frame_returns_none(self) -> None:
        self.assertIsNone(map_hockey_player_predictions(
            pd.DataFrame(),
            10,
            20))
