"""Pre-match hockey team ratings, early season and season regression."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd
import pytest

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.early_season import early_season_alpha
from models.pipeline.features.hockey.early_season import (
    early_season_multiplier)
from models.pipeline.features.hockey.ratings import HOCKEY_ELO_INITIAL
from models.pipeline.features.hockey.ratings import HOCKEY_SOG_GAP_INITIAL
from models.pipeline.features.hockey.ratings import HOCKEY_TEAM_RATING_COLUMNS
from models.pipeline.features.hockey.ratings import HockeyRatingsConfig
from models.pipeline.features.hockey.ratings import HockeyTeamRatingState
from models.pipeline.features.hockey.ratings import (
    build_hockey_pre_match_ratings)
from models.pipeline.features.hockey.ratings import build_hockey_team_ratings
from models.pipeline.features.ratings.elo import expected_home_score
from models.pipeline.features.ratings.elo import goal_difference_multiplier
from models.pipeline.features.ratings.elo import update_elo
from models.pipeline.features.ratings.gap import GapRating
from models.pipeline.features.ratings.gap import update_gap


def test_early_season_multiplier_ramps_then_returns_to_baseline() -> None:
    config = EarlySeasonConfig()
    assert early_season_multiplier(0, config) == 2.5
    assert early_season_multiplier(4, config) == 1.75
    assert early_season_multiplier(8, config) == 1.0
    assert early_season_multiplier(20, config) == 1.0


def test_early_season_alpha_is_capped() -> None:
    config = EarlySeasonConfig()
    assert early_season_alpha(0.1, 0, config) == pytest.approx(0.25)
    assert early_season_alpha(0.3, 0, config) == 0.5


def test_early_season_multiplier_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        early_season_multiplier(-1)
    with pytest.raises(ValueError, match="positive"):
        early_season_multiplier(0, EarlySeasonConfig(games=0))


def test_current_match_does_not_leak_into_its_own_rating() -> None:
    rated = build_hockey_team_ratings(_losses(1))
    assert rated.loc[0, "home_elo"] == HOCKEY_ELO_INITIAL
    assert rated.loc[0, "away_elo"] == HOCKEY_ELO_INITIAL
    assert rated.loc[0, "home_season_games"] == 0
    assert rated.loc[0, "home_early_multiplier"] == 2.5


def test_same_slate_shares_pre_match_ratings() -> None:
    start = datetime(2024, 10, 1, 1, 0)
    rows = [
        _row(1, 1, 2, start, 1, 4, "2"),
        _row(2, 1, 3, start, 5, 1, "1"),
        _row(3, 1, 2, start + timedelta(days=2), 1, 4, "2")]
    rated = build_hockey_team_ratings(pd.DataFrame(rows))
    assert rated.loc[0, "home_elo"] == rated.loc[1, "home_elo"]
    assert rated.loc[2, "home_elo"] != rated.loc[0, "home_elo"]


def test_losing_streak_drops_faster_than_constant_k() -> None:
    matches = _losses(10)
    boosted = build_hockey_team_ratings(matches)
    flat = build_hockey_team_ratings(
        matches,
        HockeyRatingsConfig(
            early_season=EarlySeasonConfig(boost=1.0)))
    # Po 8 porażkach rating jest już niższy, a 9. mecz ma bazowe K.
    assert boosted.loc[8, "home_elo"] < flat.loc[8, "home_elo"]
    assert boosted.loc[8, "home_gap_att"] < flat.loc[8, "home_gap_att"]
    assert boosted.loc[8, "home_season_games"] == 8
    assert boosted.loc[8, "home_early_multiplier"] == 1.0
    config = HockeyRatingsConfig()
    expected_home, expected_away = update_elo(
        float(boosted.loc[8, "home_elo"]),
        float(boosted.loc[8, "away_elo"]),
        1,
        4,
        config.elo)
    assert boosted.loc[9, "home_elo"] == pytest.approx(expected_home)
    assert boosted.loc[9, "away_elo"] == pytest.approx(expected_away)


def test_season_change_regresses_elo_toward_the_mean() -> None:
    continued = build_hockey_team_ratings(_wins(6, season=1))
    reset = build_hockey_team_ratings(_wins_then_new_season(5))
    raw = float(continued.loc[5, "home_elo"])
    regressed = float(reset.loc[5, "home_elo"])
    assert regressed == pytest.approx(0.7 * raw + 0.3 * HOCKEY_ELO_INITIAL)
    assert abs(regressed - HOCKEY_ELO_INITIAL) < abs(raw - HOCKEY_ELO_INITIAL)
    assert reset.loc[5, "home_season_games"] == 0
    assert reset.loc[5, "home_early_multiplier"] == 2.5


def test_earlier_game_date_is_rejected() -> None:
    state = HockeyTeamRatingState()
    later = datetime(2024, 10, 2, 1, 0)
    state.snapshot(1, 2, 8, later)
    state.snapshot(3, 4, 8, later)
    with pytest.raises(ValueError, match="chronological"):
        state.snapshot(1, 2, 7, datetime(2024, 10, 1, 1, 0))


def test_lower_season_id_still_starts_a_new_season() -> None:
    opening = datetime(2016, 10, 1, 1, 0)
    nxt = datetime(2017, 10, 1, 1, 0)
    first = _row(1, 1, 2, opening, 5, 1, "1", season=8)
    changed = build_hockey_team_ratings(pd.DataFrame([
        first,
        _row(2, 1, 2, nxt, 5, 1, "1", season=7)]))
    continued = build_hockey_team_ratings(pd.DataFrame([
        first,
        _row(2, 1, 2, nxt, 5, 1, "1", season=8)]))
    raw = float(continued.loc[1, "home_elo"])
    regressed = float(changed.loc[1, "home_elo"])
    assert changed.loc[1, "home_season_games"] == 0
    assert changed.loc[1, "home_early_multiplier"] == 2.5
    assert regressed == pytest.approx(
        0.7 * raw + 0.3 * HOCKEY_ELO_INITIAL)


def test_each_team_uses_its_own_early_season_k() -> None:
    config = HockeyRatingsConfig()
    state = HockeyTeamRatingState(config)
    start = datetime(2024, 10, 1, 1, 0)
    for index in range(8):
        state.snapshot(2, 3, 1, start + timedelta(days=index))
        state.commit(2, 3, 3, 2)
    before = state.snapshot(1, 2, 1, start + timedelta(days=20))
    state.commit(1, 2, 4, 1)
    after = state.snapshot(1, 2, 1, start + timedelta(days=21))
    expected = expected_home_score(
        before["home_elo"],
        before["away_elo"],
        config.elo.home_advantage)
    margin = goal_difference_multiplier(4 - 1)
    surprise = 1.0 - expected
    home_k = config.elo.k_factor * 2.5
    away_k = config.elo.k_factor
    assert before["home_season_games"] == 0
    assert before["away_season_games"] == 8
    assert after["home_elo"] == pytest.approx(
        before["home_elo"] + home_k * margin * surprise)
    assert after["away_elo"] == pytest.approx(
        before["away_elo"] - away_k * margin * surprise)


def test_elo_uses_final_margin_and_gap_uses_regulation() -> None:
    config = HockeyRatingsConfig(
        early_season=EarlySeasonConfig(boost=1.0))
    state = HockeyTeamRatingState(config)
    opening = datetime(2024, 10, 1, 1, 0)
    before = state.snapshot(1, 2, 1, opening)
    state.commit(
        1, 2, 2, 2,
        home_sog=30, away_sog=30,
        home_saves=28, away_saves=28,
        ot_winner=1)
    after = state.snapshot(1, 2, 1, opening + timedelta(days=1))
    elo_home, elo_away = update_elo(
        before["home_elo"], before["away_elo"], 3, 2, config.elo)
    assert after["home_elo"] == pytest.approx(elo_home)
    assert after["away_elo"] == pytest.approx(elo_away)
    gap_home, _gap_away = update_gap(
        GapRating(before["home_gap_att"], before["home_gap_def"]),
        GapRating(before["away_gap_att"], before["away_gap_def"]),
        2, 2, config.goal_gap)
    overtime_home, _overtime_away = update_gap(
        GapRating(before["home_gap_att"], before["home_gap_def"]),
        GapRating(before["away_gap_att"], before["away_gap_def"]),
        3, 2, config.goal_gap)
    assert after["home_gap_att"] == pytest.approx(gap_home.attack)
    assert abs(after["home_gap_att"] - overtime_home.attack) > 1e-6


def test_shootout_loss_is_a_one_goal_elo_result() -> None:
    config = HockeyRatingsConfig(
        early_season=EarlySeasonConfig(boost=1.0))
    state = HockeyTeamRatingState(config)
    opening = datetime(2024, 10, 1, 1, 0)
    before = state.snapshot(1, 2, 1, opening)
    state.commit(1, 2, 2, 2, ot_winner=3, so_winner=2)
    after = state.snapshot(1, 2, 1, opening + timedelta(days=1))
    elo_home, _elo_away = update_elo(
        before["home_elo"], before["away_elo"], 2, 3, config.elo)
    assert after["home_elo"] == pytest.approx(elo_home)


def test_pdo_uses_early_season_alpha() -> None:
    config = HockeyRatingsConfig()
    state = HockeyTeamRatingState(config)
    opening = datetime(2024, 10, 1, 1, 0)
    state.snapshot(1, 2, 1, opening)
    state.commit(
        1, 2, 5, 1,
        home_sog=40, away_sog=20,
        home_saves=18, away_saves=35)
    after = state.snapshot(1, 2, 1, opening + timedelta(days=1))
    alpha = early_season_alpha(config.pdo_alpha, 0, config.early_season)
    observed = (5 / 40 + 18 / 20) * 100.0
    expected = alpha * observed + (1.0 - alpha) * 100.0
    assert after["home_pdo"] == pytest.approx(expected)
    assert after["home_sog_gap_att"] > HOCKEY_SOG_GAP_INITIAL
    assert alpha == pytest.approx(0.25)


def test_pdo_excludes_empty_net_goals() -> None:
    config = HockeyRatingsConfig()
    state = HockeyTeamRatingState(config)
    opening = datetime(2024, 10, 1, 1, 0)
    state.snapshot(1, 2, 1, opening)
    state.commit(
        1, 2, 4, 2,
        home_sog=30, away_sog=25,
        home_saves=18, away_saves=26,
        home_empty_net=1, away_empty_net=1)
    after = state.snapshot(1, 2, 1, opening + timedelta(days=1))
    alpha = early_season_alpha(config.pdo_alpha, 0, config.early_season)
    observed = ((4 - 1) / (30 - 1) + 18 / (25 - 1)) * 100.0
    raw = (4 / 30 + 18 / 25) * 100.0
    expected = alpha * observed + (1.0 - alpha) * 100.0
    assert after["home_pdo"] == pytest.approx(expected)
    assert abs(observed - raw) > 1e-6


def test_unplayed_match_is_excluded_and_columns_exist() -> None:
    played = _losses(1)
    postponed = dict(played.iloc[0])
    postponed["match_id"] = 99
    postponed["result"] = "0"
    postponed["game_date"] = datetime(2024, 10, 5, 1, 0)
    rated = build_hockey_team_ratings(
        pd.concat(
            [played, pd.DataFrame([postponed])],
            ignore_index=True))
    assert list(rated["match_id"]) == [1]
    for column in HOCKEY_TEAM_RATING_COLUMNS:
        assert column in rated.columns


def test_pre_match_frame_includes_both_goalies() -> None:
    matches = _losses(2)
    rated = build_hockey_pre_match_ratings(
        matches, _goalies(matches), _goalie_rosters(matches))
    assert len(rated) == 2
    assert rated["home_goalie_save_pct"].notna().all()
    assert rated["away_goalie_save_pct"].notna().all()
    assert int(rated.loc[0, "home_goalie_id"]) == 101
    assert int(rated.loc[0, "away_goalie_id"]) == 202
    assert rated.loc[0, "home_elo"] == HOCKEY_ELO_INITIAL
    assert "home_goalie_gsaa_per_60" in rated.columns


def _losses(count: int) -> pd.DataFrame:
    start = datetime(2024, 10, 1, 1, 0)
    rows = [
        _row(
            index + 1, 1, 2,
            start + timedelta(days=index * 2),
            1, 4, "2")
        for index in range(count)]
    return pd.DataFrame(rows)


def _wins(count: int, season: int) -> pd.DataFrame:
    start = datetime(2024, 10, 1, 1, 0)
    rows = [
        _row(
            index + 1, 1, 2,
            start + timedelta(days=index * 2),
            5, 1, "1", season=season)
        for index in range(count)]
    return pd.DataFrame(rows)


def _wins_then_new_season(season_one_games: int) -> pd.DataFrame:
    first = _wins(season_one_games, season=1)
    opener = _row(
        100, 1, 2,
        datetime(2025, 10, 1, 1, 0),
        5, 1, "1", season=2)
    return pd.concat(
        [first, pd.DataFrame([opener])], ignore_index=True)


def _row(
        match_id: int,
        home_team: int,
        away_team: int,
        game_date: datetime,
        home_goals: int,
        away_goals: int,
        result: str,
        season: int = 1) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
        "game_date": game_date,
        "home_team_goals": home_goals,
        "away_team_goals": away_goals,
        "result": result,
        "home_team_sog": 28,
        "away_team_sog": 30,
        "home_team_saves": 26,
        "away_team_saves": 25,
        "home_team_en": 0,
        "away_team_en": 0,
        "ot_winner": None,
        "so_winner": None
    }


def _goalies(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, match in matches.iterrows():
        rows.append(_goalie_row(
            int(match["match_id"]), 101, int(match["home_team"]),
            match["game_date"], 30, 27))
        rows.append(_goalie_row(
            int(match["match_id"]), 202, int(match["away_team"]),
            match["game_date"], 28, 25))
    return pd.DataFrame(rows)


def _goalie_rosters(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, match in matches.iterrows():
        rows.append({
            "match_id": int(match["match_id"]),
            "player_id": 101,
            "team_id": int(match["home_team"]),
            "position": "G",
            "line": 1
        })
        rows.append({
            "match_id": int(match["match_id"]),
            "player_id": 202,
            "team_id": int(match["away_team"]),
            "position": "G",
            "line": 1
        })
    return pd.DataFrame(rows)


def _goalie_row(
        match_id: int,
        player_id: int,
        team_id: int,
        game_date: datetime,
        shots_against: int,
        shots_saved: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "game_date": game_date,
        "shots_against": shots_against,
        "shots_saved": shots_saved,
        "toi_seconds": 3600
    }
