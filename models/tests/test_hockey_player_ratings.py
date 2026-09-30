"""As-of skater ratings, slot shrinkage and early-season alpha."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd
import pytest

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.player_ratings import (
    HockeyPlayerRatingState)
from models.pipeline.features.hockey.player_ratings import PlayerRatingsConfig
from models.pipeline.features.hockey.player_ratings import (
    build_player_ratings)


def test_line_one_forward_is_rated_before_the_match() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rated = build_player_ratings(pd.DataFrame([
        _skater(1, 10, "C", 1, start, points=2, toi_seconds=1200)]))
    assert rated.loc[0, "slot"] == "F1"
    assert rated.loc[0, "season_games_played"] == 0
    assert rated.loc[0, "off_rating"] == pytest.approx(2.6)


def test_new_player_takes_the_slot_average() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    nxt = start + timedelta(days=1)
    rated = build_player_ratings(pd.DataFrame([
        _skater(1, 10, "C", 1, start, points=2, sog=4, toi_seconds=1200),
        _skater(1, 11, "C", 4, start, points=0, toi_seconds=1200),
        _skater(2, 12, "LW", 1, nxt, points=9, toi_seconds=1200),
        _skater(2, 13, "RW", 4, nxt, points=9, toi_seconds=1200)]))
    debuts = rated.loc[rated["match_id"] == 2].set_index("slot")
    assert debuts.loc["F1", "off_rating"] == pytest.approx(6.0)
    assert debuts.loc["F1", "shot_rating"] == pytest.approx(12.0)
    assert debuts.loc["F4", "off_rating"] == pytest.approx(0.0)
    assert debuts.loc["F1", "season_games_played"] == 0


def test_def_rating_removes_the_team_result() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    nxt = start + timedelta(days=1)
    rated = build_player_ratings(
        pd.DataFrame([
            _skater(
                1, 10, "C", 1, start, plus_minus=2, toi_seconds=1200),
            _skater(
                1, 11, "C", 4, start, plus_minus=2, toi_seconds=1200),
            _skater(2, 12, "LW", 1, nxt, toi_seconds=1200)]),
        PlayerRatingsConfig(initial_def=1.0))
    debut = rated.loc[rated["player_id"] == 12].iloc[0]
    assert debut["def_rating"] == pytest.approx(0.0)


def test_current_match_does_not_leak_into_its_rating() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rated = build_player_ratings(
        pd.DataFrame([
            _skater(1, 10, "C", 1, start, points=2, toi_seconds=1200),
            _skater(
                2, 10, "C", 1, start + timedelta(days=1),
                points=0, toi_seconds=1200)]),
        _off_config(2.0, EarlySeasonConfig(boost=1.0)))
    assert rated.loc[0, "off_rating"] == pytest.approx(2.0)
    assert rated.loc[0, "season_games_played"] == 0
    assert rated.loc[1, "off_rating"] == pytest.approx(6.0)
    assert rated.loc[1, "season_games_played"] == 1


def test_same_slate_does_not_share_player_results() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rated = build_player_ratings(
        pd.DataFrame([
            _skater(1, 10, "C", 1, start, points=2, toi_seconds=1200),
            _skater(
                2, 20, "C", 1, start, points=0, toi_seconds=1200,
                team_id=8)]),
        _off_config(2.0))
    assert list(rated["off_rating"]) == pytest.approx([2.0, 2.0])


def test_early_season_boost_reacts_faster_than_flat_alpha() -> None:
    matches = _spike_then_follow_up()
    boosted = build_player_ratings(
        matches, _off_config(2.0, EarlySeasonConfig()))
    flat = build_player_ratings(
        matches, _off_config(2.0, EarlySeasonConfig(boost=1.0)))
    assert boosted.loc[2, "season_games_played"] == 2
    assert boosted.loc[2, "off_rating"] == pytest.approx(85.85 / 22.0)
    assert flat.loc[2, "off_rating"] == pytest.approx(84.8 / 22.0)
    assert boosted.loc[2, "off_rating"] > flat.loc[2, "off_rating"]


def test_new_season_resets_the_counter_and_keeps_memory() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rated = build_player_ratings(
        pd.DataFrame([
            _skater(1, 10, "C", 1, start, points=2, toi_seconds=1200),
            _skater(
                2, 10, "C", 1, start + timedelta(days=40),
                points=2, toi_seconds=1200, season=2)]),
        _off_config(2.0, EarlySeasonConfig(boost=1.0)))
    assert rated.loc[1, "season_games_played"] == 0
    assert rated.loc[1, "off_rating"] == pytest.approx(6.0)
    assert rated.loc[1, "off_rating"] != pytest.approx(2.0)


def test_goalie_is_slotted_but_not_rated_as_a_skater() -> None:
    start = datetime(2025, 10, 1, 1, 0)
    rated = build_player_ratings(pd.DataFrame([
        _skater(1, 10, "G", 1, start, toi_seconds=3600),
        _skater(1, 11, "D", 1, start, toi_seconds=1200)]))
    assert list(rated["player_id"]) == [11]
    assert rated.loc[0, "slot"] == "D1"


def test_earlier_player_rating_date_is_rejected() -> None:
    state = HockeyPlayerRatingState()
    later = datetime(2025, 10, 2, 1, 0)
    state.snapshot(10, "F1", 1, later)
    with pytest.raises(ValueError, match="chronological"):
        state.snapshot(10, "F1", 1, later - timedelta(days=1))


def _spike_then_follow_up() -> pd.DataFrame:
    start = datetime(2025, 10, 1, 1, 0)
    return pd.DataFrame([
        _skater(1, 10, "C", 1, start, points=2, toi_seconds=3600),
        _skater(
            2, 10, "C", 1, start + timedelta(days=1),
            points=6, toi_seconds=3600),
        _skater(
            3, 10, "C", 1, start + timedelta(days=2),
            points=2, toi_seconds=3600)])


def _off_config(
        f1_off: float,
        early_season: EarlySeasonConfig | None = None) -> PlayerRatingsConfig:
    return PlayerRatingsConfig(
        initial_off={"F1": f1_off},
        early_season=early_season or EarlySeasonConfig())


def _skater(
        match_id: int,
        player_id: int,
        position: str,
        line: int,
        game_date: datetime,
        points: float = 0.0,
        sog: float = 0.0,
        plus_minus: float = 0.0,
        toi_seconds: int = 1200,
        season: int = 1,
        team_id: int = 7) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "position": position,
        "line": line,
        "toi_seconds": toi_seconds,
        "game_date": game_date,
        "season": season,
        "points": points,
        "sog": sog,
        "plus_minus": plus_minus
    }
