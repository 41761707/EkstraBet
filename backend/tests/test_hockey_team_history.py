"""Tests for hockey team history opponent labels."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from api.schemas.sport_league import HockeyTeamHistoryPoint
from backend.sports.hockey.team_history import build_hockey_team_history


TEAM_ID = 100
HOME_OPPONENT_ID = 200
AWAY_OPPONENT_ID = 300


def _hockey_matches() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": 1,
            "game_date": datetime(2025, 3, 10, 19, 0),
            "result": "1",
            "home_id": TEAM_ID,
            "away_id": HOME_OPPONENT_ID,
            "home_name": "Rangers",
            "away_name": "Bruins",
            "home_shortcut": "NYR",
            "away_shortcut": "BOS",
            "home_team_goals": 3,
            "away_team_goals": 2,
            "home_team_sog": 28,
            "away_team_sog": 22,
            "hma_ot": 0,
            "hma_so": 0,
            "hma_ot_winner": 0,
            "hma_so_winner": 0
        },
        {
            "id": 2,
            "game_date": datetime(2025, 3, 12, 19, 0),
            "result": "1",
            "home_id": AWAY_OPPONENT_ID,
            "away_id": TEAM_ID,
            "home_name": "Maple Leafs",
            "away_name": "Rangers",
            "home_shortcut": "TOR",
            "away_shortcut": "NYR",
            "home_team_goals": 1,
            "away_team_goals": 4,
            "home_team_sog": 20,
            "away_team_sog": 31,
            "hma_ot": 0,
            "hma_so": 0,
            "hma_ot_winner": 0,
            "hma_so_winner": 0
        }
    ])


def test_hockey_team_history_includes_opponent_name_home_and_away() -> None:
    history = build_hockey_team_history(TEAM_ID, _hockey_matches(), lookback=10)
    by_match_id = {point["match_id"]: point for point in history}

    home_game = by_match_id[1]
    away_game = by_match_id[2]
    assert home_game["opponent_shortcut"] == "BOS"
    assert home_game["opponent_name"] == "Bruins"
    assert away_game["opponent_shortcut"] == "TOR"
    assert away_game["opponent_name"] == "Maple Leafs"

    HockeyTeamHistoryPoint.model_validate(home_game)
    HockeyTeamHistoryPoint.model_validate(away_game)
