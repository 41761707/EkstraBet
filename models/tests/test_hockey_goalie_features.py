"""Shrunk goalie save percentage, GSAA/60 and as-of windows."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd
import pytest

from models.pipeline.features.hockey.goalies import GoalieRatingState
from models.pipeline.features.hockey.goalies import GoalieRatingsConfig
from models.pipeline.features.hockey.goalies import build_goalie_ratings
from models.pipeline.features.hockey.ratings import (
    build_hockey_pre_match_ratings)


def test_small_sample_shrinks_toward_the_league() -> None:
    start = datetime(2024, 10, 1, 1, 0)
    rows = [
        _appearance(1, 1, 10, start, 10000, 9000, 3600),
        _appearance(2, 2, 20, start + timedelta(days=10), 10, 10, 3600),
        _appearance(3, 2, 20, start + timedelta(days=20), 20, 18, 3600)]
    rated = build_goalie_ratings(pd.DataFrame(rows))
    cold = rated.loc[rated["match_id"] == 3].iloc[0]
    league_save = (9000 + 10) / (10000 + 10)
    expected = (10 + 1000 * league_save) / (10 + 1000)
    assert cold["goalie_shots"] == 10
    assert cold["goalie_save_pct"] == pytest.approx(expected)
    assert abs(expected - league_save) < abs(1.0 - league_save)


def test_same_slate_does_not_leak_into_the_league_prior() -> None:
    start = datetime(2024, 10, 1, 1, 0)
    same_night = start + timedelta(days=10)
    next_day = same_night + timedelta(days=1)
    rows = [
        _appearance(1, 1, 10, start, 10000, 9000, 3600),
        _appearance(2, 2, 20, same_night, 40, 40, 3600),
        _appearance(3, 3, 30, same_night, 25, 22, 3600),
        _appearance(4, 4, 40, next_day, 25, 22, 3600)]
    rated = build_goalie_ratings(pd.DataFrame(rows))
    debut = rated.loc[rated["match_id"] == 3].iloc[0]
    later = rated.loc[rated["match_id"] == 4].iloc[0]
    assert debut["goalie_save_pct"] == pytest.approx(0.9)
    assert later["goalie_shots"] == 0
    assert later["goalie_save_pct"] > debut["goalie_save_pct"]


def test_shots_older_than_the_window_are_dropped() -> None:
    start = datetime(2024, 1, 1, 1, 0)
    rows = [
        _appearance(1, 7, 70, start, 20, 20, 3600),
        _appearance(
            2, 7, 70, start + timedelta(days=400), 30, 27, 3600)]
    rated = build_goalie_ratings(pd.DataFrame(rows))
    later = rated.loc[rated["match_id"] == 2].iloc[0]
    assert later["goalie_shots"] == 0
    assert later["goalie_save_pct"] == pytest.approx(0.9)
    assert later["goalie_gsaa_per_60"] == 0.0


def test_gsaa_per_60_uses_the_league_rate_and_ice_time() -> None:
    start = datetime(2024, 10, 1, 1, 0)
    rows = [
        _appearance(1, 1, 10, start, 10000, 9000, 3600),
        _appearance(2, 4, 40, start + timedelta(days=1), 600, 570, 36000),
        _appearance(3, 4, 40, start + timedelta(days=2), 30, 27, 3600)]
    rated = build_goalie_ratings(pd.DataFrame(rows))
    follow_up = rated.loc[rated["match_id"] == 3].iloc[0]
    league_save = (9000 + 570) / (10000 + 600)
    gsaa = 570 - 600 * league_save
    assert follow_up["goalie_gsaa_per_60"] == pytest.approx(
        gsaa * 60.0 / 600.0)
    assert follow_up["goalie_gsaa_per_60"] > 0


def test_goalie_without_ice_time_has_zero_gsaa_rate() -> None:
    start = datetime(2024, 10, 1)
    later = start + timedelta(days=1)
    rows = [
        _appearance(1, 5, 50, start, 30, 28, None),
        _appearance(2, 5, 50, later, 30, 28, None)]
    rated = build_goalie_ratings(pd.DataFrame(rows))
    assert rated.loc[1, "goalie_shots"] == 30
    assert rated.loc[1, "goalie_gsaa_per_60"] == 0.0


def test_line_one_goalie_beats_a_busier_backup() -> None:
    match_date = datetime(2024, 11, 1, 1, 0)
    history = datetime(2024, 10, 1, 1, 0)
    appearances = pd.DataFrame([
        _appearance(10, 8, 1, history, 500, 480, 3600),
        _appearance(10, 9, 1, history, 500, 430, 3600),
        _appearance(11, 9, 2, history, 500, 450, 3600),
        _appearance(20, 8, 1, match_date, 5, 4, 3600),
        _appearance(20, 9, 1, match_date, 35, 32, 3600),
        _appearance(20, 11, 2, match_date, 30, 27, 3600)])
    rosters = pd.DataFrame([
        _roster(20, 8, 1, "G", 1),
        _roster(20, 9, 1, "G", 2),
        _roster(20, 11, 2, "G", 1)])
    rated = build_hockey_pre_match_ratings(
        _finished_match(20, match_date), appearances, rosters)
    assert int(rated.loc[0, "home_goalie_id"]) == 8
    goalies = build_goalie_ratings(appearances)
    starter = goalies.loc[
        (goalies["match_id"] == 20) & (goalies["player_id"] == 8)
    ].iloc[0]
    assert rated.loc[0, "home_goalie_save_pct"] == pytest.approx(
        starter["goalie_save_pct"])


def test_duplicate_line_one_goalies_use_shots_as_tiebreak() -> None:
    match_date = datetime(2024, 11, 1, 1, 0)
    appearances = pd.DataFrame([
        _appearance(20, 8, 1, match_date, 12, 10, 1800),
        _appearance(20, 9, 1, match_date, 20, 18, 1800)])
    rosters = pd.DataFrame([
        _roster(20, 8, 1, "G", 1),
        _roster(20, 9, 1, "G", 1)])
    rated = build_hockey_pre_match_ratings(
        _finished_match(20, match_date), appearances, rosters)
    assert int(rated.loc[0, "home_goalie_id"]) == 9


def test_earlier_goalie_date_is_rejected() -> None:
    state = GoalieRatingState()
    later = datetime(2024, 10, 2, 1, 0)
    earlier = datetime(2024, 10, 1, 1, 0)
    state.snapshot(1, later)
    state.commit(1, later, 30, 27, 3600)
    with pytest.raises(ValueError, match="chronological"):
        state.snapshot(2, earlier)
    with pytest.raises(ValueError, match="chronological"):
        state.commit(2, earlier, 20, 18, 3600)


def test_goalie_config_rejects_non_positive_prior() -> None:
    with pytest.raises(ValueError, match="prior_shots"):
        build_goalie_ratings(
            pd.DataFrame([_appearance(
                1, 1, 1, datetime(2024, 10, 1), 10, 9, 3600)]),
            GoalieRatingsConfig(prior_shots=0))


def _roster(
        match_id: int,
        player_id: int,
        team_id: int,
        position: str,
        line: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "position": position,
        "line": line
    }


def _finished_match(match_id: int, game_date: datetime) -> pd.DataFrame:
    return pd.DataFrame([{
        "match_id": match_id,
        "season": 1,
        "home_team": 1,
        "away_team": 2,
        "game_date": game_date,
        "home_team_goals": 3,
        "away_team_goals": 2,
        "result": "1",
        "home_team_sog": 30,
        "away_team_sog": 28,
        "home_team_saves": 26,
        "away_team_saves": 27,
        "home_team_en": 0,
        "away_team_en": 0,
        "ot_winner": None,
        "so_winner": None
    }])


def _appearance(
        match_id: int,
        player_id: int,
        team_id: int,
        game_date: datetime,
        shots_against: int,
        shots_saved: int,
        toi_seconds: int | None) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "game_date": game_date,
        "shots_against": shots_against,
        "shots_saved": shots_saved,
        "toi_seconds": toi_seconds
    }
