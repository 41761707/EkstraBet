"""Tests for hockey season match point mapping."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from api.schemas.match import TeamSeasonMatchPoint
from backend.sports.hockey.season_match_point import map_hockey_season_match_point


def _hockey_match_row() -> pd.Series:
    return pd.Series({
        "id": 501,
        "game_date": datetime(2025, 3, 10, 19, 0),
        "home_id": 100,
        "away_id": 200,
        "home_name": "Rangers",
        "away_name": "Bruins",
        "home_shortcut": "NYR",
        "away_shortcut": "BOS",
        "home_team_goals": 3,
        "away_team_goals": 2,
        "hma_ot": 0,
        "hma_so": 0,
        "home_team_sc": 30,
        "away_team_sc": 25,
        "home_team_sog": 28,
        "away_team_sog": 22,
        "home_team_fk": 8,
        "away_team_fk": 12,
        "home_team_fouls": 4,
        "away_team_fouls": 6,
    })


def test_map_hockey_season_match_point_includes_zero_foul_fields() -> None:
    mapped = map_hockey_season_match_point(100, _hockey_match_row())
    assert mapped["team_fouls"] == 0
    assert mapped["opponent_fouls"] == 0
    assert mapped["total_fouls"] == 0


def test_map_hockey_season_match_point_validates_against_team_season_schema() -> None:
    mapped = map_hockey_season_match_point(
        100,
        _hockey_match_row(),
        first_period_goals=1)
    validated = TeamSeasonMatchPoint.model_validate(mapped)
    assert validated.team_fouls == 0
    assert validated.opponent_fouls == 0
    assert validated.total_fouls == 0
    assert validated.team_penalties == 4
    assert validated.opponent_penalties == 6
