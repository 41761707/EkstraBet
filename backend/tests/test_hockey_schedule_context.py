"""Unit tests for prematch NHL schedule context."""

from __future__ import annotations

import unittest
from datetime import datetime

import pandas as pd

from backend.sports.hockey.schedule_context import (
    build_hockey_schedule_context)
from models.pipeline.features.hockey.schedule import (
    build_schedule_features)


WEST_TEAM = 2
EAST_TEAM = 1
# 06:00 w Warszawie to 21:00 poprzedniego dnia w Los Angeles.
EVENING_STORED = "2025-01-12 06:00"
# 22:00 w Warszawie to 13:00 tego samego dnia lokalnego na Zachodzie.
AFTERNOON_STORED = "2025-01-12 22:00"


class TestHockeyScheduleContext(unittest.TestCase):
    """Rest follows each match's home-arena local date."""

    def test_west_coast_evening_then_afternoon_matches_the_model(
        self) -> None:
        prior = _history_row(1, EVENING_STORED, WEST_TEAM, EAST_TEAM)
        context = build_hockey_schedule_context(
            prior,
            prior,
            _arenas(),
            match_id=2,
            home_team_id=WEST_TEAM,
            away_team_id=EAST_TEAM,
            game_date=datetime(2025, 1, 12, 22, 0))
        features = build_schedule_features(
            pd.DataFrame([
                _feature_match(1, EVENING_STORED, "1"),
                _feature_match(2, AFTERNOON_STORED, "0")]),
            _arenas())
        assert context is not None
        home = features.loc[features["match_id"] == 2].iloc[0]
        self.assertEqual(
            context["home"]["rest_days"],
            int(home["home_rest_days"]))
        self.assertEqual(
            context["home"]["is_b2b"],
            float(home["home_is_b2b"]) == 1.0)
        self.assertEqual(
            context["home"]["games_last_7_days"],
            int(home["home_games_last_7_days"]))
        self.assertEqual(
            context["away"]["rest_days"],
            int(home["away_rest_days"]))
        self.assertEqual(context["home"]["rest_days"], 1)
        self.assertTrue(context["home"]["is_b2b"])
        self.assertEqual(context["home"]["games_last_7_days"], 2)
        self.assertTrue(context["away"]["is_b2b"])

    def test_warsaw_gap_of_one_day_is_a_back_to_back(self) -> None:
        prior = _history_row(
            1,
            datetime(2026, 10, 1, 19, 0),
            WEST_TEAM,
            99)
        context = build_hockey_schedule_context(
            prior,
            pd.DataFrame(),
            _warsaw_arenas(),
            match_id=2,
            home_team_id=WEST_TEAM,
            away_team_id=EAST_TEAM,
            game_date=datetime(2026, 10, 2, 19, 0))
        assert context is not None
        self.assertEqual(context["home"]["rest_days"], 1)
        self.assertTrue(context["home"]["is_b2b"])
        self.assertEqual(context["home"]["games_last_7_days"], 2)
        self.assertEqual(context["away"]["rest_days"], 0)
        self.assertFalse(context["away"]["is_b2b"])
        self.assertEqual(context["away"]["games_last_7_days"], 1)

    def test_missing_kickoff_returns_none(self) -> None:
        self.assertIsNone(build_hockey_schedule_context(
            pd.DataFrame(),
            pd.DataFrame(),
            _arenas(),
            match_id=2,
            home_team_id=WEST_TEAM,
            away_team_id=EAST_TEAM,
            game_date=None))


def _arenas() -> pd.DataFrame:
    """New York and Los Angeles halls."""
    return pd.DataFrame([
        {
            "team_id": EAST_TEAM,
            "latitude": 40.0,
            "longitude": -74.0,
            "timezone": "America/New_York"},
        {
            "team_id": WEST_TEAM,
            "latitude": 34.0,
            "longitude": -118.0,
            "timezone": "America/Los_Angeles"}])


def _warsaw_arenas() -> pd.DataFrame:
    """Both clubs share the stored clock, so local date is Warsaw."""
    return pd.DataFrame([
        {
            "team_id": EAST_TEAM,
            "latitude": 52.2,
            "longitude": 21.0,
            "timezone": "Europe/Warsaw"},
        {
            "team_id": WEST_TEAM,
            "latitude": 52.2,
            "longitude": 21.0,
            "timezone": "Europe/Warsaw"}])


def _history_row(
    match_id: int,
    game_date: object,
    home_id: int,
    away_id: int) -> pd.DataFrame:
    """One completed game in the shape of team history."""
    return pd.DataFrame([{
        "id": match_id,
        "home_id": home_id,
        "away_id": away_id,
        "game_date": game_date,
        "result": "1"}])


def _feature_match(
    match_id: int,
    game_date: str,
    result: str) -> dict[str, object]:
    """One row for the schedule-feature builder."""
    return {
        "match_id": match_id,
        "home_team": WEST_TEAM,
        "away_team": EAST_TEAM,
        "game_date": game_date,
        "result": result}
