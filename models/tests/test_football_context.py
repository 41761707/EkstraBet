"""Tests for shrunk seasonal league context."""

from __future__ import annotations

from datetime import date

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
