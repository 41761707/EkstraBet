"""Tests for shrunk seasonal league and team context."""

from __future__ import annotations

from datetime import date
from math import exp

import pandas as pd
import pytest

from models.pipeline.core.config import FootballContextParams
from models.pipeline.features.football_context import ContextMatch
from models.pipeline.features.football_context import FootballContextState
from models.pipeline.features.football_context import build_context_state
from models.pipeline.features.football_context import context_match_from_row


AS_OF = pd.Timestamp("2026-06-01")
_ABS = 1e-9


def _match(
        match_id: int,
        league_id: int,
        season_id: int,
        game_date: str,
        home_goals: int,
        away_goals: int) -> ContextMatch:
    return ContextMatch(
        match_id=match_id,
        league_id=league_id,
        season_id=season_id,
        game_date=pd.Timestamp(game_date),
        home_team=10,
        away_team=20,
        home_goals=home_goals,
        away_goals=away_goals)


def _commit(state: FootballContextState, matches: list[ContextMatch]) -> None:
    for match in matches:
        state.commit(match)


def _teams(
        match_id: int,
        league_id: int,
        season_id: int,
        game_date: str,
        home_team: int,
        away_team: int,
        home_goals: int,
        away_goals: int) -> ContextMatch:
    return ContextMatch(
        match_id=match_id,
        league_id=league_id,
        season_id=season_id,
        game_date=pd.Timestamp(game_date),
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals)


def _newcomer(
        state: FootballContextState,
        team_id: int,
        league_id: int,
        season_id: int) -> float:
    features = state.team_features(
        team_id, "home", league_id, season_id, AS_OF)
    return features["home_ctx_is_newcomer"]


def test_context_match_from_row_reads_history_columns() -> None:
    frame = pd.DataFrame([{
        "id": 7,
        "league": 3,
        "season": 11,
        "game_date": "2026-03-01",
        "home_team": 10,
        "away_team": 20,
        "home_team_goals": 3,
        "away_team_goals": 0
    }])
    match = context_match_from_row(next(frame.itertuples(index=False)))
    assert match.match_id == 7
    assert match.league_id == 3
    assert match.season_id == 11
    assert match.game_date == pd.Timestamp("2026-03-01")
    assert match.home_team == 10
    assert match.away_team == 20
    assert match.home_goals == 3
    assert match.away_goals == 0


def test_league_features_match_hand_calculated_shrinkage() -> None:
    # Sezon 9: 1-0, 1-0, 2-2. Sezon 10: 3-0, 3-0.
    # Prior ligi (5 meczów): home 10/5, away 2/5, btts 1/5,
    # over 3/5, draw 1/5. k = 4, n_s = 2, sumy sezonu 6, 0, 0, 2, 0.
    # Mecz 10-10 innej ligi leży w oknie i nie może wejść do prioru.
    params = FootballContextParams(league_shrink_matches=4.0)
    state = FootballContextState(params)
    _commit(state, [
        _match(1, 1, 9, "2025-01-10", 1, 0),
        _match(2, 1, 9, "2025-01-17", 1, 0),
        _match(3, 1, 9, "2025-01-24", 2, 2),
        _match(4, 1, 10, "2026-03-01", 3, 0),
        _match(5, 1, 10, "2026-03-08", 3, 0),
        _match(6, 2, 1, "2026-02-01", 10, 10)
    ])
    features = state.league_features(1, 10, AS_OF)
    assert features["league_ctx_home_goals"] == pytest.approx(
        (6 + 4 * (10 / 5)) / 6, abs=_ABS)
    assert features["league_ctx_away_goals"] == pytest.approx(
        (0 + 4 * (2 / 5)) / 6, abs=_ABS)
    assert features["league_ctx_btts_pct"] == pytest.approx(
        (0 + 4 * (1 / 5)) / 6, abs=_ABS)
    assert features["league_ctx_over_25_pct"] == pytest.approx(
        (2 + 4 * (3 / 5)) / 6, abs=_ABS)
    assert features["league_ctx_draw_pct"] == pytest.approx(
        (0 + 4 * (1 / 5)) / 6, abs=_ABS)
    assert features["league_ctx_season_matches"] == pytest.approx(
        2.0, abs=_ABS)


def test_league_features_fall_back_to_the_global_window() -> None:
    # Liga 8 ma tylko mecz spoza okna. Prior bierze 5 meczów ligi 1.
    params = FootballContextParams(league_shrink_matches=4.0)
    state = FootballContextState(params)
    _commit(state, [
        _match(1, 1, 9, "2025-01-10", 1, 0),
        _match(2, 1, 9, "2025-01-17", 1, 0),
        _match(3, 1, 9, "2025-01-24", 2, 2),
        _match(4, 1, 10, "2026-03-01", 3, 0),
        _match(5, 1, 10, "2026-03-08", 3, 0),
        _match(6, 8, 4, "2020-01-01", 4, 2)
    ])
    features = state.league_features(8, 4, AS_OF)
    assert features["league_ctx_home_goals"] == pytest.approx(
        (4 + 4 * (10 / 5)) / 5, abs=_ABS)
    assert features["league_ctx_away_goals"] == pytest.approx(
        (2 + 4 * (2 / 5)) / 5, abs=_ABS)
    assert features["league_ctx_btts_pct"] == pytest.approx(
        (1 + 4 * (1 / 5)) / 5, abs=_ABS)
    assert features["league_ctx_over_25_pct"] == pytest.approx(
        (1 + 4 * (3 / 5)) / 5, abs=_ABS)
    assert features["league_ctx_draw_pct"] == pytest.approx(
        (0 + 4 * (1 / 5)) / 5, abs=_ABS)
    assert features["league_ctx_season_matches"] == pytest.approx(
        1.0, abs=_ABS)
    unseen = state.league_features(9, 1, AS_OF)
    assert unseen["league_ctx_home_goals"] == pytest.approx(10 / 5, abs=_ABS)
    assert unseen["league_ctx_away_goals"] == pytest.approx(2 / 5, abs=_ABS)
    assert unseen["league_ctx_btts_pct"] == pytest.approx(1 / 5, abs=_ABS)
    assert unseen["league_ctx_over_25_pct"] == pytest.approx(3 / 5, abs=_ABS)
    assert unseen["league_ctx_draw_pct"] == pytest.approx(1 / 5, abs=_ABS)
    assert unseen["league_ctx_season_matches"] == pytest.approx(0.0, abs=_ABS)


def test_league_features_fall_back_to_the_constant_prior() -> None:
    state = FootballContextState(FootballContextParams())
    empty = state.league_features(1, 1, AS_OF)
    assert empty["league_ctx_home_goals"] == pytest.approx(1.5, abs=_ABS)
    assert empty["league_ctx_away_goals"] == pytest.approx(1.2, abs=_ABS)
    assert empty["league_ctx_btts_pct"] == pytest.approx(0.52, abs=_ABS)
    assert empty["league_ctx_over_25_pct"] == pytest.approx(0.52, abs=_ABS)
    assert empty["league_ctx_draw_pct"] == pytest.approx(0.26, abs=_ABS)
    assert empty["league_ctx_season_matches"] == pytest.approx(0.0, abs=_ABS)
    state.commit(_match(1, 1, 5, "2020-01-01", 4, 2))
    shrunk = state.league_features(1, 5, AS_OF)
    assert shrunk["league_ctx_home_goals"] == pytest.approx(
        (4 + 60 * 1.5) / 61, abs=_ABS)
    assert shrunk["league_ctx_away_goals"] == pytest.approx(
        (2 + 60 * 1.2) / 61, abs=_ABS)
    assert shrunk["league_ctx_btts_pct"] == pytest.approx(
        (1 + 60 * 0.52) / 61, abs=_ABS)
    assert shrunk["league_ctx_over_25_pct"] == pytest.approx(
        (1 + 60 * 0.52) / 61, abs=_ABS)
    assert shrunk["league_ctx_draw_pct"] == pytest.approx(
        (0 + 60 * 0.26) / 61, abs=_ABS)
    assert shrunk["league_ctx_season_matches"] == pytest.approx(1.0, abs=_ABS)


def test_league_prior_window_is_730_days_and_excludes_as_of() -> None:
    # Dzień as_of - 730 wchodzi do prioru. Dzień wcześniejszy zostaje
    # w średniej sezonu, ale nie w priorze. Mecz z dnia as_of nie wchodzi.
    as_of = date(2026, 6, 1)
    start = pd.Timestamp(as_of) - pd.Timedelta(days=730)
    outside = start - pd.Timedelta(days=1)
    frame = pd.DataFrame([
        {
            "id": 1,
            "league": 1,
            "season": 20,
            "game_date": outside,
            "home_team": 10,
            "away_team": 20,
            "home_team_goals": 0,
            "away_team_goals": 5
        },
        {
            "id": 2,
            "league": 1,
            "season": 20,
            "game_date": start,
            "home_team": 10,
            "away_team": 20,
            "home_team_goals": 2,
            "away_team_goals": 1
        },
        {
            "id": 3,
            "league": 1,
            "season": 20,
            "game_date": pd.Timestamp(as_of),
            "home_team": 10,
            "away_team": 20,
            "home_team_goals": 9,
            "away_team_goals": 9
        },
        {
            "id": 4,
            "league": 1,
            "season": 20,
            "game_date": outside,
            "home_team": 10,
            "away_team": 20,
            "home_team_goals": None,
            "away_team_goals": None
        }
    ])
    state = build_context_state(frame, as_of, FootballContextParams())
    features = state.league_features(1, 20, pd.Timestamp(as_of))
    assert features["league_ctx_home_goals"] == pytest.approx(
        (2 + 60 * 2) / 62, abs=_ABS)
    assert features["league_ctx_away_goals"] == pytest.approx(
        (6 + 60 * 1) / 62, abs=_ABS)
    assert features["league_ctx_btts_pct"] == pytest.approx(
        (1 + 60 * 1) / 62, abs=_ABS)
    assert features["league_ctx_over_25_pct"] == pytest.approx(
        (2 + 60 * 1) / 62, abs=_ABS)
    assert features["league_ctx_draw_pct"] == pytest.approx(0.0, abs=_ABS)
    assert features["league_ctx_season_matches"] == pytest.approx(
        2.0, abs=_ABS)


def test_team_with_no_history_gets_the_league_prior() -> None:
    state = FootballContextState(FootballContextParams())
    features = state.team_features(1, "home", 1, 1, AS_OF)
    zero_prior = exp(-(1.5 + 1.2) / 2.0)
    assert features["home_ctx_clean_sheet_pct"] == pytest.approx(
        zero_prior, abs=_ABS)
    assert features["home_ctx_failed_to_score_pct"] == pytest.approx(
        zero_prior, abs=_ABS)
    assert features["home_ctx_draw_pct"] == pytest.approx(0.26, abs=_ABS)
    assert features["home_ctx_matches_played"] == pytest.approx(
        0.0, abs=_ABS)
    assert features["home_ctx_is_newcomer"] == pytest.approx(0.0, abs=_ABS)


def test_team_rates_shrink_toward_the_league() -> None:
    # Sezon 8: trzy razy 0:0 (6 stron bez gola, 3 remisy).
    # Sezon 10: 2:1 i 1:0 (1 strona bez gola, 0 remisów).
    # Prior z 5 meczów: zero 7/10, remis 3/5. k ligi = 4, k drużyny = 2.
    # 9:0 w innej lidze i mecz z dnia as_of nie wchodzą do sezonu 10.
    params = FootballContextParams(
        league_shrink_matches=4.0,
        team_shrink_matches=2.0)
    state = FootballContextState(params)
    _commit(state, [
        _teams(1, 1, 8, "2025-08-01", 1, 2, 0, 0),
        _teams(2, 1, 8, "2025-08-08", 1, 2, 0, 0),
        _teams(3, 1, 8, "2025-08-15", 1, 2, 0, 0),
        _teams(4, 1, 10, "2026-03-01", 1, 3, 2, 1),
        _teams(5, 1, 10, "2026-03-08", 1, 4, 1, 0),
        _teams(6, 2, 1, "2026-03-01", 1, 9, 9, 0),
        _teams(7, 1, 10, "2026-06-01", 1, 3, 5, 0)
    ])
    zero_ref = (0.5 + 4 * (7 / 10)) / 6
    draw_ref = (0 + 4 * (3 / 5)) / 6
    home = state.team_features(1, "home", 1, 10, AS_OF)
    assert set(home) == {
        "home_ctx_clean_sheet_pct",
        "home_ctx_failed_to_score_pct",
        "home_ctx_draw_pct",
        "home_ctx_matches_played",
        "home_ctx_is_newcomer",
        "home_ctx_rank_pct",
        "home_ctx_points_per_game",
        "home_ctx_matches_last_14d"
    }
    assert home["home_ctx_clean_sheet_pct"] == pytest.approx(
        (1 + 2 * zero_ref) / 4, abs=_ABS)
    assert home["home_ctx_failed_to_score_pct"] == pytest.approx(
        (0 + 2 * zero_ref) / 4, abs=_ABS)
    assert home["home_ctx_draw_pct"] == pytest.approx(
        (0 + 2 * draw_ref) / 4, abs=_ABS)
    assert home["home_ctx_matches_played"] == pytest.approx(2.0, abs=_ABS)
    assert home["home_ctx_is_newcomer"] == pytest.approx(0.0, abs=_ABS)
    away = state.team_features(1, "away", 1, 10, AS_OF)
    assert away["away_ctx_clean_sheet_pct"] == pytest.approx(
        home["home_ctx_clean_sheet_pct"], abs=_ABS)
    conceded = state.team_features(4, "away", 1, 10, AS_OF)
    assert conceded["away_ctx_clean_sheet_pct"] == pytest.approx(
        (0 + 2 * zero_ref) / 3, abs=_ABS)
    assert conceded["away_ctx_failed_to_score_pct"] == pytest.approx(
        (1 + 2 * zero_ref) / 3, abs=_ABS)
    assert conceded["away_ctx_draw_pct"] == pytest.approx(
        (0 + 2 * draw_ref) / 3, abs=_ABS)
    assert conceded["away_ctx_matches_played"] == pytest.approx(
        1.0, abs=_ABS)
    assert conceded["away_ctx_is_newcomer"] == pytest.approx(1.0, abs=_ABS)
    idle = state.team_features(9, "home", 1, 10, AS_OF)
    assert idle["home_ctx_matches_played"] == pytest.approx(0.0, abs=_ABS)
    assert idle["home_ctx_clean_sheet_pct"] == pytest.approx(
        zero_ref, abs=_ABS)
    assert idle["home_ctx_failed_to_score_pct"] == pytest.approx(
        zero_ref, abs=_ABS)
    assert idle["home_ctx_draw_pct"] == pytest.approx(draw_ref, abs=_ABS)
    assert idle["home_ctx_is_newcomer"] == pytest.approx(1.0, abs=_ABS)
    stayed = state.team_features(2, "home", 1, 10, AS_OF)
    assert stayed["home_ctx_matches_played"] == pytest.approx(
        0.0, abs=_ABS)
    assert stayed["home_ctx_clean_sheet_pct"] == pytest.approx(
        zero_ref, abs=_ABS)
    assert stayed["home_ctx_draw_pct"] == pytest.approx(draw_ref, abs=_ABS)
    assert stayed["home_ctx_is_newcomer"] == pytest.approx(0.0, abs=_ABS)


def test_newcomer_follows_the_previous_season_of_the_league() -> None:
    # Sezon 90 zaczyna się przed 50, mimo wyższego id.
    # Drużyna 6 grała w 90, opuściła 50 i nie jest w 70.
    state = FootballContextState(FootballContextParams())
    _commit(state, [
        _teams(1, 4, 90, "2025-05-01", 6, 7, 1, 0),
        _teams(2, 4, 50, "2026-02-01", 7, 8, 1, 0),
        _teams(3, 4, 70, "2026-04-01", 8, 9, 1, 0)
    ])
    assert _newcomer(state, 6, 4, 90) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 99, 4, 90) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 6, 4, 50) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 8, 4, 50) == pytest.approx(1.0, abs=_ABS)
    assert _newcomer(state, 6, 4, 70) == pytest.approx(1.0, abs=_ABS)
    assert _newcomer(state, 7, 4, 70) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 8, 4, 70) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 9, 4, 70) == pytest.approx(1.0, abs=_ABS)
    assert _newcomer(state, 8, 4, 80) == pytest.approx(0.0, abs=_ABS)
    assert _newcomer(state, 6, 4, 80) == pytest.approx(1.0, abs=_ABS)
    assert _newcomer(state, 6, 5, 1) == pytest.approx(0.0, abs=_ABS)


def test_team_features_reject_an_unknown_side() -> None:
    state = FootballContextState(FootballContextParams())
    with pytest.raises(ValueError, match="side"):
        state.team_features(1, "draw", 1, 1, AS_OF)


def _context_feature_names() -> set[str]:
    league = {
        "league_ctx_home_goals",
        "league_ctx_away_goals",
        "league_ctx_btts_pct",
        "league_ctx_over_25_pct",
        "league_ctx_draw_pct",
        "league_ctx_season_matches"
    }
    suffixes = (
        "clean_sheet_pct",
        "failed_to_score_pct",
        "draw_pct",
        "matches_played",
        "is_newcomer",
        "rank_pct",
        "points_per_game",
        "matches_last_14d"
    )
    names = set(league)
    for side in ("home", "away"):
        for suffix in suffixes:
            names.add(f"{side}_ctx_{suffix}")
    return names


def test_rank_pct_breaks_points_ties_by_difference_goals_and_id() -> None:
    # Sezon 10: 3:0 i 1:0. Oba zwycięstwa dają 3 pkt, bilans stawia
    # 10 przed 30 oraz 40 przed 20. Sezon 11 to same remisy: punkty
    # i bilans równe, więc decydują gole, a potem niższe id.
    # Porażka 10 w innej lidze i mecz z dnia as_of nie wchodzą.
    state = FootballContextState(FootballContextParams())
    _commit(state, [
        _teams(1, 1, 10, "2026-03-01", 10, 20, 3, 0),
        _teams(2, 1, 10, "2026-03-08", 30, 40, 1, 0),
        _teams(3, 1, 11, "2026-04-01", 10, 20, 2, 2),
        _teams(4, 1, 11, "2026-04-08", 30, 40, 0, 0),
        _teams(5, 2, 10, "2026-03-02", 10, 70, 0, 5),
        _teams(6, 1, 10, "2026-06-01", 20, 10, 5, 0)
    ])
    rank = "home_ctx_rank_pct"
    season_10 = {
        10: 0.0,
        30: 1 / 3,
        40: 2 / 3,
        20: 1.0
    }
    for team_id, expected in season_10.items():
        features = state.team_features(team_id, "home", 1, 10, AS_OF)
        assert features[rank] == pytest.approx(expected, abs=_ABS)
    leader = state.team_features(10, "home", 1, 10, AS_OF)
    assert leader["home_ctx_matches_played"] == pytest.approx(1.0, abs=_ABS)
    assert leader["home_ctx_points_per_game"] == pytest.approx(3.0, abs=_ABS)
    season_11 = {
        10: 0.0,
        20: 1 / 3,
        30: 2 / 3,
        40: 1.0
    }
    for team_id, expected in season_11.items():
        features = state.team_features(team_id, "home", 1, 11, AS_OF)
        assert features[rank] == pytest.approx(expected, abs=_ABS)
        assert features["home_ctx_points_per_game"] == pytest.approx(
            1.0, abs=_ABS)
    early = state.team_features(
        30, "home", 1, 10, pd.Timestamp("2026-03-05"))
    assert early[rank] == pytest.approx(0.5, abs=_ABS)
    assert early["home_ctx_points_per_game"] == pytest.approx(1.5, abs=_ABS)


def test_points_per_game_without_matches_uses_league_average() -> None:
    # Cztery mecze drużyn rozdają 6 punktów, więc średnia to 1.5.
    # Drużyna bez występu bierze 1.5. Pusta liga zostaje przy 1.35.
    state = FootballContextState(FootballContextParams())
    _commit(state, [
        _teams(1, 1, 10, "2026-03-01", 10, 20, 3, 0),
        _teams(2, 1, 10, "2026-03-08", 30, 40, 1, 0)
    ])
    played = state.team_features(10, "home", 1, 10, AS_OF)
    beaten = state.team_features(40, "away", 1, 10, AS_OF)
    idle = state.team_features(99, "home", 1, 10, AS_OF)
    empty = state.team_features(1, "home", 8, 1, AS_OF)
    assert played["home_ctx_points_per_game"] == pytest.approx(3.0, abs=_ABS)
    assert beaten["away_ctx_points_per_game"] == pytest.approx(0.0, abs=_ABS)
    assert idle["home_ctx_points_per_game"] == pytest.approx(1.5, abs=_ABS)
    assert idle["home_ctx_rank_pct"] == pytest.approx(0.5, abs=_ABS)
    assert empty["home_ctx_points_per_game"] == pytest.approx(
        1.35, abs=_ABS)
    assert empty["home_ctx_rank_pct"] == pytest.approx(0.5, abs=_ABS)
    assert empty["home_ctx_matches_last_14d"] == pytest.approx(
        0.0, abs=_ABS)


def test_fatigue_window_includes_the_opening_day_and_other_leagues() -> None:
    # Okno [as_of - dni, as_of). Dzień otwarcia wchodzi, dzień wcześniej
    # i dzień as_of nie. Mecz innej ligi w środku okna też się liczy.
    # Przy fatigue_days=1 zostaje tylko wczoraj: nazwa cechy bez zmian.
    as_of = pd.Timestamp("2026-06-01")
    start = as_of - pd.Timedelta(days=14)
    outside = (start - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    state = FootballContextState(FootballContextParams(fatigue_days=14))
    _commit(state, [
        _teams(1, 1, 10, outside, 10, 20, 1, 0),
        _teams(2, 1, 10, start.strftime("%Y-%m-%d"), 10, 30, 1, 0),
        _teams(3, 9, 3, "2026-05-25", 10, 40, 2, 2),
        _teams(4, 1, 10, "2026-06-01", 10, 20, 3, 0)
    ])
    home = state.team_features(10, "home", 1, 10, as_of)
    rested = state.team_features(20, "away", 1, 10, as_of)
    boundary = state.team_features(30, "away", 1, 10, as_of)
    assert home["home_ctx_matches_last_14d"] == pytest.approx(2.0, abs=_ABS)
    assert rested["away_ctx_matches_last_14d"] == pytest.approx(
        0.0, abs=_ABS)
    assert boundary["away_ctx_matches_last_14d"] == pytest.approx(
        1.0, abs=_ABS)
    narrow = FootballContextState(FootballContextParams(fatigue_days=1))
    _commit(narrow, [
        _teams(1, 1, 10, "2026-05-30", 10, 20, 1, 0),
        _teams(2, 1, 10, "2026-05-31", 10, 20, 1, 0),
        _teams(3, 1, 10, "2026-06-01", 10, 20, 1, 0)
    ])
    short = narrow.team_features(10, "home", 1, 10, as_of)
    assert short["home_ctx_matches_last_14d"] == pytest.approx(
        1.0, abs=_ABS)


def test_static_features_join_league_and_both_teams() -> None:
    state = FootballContextState(FootballContextParams())
    _commit(state, [
        _teams(1, 1, 10, "2026-03-01", 10, 20, 2, 0)
    ])
    features = state.static_features(10, 20, 1, 10, AS_OF)
    home = state.team_features(10, "home", 1, 10, AS_OF)
    away = state.team_features(20, "away", 1, 10, AS_OF)
    league = state.league_features(1, 10, AS_OF)
    assert set(features) == _context_feature_names()
    assert "abs_elo_diff" not in features
    assert features["home_ctx_rank_pct"] == pytest.approx(
        home["home_ctx_rank_pct"], abs=_ABS)
    assert features["away_ctx_points_per_game"] == pytest.approx(
        away["away_ctx_points_per_game"], abs=_ABS)
    assert features["league_ctx_home_goals"] == pytest.approx(
        league["league_ctx_home_goals"], abs=_ABS)
    assert features["home_ctx_matches_last_14d"] == pytest.approx(
        home["home_ctx_matches_last_14d"], abs=_ABS)
