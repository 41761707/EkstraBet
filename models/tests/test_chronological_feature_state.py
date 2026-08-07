"""Tests for in-memory ChronologicalFeatureState (season simulation)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from models.pipeline.features.chronological_state import BuiltMatchupFeatures
from models.pipeline.features.chronological_state import ChronologicalFeatureState
from models.pipeline.features.chronological_state import SimulatedMatchResult
from models.pipeline.features.chronological_state import build_season_start_state
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SimulationMode


def _config() -> SeasonSimulationConfig:
    return SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        days_per_round=7)


def _result(
        home: int,
        away: int,
        home_goals: int,
        away_goals: int) -> SimulatedMatchResult:
    return SimulatedMatchResult(
        home_team_id=home,
        away_team_id=away,
        home_goals=home_goals,
        away_goals=away_goals)


def _prior_history(
        rows: list[dict],
        start: date | None = None) -> pd.DataFrame:
    """Build finished-match rows from previous seasons for warm-start."""
    base = start or date(2025, 5, 1)
    frame_rows = []
    for index, row in enumerate(rows):
        frame_rows.append({
            "id": index + 1,
            "league": row.get("league", 1),
            "season": row.get("season", 12),
            "home_team": row["home"],
            "away_team": row["away"],
            "game_date": row.get(
                "game_date", base + timedelta(days=index)),
            "result": row.get("result", "1"),
            "home_team_goals": row["home_goals"],
            "away_team_goals": row["away_goals"],
            "home_team_xg": row.get("home_xg"),
            "away_team_xg": row.get("away_xg"),
            "home_team_sc": row.get("home_shots"),
            "away_team_sc": row.get("away_shots"),
            "home_team_sog": None,
            "away_team_sog": None,
            "home_team_bp": None,
            "away_team_bp": None
        })
    return pd.DataFrame(frame_rows)


def _warm_state(
        teams: list[int],
        *,
        window: int,
        history_rows: list[dict] | None = None,
        sequence_feature_columns: list[str] | None = None,
        static_feature_columns: list[str] | None = None,
        season_anchor: date | None = None) -> ChronologicalFeatureState:
    if history_rows is None:
        # domyślnie pełne okno z poprzedniego sezonu dla pierwszej pary
        history_rows = [
            {"home": teams[0], "away": teams[1], "home_goals": 2,
             "away_goals": 1}
            for _ in range(window)]
    return build_season_start_state(
        teams,
        _config(),
        window=window,
        sequence_feature_columns=sequence_feature_columns,
        static_feature_columns=static_feature_columns,
        prior_matches=_prior_history(history_rows),
        season_anchor=season_anchor or date(2026, 7, 1),
        load_history=False)


def test_warm_start_enables_features_on_season_day_zero() -> None:
    state = _warm_state(
        [10, 20],
        window=2,
        sequence_feature_columns=["goals_for", "won"],
        static_feature_columns=["elo_home", "h2h_home_wins", "league_avg_goals"])
    assert state.season_anchor == date(2026, 7, 1)
    features = state.build_matchup_features(10, 20, date(2026, 7, 1))
    assert features is not None
    assert features.home_sequence.shape == (2, 2)
    assert features.static_features[1] == 2.0
    assert features.static_features[0] > 1500.0


def test_without_history_returns_none_for_short_window() -> None:
    state = build_season_start_state(
        [10, 20, 30, 40],
        _config(),
        window=2,
        prior_matches=pd.DataFrame(),
        season_anchor=date(2026, 7, 1),
        load_history=False)
    assert state.build_matchup_features(10, 20, date(2026, 7, 1)) is None


def test_rest_days_equal_seven_between_simulated_rounds() -> None:
    state = _warm_state(
        [10, 20],
        window=1,
        static_feature_columns=[
            "home_rest_days", "away_rest_days", "rest_days_diff"],
        history_rows=[{
            "home": 10, "away": 20, "home_goals": 1, "away_goals": 0,
            "game_date": date(2026, 6, 24)}])
    first = state.build_matchup_features(10, 20, date(2026, 7, 1))
    assert first is not None
    assert first.static_features.tolist() == [7.0, 7.0, 0.0]
    state.commit_round([_result(10, 20, 1, 0)], date(2026, 7, 1))
    second = state.build_matchup_features(10, 20, date(2026, 7, 8))
    assert second is not None
    assert second.static_features.tolist() == [7.0, 7.0, 0.0]


def test_same_round_matches_do_not_leak_before_commit() -> None:
    state = _warm_state(
        [10, 20, 30, 40],
        window=1,
        sequence_feature_columns=["goals_for"],
        static_feature_columns=["elo_home", "elo_away", "h2h_home_wins"],
        history_rows=[
            {"home": 10, "away": 20, "home_goals": 1, "away_goals": 0},
            {"home": 30, "away": 40, "home_goals": 0, "away_goals": 0,
             "game_date": date(2025, 5, 2)}])
    round_date = date(2026, 7, 1)
    first = state.build_matchup_features(10, 30, round_date)
    second = state.build_matchup_features(20, 40, round_date)
    assert first is not None and second is not None
    elo_before = first.static_features[0]
    assert first.static_features[2] == 0.0
    assert second.static_features[2] == 0.0
    state.commit_round(
        [_result(10, 30, 5, 0), _result(20, 40, 0, 3)],
        round_date)
    after = state.build_matchup_features(10, 30, date(2026, 7, 8))
    assert after is not None
    assert after.static_features[0] > elo_before
    assert after.static_features[2] == 1.0


def test_next_round_sees_previous_round_results() -> None:
    state = _warm_state(
        [10, 20],
        window=1,
        sequence_feature_columns=["goals_for", "goals_against", "won"],
        static_feature_columns=[
            "league_avg_home_goals", "h2h_home_wins", "home_rest_days"])
    start = date(2026, 7, 1)
    state.commit_round([_result(10, 20, 3, 1)], start)
    later = state.build_matchup_features(10, 20, start + timedelta(days=7))
    assert later is not None
    assert later.home_sequence[-1].tolist() == [3.0, 1.0, 1.0]
    assert later.away_sequence[-1].tolist() == [1.0, 3.0, 0.0]
    assert later.static_features[1] >= 1.0
    assert later.static_features[2] == 7.0


def test_optional_stats_imputed_when_simulated_window_missing() -> None:
    state = _warm_state(
        [10, 20],
        window=2,
        sequence_feature_columns=["xg_for", "shots_for"],
        history_rows=[
            {"home": 10, "away": 20, "home_goals": 1, "away_goals": 0,
             "home_xg": 1.5, "home_shots": 10.0},
            {"home": 10, "away": 20, "home_goals": 2, "away_goals": 0,
             "home_xg": 2.0, "home_shots": 12.0,
             "game_date": date(2025, 5, 8)}])
    start = date(2026, 7, 1)
    # dwa symulowane mecze bez xG — okno może się złożyć z samym NaN
    state.commit_round([_result(10, 20, 1, 0)], start)
    state.commit_round(
        [_result(10, 20, 1, 0)], start + timedelta(days=7))
    built = state.build_matchup_features(
        10, 20, start + timedelta(days=14))
    assert built is not None
    assert np.isfinite(built.home_sequence).all()


def test_trial_copies_are_independent_after_warm_start() -> None:
    base = _warm_state(
        [10, 20],
        window=1,
        sequence_feature_columns=["goals_for"],
        static_feature_columns=["elo_home", "h2h_home_wins"])
    trial_a = base.copy()
    trial_b = base.copy()
    round_date = date(2026, 7, 1)
    trial_a.commit_round([_result(10, 20, 5, 0)], round_date)
    trial_b.commit_round([_result(10, 20, 0, 0)], round_date)
    next_date = round_date + timedelta(days=7)
    feats_a = trial_a.build_matchup_features(10, 20, next_date)
    feats_b = trial_b.build_matchup_features(10, 20, next_date)
    feats_base = base.build_matchup_features(10, 20, next_date)
    assert feats_a is not None and feats_b is not None
    assert feats_base is not None
    assert feats_a.static_features[0] > feats_b.static_features[0]
    assert feats_a.home_sequence[-1, 0] == 5.0
    assert feats_b.home_sequence[-1, 0] == 0.0
    assert feats_base.home_sequence[-1, 0] == 2.0


def test_seed_excludes_matches_on_or_after_anchor_via_caller() -> None:
    # caller podaje wyłącznie mecze sprzed kotwicy — jak fetch_finished_matches
    history = _prior_history([
        {"home": 10, "away": 20, "home_goals": 4, "away_goals": 0,
         "game_date": date(2026, 6, 30)},
        {"home": 10, "away": 20, "home_goals": 0, "away_goals": 5,
         "game_date": date(2026, 7, 1)}])
    # symulujemy filtr game_date < anchor po stronie loadera
    filtered = history.loc[
        pd.to_datetime(history["game_date"]) < pd.Timestamp(date(2026, 7, 1))]
    state = build_season_start_state(
        [10, 20],
        _config(),
        window=1,
        sequence_feature_columns=["goals_for"],
        static_feature_columns=["elo_home"],
        prior_matches=filtered,
        season_anchor=date(2026, 7, 1),
        load_history=False)
    built = state.build_matchup_features(10, 20, date(2026, 7, 1))
    assert built is not None
    assert built.home_sequence[-1, 0] == 4.0
    assert built.static_features[0] > 1500.0


def test_trial_methods_do_not_import_database_helpers() -> None:
    import inspect

    from models.pipeline.features import chronological_state as module

    build_src = inspect.getsource(ChronologicalFeatureState.build_matchup_features)
    commit_src = inspect.getsource(ChronologicalFeatureState.commit_round)
    assert "fetch_" not in build_src
    assert "fetch_" not in commit_src
    assert "get_db_connection" not in build_src
    assert "get_db_connection" not in commit_src
    assert isinstance(
        BuiltMatchupFeatures(
            home_sequence=np.zeros((1, 1), dtype=np.float32),
            away_sequence=np.zeros((1, 1), dtype=np.float32),
            static_features=np.zeros((1,), dtype=np.float32)),
        BuiltMatchupFeatures)


def test_build_season_start_state_rejects_empty_roster() -> None:
    with pytest.raises(ValueError, match="team_ids"):
        build_season_start_state(
            [], _config(), load_history=False, prior_matches=pd.DataFrame())


def test_anchor_from_season_years() -> None:
    from models.pipeline.data.match_history_repository import (
        _anchor_from_season_years)

    assert _anchor_from_season_years("2026/27") == date(2026, 7, 1)
    assert _anchor_from_season_years("2025/26") == date(2025, 7, 1)


def test_warm_start_uses_loader_when_requested(monkeypatch) -> None:
    calls: list[tuple[object, ...]] = []

    def fake_anchor(season_id: int, league_id: int | None = None) -> date:
        calls.append(("anchor", season_id, league_id))
        return date(2026, 7, 1)

    def fake_fetch(sport_id: int, date_to: date | datetime) -> pd.DataFrame:
        calls.append(("fetch", sport_id, date_to))
        return _prior_history([
            {"home": 10, "away": 20, "home_goals": 2, "away_goals": 1},
            {"home": 10, "away": 20, "home_goals": 1, "away_goals": 0,
             "game_date": date(2025, 5, 8)}])

    monkeypatch.setattr(
        "models.pipeline.data.match_history_repository.resolve_season_anchor_date",
        fake_anchor)
    monkeypatch.setattr(
        "models.pipeline.data.match_history_repository.fetch_finished_matches",
        fake_fetch)
    state = build_season_start_state(
        [10, 20],
        _config(),
        window=2,
        sequence_feature_columns=["goals_for"],
        load_history=True)
    assert ("anchor", 13, 1) in calls
    assert ("fetch", 1, date(2026, 7, 1)) in calls
    assert state.build_matchup_features(10, 20, date(2026, 7, 1)) is not None


def _parity_history(window: int = 3) -> pd.DataFrame:
    """Richer prior-season history: same-day batch, missing xG, multi-team."""
    start = date(2025, 3, 1)
    rows: list[dict] = []
    # naprzemienne pary + jeden dzień z dwoma meczami (batch jak trening)
    fixtures = [
        (10, 20, 2, 1, 1.4, 0.8),
        (30, 40, 0, 0, None, 0.5),
        (10, 30, 3, 1, 2.1, None),
        (20, 40, 1, 2, 0.9, 1.1),
        (10, 40, 1, 1, None, None),
        (20, 30, 4, 0, 2.5, 0.4)
    ]
    for index, (home, away, hg, ag, hxg, axg) in enumerate(fixtures):
        game_date = start + timedelta(days=index)
        if index == 1:
            # drugi mecz tej samej daty co pierwszy — leakage-safe batch
            game_date = start
        rows.append({
            "home": home,
            "away": away,
            "home_goals": hg,
            "away_goals": ag,
            "home_xg": hxg,
            "away_xg": axg,
            "game_date": game_date,
            "result": (
                "1" if hg > ag else "2" if hg < ag else "X")
        })
    # dociągamy okno dla 10 i 20
    while len(rows) < window + 4:
        index = len(rows)
        rows.append({
            "home": 10,
            "away": 20,
            "home_goals": 1 + index % 3,
            "away_goals": index % 2,
            "home_xg": 1.0,
            "away_xg": 0.7,
            "game_date": start + timedelta(days=10 + index),
            "result": "1"
        })
    return _prior_history(rows)


def _rating_row_from_snapshot(
        home_id: int,
        away_id: int,
        match_date: date,
        league_id: int,
        snap: dict[str, float]) -> pd.Series:
    values = {
        "home_team": home_id,
        "away_team": away_id,
        "league": league_id,
        "game_date": match_date,
        "home_elo": snap["home_elo"],
        "away_elo": snap["away_elo"],
        "home_gap_att": snap["home_gap_att"],
        "home_gap_def": snap["home_gap_def"],
        "away_gap_att": snap["away_gap_att"],
        "away_gap_def": snap["away_gap_def"]
    }
    for statistic in [
            "win_pct", "goals_for_avg", "goals_against_avg",
            "goals_for_std", "goals_against_std"]:
        values[f"home_czech_{statistic}"] = snap[f"home_czech_{statistic}"]
        values[f"away_czech_{statistic}"] = snap[f"away_czech_{statistic}"]
    return pd.Series(values)


def test_warm_start_matches_training_history_tensors() -> None:
    """Guard train/serve skew: same history → same sequence + static."""
    from models.pipeline.features import sequence_builder as sb
    from models.pipeline.features.matchup_features import STATIC_FEATURE_COLUMNS
    from models.pipeline.features.ratings import compute_ratings_timeline
    from models.pipeline.features.ratings.state import RatingState
    from models.pipeline.features.sequence_builder import DEFAULT_SEQUENCE_FEATURES

    window = 3
    league_tier = 2
    history = _parity_history(window)
    as_of = date(2026, 7, 1)
    timeline = compute_ratings_timeline(history)
    train_history = sb._TrainingHistory(window)
    for _, group in timeline.groupby("game_date", sort=False):
        for _, row in group.iterrows():
            train_history.commit(row)

    # niezależny replay ratingów — ten sam wzorzec co compute_ratings_timeline
    rating_replay = RatingState()
    for _, group in history.groupby("game_date", sort=False):
        for _, row in group.iterrows():
            rating_replay.snapshot(
                int(row["home_team"]), int(row["away_team"]))
        for _, row in group.iterrows():
            rating_replay.commit(
                int(row["home_team"]),
                int(row["away_team"]),
                int(row["home_team_goals"]),
                int(row["away_team_goals"]))

    sim_state = build_season_start_state(
        [10, 20, 30, 40],
        _config(),
        window=window,
        league_tier=league_tier,
        sequence_feature_columns=list(DEFAULT_SEQUENCE_FEATURES),
        static_feature_columns=list(STATIC_FEATURE_COLUMNS),
        prior_matches=history,
        season_anchor=as_of,
        load_history=False)

    built = sim_state.build_matchup_features(10, 20, as_of)
    assert built is not None
    train_home = train_history.sequence(10, list(DEFAULT_SEQUENCE_FEATURES))
    train_away = train_history.sequence(20, list(DEFAULT_SEQUENCE_FEATURES))
    assert train_home is not None and train_away is not None
    np.testing.assert_allclose(
        built.home_sequence, train_home, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(
        built.away_sequence, train_away, rtol=1e-5, atol=1e-5)

    independent_snap = rating_replay.snapshot(10, 20)
    sim_snap = sim_state.ratings.snapshot(10, 20)
    assert independent_snap == sim_snap
    train_static = sb._training_static(
        _rating_row_from_snapshot(10, 20, as_of, 1, independent_snap),
        train_history,
        league_tier,
        list(STATIC_FEATURE_COLUMNS))
    np.testing.assert_allclose(
        built.static_features, train_static, rtol=1e-5, atol=1e-5)
