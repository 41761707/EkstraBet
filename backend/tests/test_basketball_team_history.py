"""Tests for basketball team history opponent labels."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from api.schemas.sport_league import BasketballTeamHistoryPoint
from backend.sports.basketball.team_history import build_basketball_team_history


TEAM_ID = 10
HOME_OPPONENT_ID = 20
AWAY_OPPONENT_ID = 30


def _basketball_matches() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": 1,
            "game_date": datetime(2025, 3, 10, 19, 0),
            "result": "1",
            "home_id": TEAM_ID,
            "away_id": HOME_OPPONENT_ID,
            "home_name": "Boston Celtics",
            "away_name": "Los Angeles Lakers",
            "home_shortcut": "BOS",
            "away_shortcut": "LAL",
            "home_team_goals": 112,
            "away_team_goals": 108
        },
        {
            "id": 2,
            "game_date": datetime(2025, 3, 12, 19, 0),
            "result": "1",
            "home_id": AWAY_OPPONENT_ID,
            "away_id": TEAM_ID,
            "home_name": "Golden State Warriors",
            "away_name": "Boston Celtics",
            "home_shortcut": "GSW",
            "away_shortcut": "BOS",
            "home_team_goals": 99,
            "away_team_goals": 105
        }
    ])


def test_basketball_team_history_includes_opponent_name_home_and_away() -> None:
    history = build_basketball_team_history(
        TEAM_ID,
        _basketball_matches(),
        lookback=10)
    by_match_id = {point["match_id"]: point for point in history}

    home_game = by_match_id[1]
    away_game = by_match_id[2]
    assert home_game["opponent_shortcut"] == "LAL"
    assert home_game["opponent_name"] == "Los Angeles Lakers"
    assert away_game["opponent_shortcut"] == "GSW"
    assert away_game["opponent_name"] == "Golden State Warriors"

    BasketballTeamHistoryPoint.model_validate(home_game)
    BasketballTeamHistoryPoint.model_validate(away_game)
