"""Tests for DynamicSeasonSimulator (both modes, small season)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Sequence
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import SequenceBatch
from models.pipeline.features.chronological_state import (
    build_season_start_state)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
from models.pipeline.prediction.future_events_predictor import (
    LoadedFutureModels)
from models.pipeline.simulation.config import ResolvedFixture
from models.pipeline.simulation.config import ScheduleRow
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.season_simulator import DynamicSeasonSimulator
from models.pipeline.simulation.season_simulator import TrialStandingState


def _goals_config(window: int = 1) -> FutureEventsRunConfig:
    return FutureEventsRunConfig(
        model_name="FOOTBALL_GOALS_POISSON_V1",
        task_type="goals_poisson",
        model_version="1.0.0",
        artifact_dir="models/artifacts/dev/football_goals_poisson_v1",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="FootballGoalsPoissonLabeler",
        trainer="PoissonTrainer",
        output_columns=["lambda_home", "lambda_away"],
        window_size=window,
        events={},
        sequence_feature_columns=["goals_for", "won"],
        static_feature_columns=["elo_home", "elo_away", "h2h_home_wins"])


def _mock_predictor(
        rates_fn=None) -> FutureEventsPredictor:
    model = MagicMock()

    def _predict(inputs, verbose=0):
        batch_size = inputs[0].shape[0]
        if rates_fn is not None:
            return rates_fn(inputs, batch_size)
        return np.full((batch_size, 2), [1.4, 1.1], dtype=float)

    model.predict.side_effect = _predict
    return FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(goals_model=model),
        feature_provider=lambda _m, _c: SequenceBatch(
            X_home=np.zeros((1, 1, 2)),
            X_away=np.zeros((1, 1, 2)),
            X_static=np.zeros((1, 3))))


def _schedule_row(
        row_id: int,
        home: int,
        away: int,
        round_number: int,
        match_id: int | None = None) -> ScheduleRow:
    return ScheduleRow(
        id=row_id,
        match_id=match_id,
        league_id=1,
        season_id=13,
        home_team_id=home,
        away_team_id=away,
        round=round_number)


def _two_team_input(
        mode: SimulationMode,
        *,
        fix_first: bool = False) -> SeasonSimulationInput:
    # double RR dla N=2 → dokładnie 2 mecze
    first = ResolvedFixture(
        schedule=_schedule_row(101, 10, 20, 1, match_id=501),
        result="1" if fix_first else None,
        home_goals=2 if fix_first else None,
        away_goals=0 if fix_first else None,
        is_fixed=fix_first)
    second = ResolvedFixture(
        schedule=_schedule_row(102, 20, 10, 2, match_id=None),
        is_fixed=False)
    return SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=mode,
        team_ids=[10, 20],
        fixtures=[first, second],
        input_fingerprint="test-fp")


def _warm_state(
        teams: list[int],
        window: int = 1,
        *,
        sequence_feature_columns: list[str] | None = None,
        static_feature_columns: list[str] | None = None):
    history_rows = []
    base = date(2026, 6, 1)
    row_id = 1
    # każdy klub dostaje co najmniej `window` meczów z poprzedniego sezonu
    for step in range(window):
        for pair_index in range(0, len(teams) - 1, 2):
            home = teams[pair_index]
            away = teams[pair_index + 1]
            history_rows.append({
                "id": row_id,
                "league": 1,
                "season": 12,
                "home_team": home,
                "away_team": away,
                "game_date": base + timedelta(days=row_id - 1),
                "result": "1",
                "home_team_goals": 1 + (row_id % 2),
                "away_team_goals": 0,
                "home_team_xg": None,
                "away_team_xg": None,
                "home_team_sc": None,
                "away_team_sc": None,
                "home_team_sog": None,
                "away_team_sog": None,
                "home_team_bp": None,
                "away_team_bp": None
            })
            row_id += 1
    seq_cols = sequence_feature_columns or ["goals_for", "won"]
    static_cols = static_feature_columns or [
        "elo_home", "elo_away", "h2h_home_wins"]
    config = SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        n_trials=100)
    return build_season_start_state(
        teams,
        config,
        window=window,
        sequence_feature_columns=seq_cols,
        static_feature_columns=static_cols,
        prior_matches=pd.DataFrame(history_rows),
        season_anchor=date(2026, 7, 1),
        load_history=False)


def _four_team_double_rr_input(
        mode: SimulationMode) -> SeasonSimulationInput:
    """Complete N=4 double RR with two fixtures in every round."""
    round_pairs = [
        [(10, 20), (30, 40)],
        [(10, 30), (20, 40)],
        [(10, 40), (20, 30)],
        [(20, 10), (40, 30)],
        [(30, 10), (40, 20)],
        [(40, 10), (30, 20)]
    ]
    fixtures: list[ResolvedFixture] = []
    schedule_id = 1
    for round_number, pairs in enumerate(round_pairs, start=1):
        for home, away in pairs:
            fixtures.append(ResolvedFixture(
                schedule=_schedule_row(
                    schedule_id, home, away, round_number),
                is_fixed=False))
            schedule_id += 1
    return SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=mode,
        team_ids=[10, 20, 30, 40],
        fixtures=fixtures,
        input_fingerprint="four-team-fp")


def _config(mode: SimulationMode, seed: int = 42) -> SeasonSimulationConfig:
    return SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=mode,
        n_trials=100,
        seed=seed,
        days_per_round=7)


def test_from_season_start_processes_each_fixture_once() -> None:
    simulator = DynamicSeasonSimulator(_mock_predictor())
    result = simulator.run(
        _config(SimulationMode.FROM_SEASON_START),
        simulation_input=_two_team_input(SimulationMode.FROM_SEASON_START),
        base_state=_warm_state([10, 20]))

    assert result.fixed_matches == 0
    assert result.simulated_matches == 2
    assert result.processed_schedule_ids == (101, 102)
    assert len(result.projections) == 2
    for row in result.projections:
        assert row.current_points == 0
        assert sum(row.position_probabilities) == pytest.approx(1.0)


def test_from_now_fixed_result_identical_in_all_trials() -> None:
    seen_static: list[np.ndarray] = []

    def rates_fn(inputs, batch_size):
        # round 2: tylko otwarte mecze — elo po stałym 2:0 powinno być
        # identyczne we wszystkich trialach
        seen_static.append(np.asarray(inputs[2], dtype=float).copy())
        return np.full((batch_size, 2), [1.2, 0.9], dtype=float)

    simulator = DynamicSeasonSimulator(_mock_predictor(rates_fn))
    result = simulator.run(
        _config(SimulationMode.FROM_NOW),
        simulation_input=_two_team_input(
            SimulationMode.FROM_NOW, fix_first=True),
        base_state=_warm_state([10, 20]))

    assert result.fixed_matches == 1
    assert result.simulated_matches == 1
    # po stałym 2:0 obie drużyny mają baseline 3 / 0 pkt
    by_id = {row.team_id: row for row in result.projections}
    assert by_id[10].current_points == 3
    assert by_id[20].current_points == 0
    assert by_id[10].current_position == 1
    # wszystkie triale dostały ten sam batch static po stałym wyniku
    assert len(seen_static) == 1
    static = seen_static[0]
    assert static.shape[0] == 100
    assert np.allclose(static, static[0])


def test_same_seed_is_deterministic() -> None:
    simulator = DynamicSeasonSimulator(_mock_predictor())
    kwargs = {
        "simulation_input": _two_team_input(SimulationMode.FROM_SEASON_START),
        "base_state": _warm_state([10, 20])}
    first = simulator.run(
        _config(SimulationMode.FROM_SEASON_START, seed=7), **kwargs)
    second = simulator.run(
        _config(SimulationMode.FROM_SEASON_START, seed=7),
        simulation_input=_two_team_input(SimulationMode.FROM_SEASON_START),
        base_state=_warm_state([10, 20]))
    third = simulator.run(
        _config(SimulationMode.FROM_SEASON_START, seed=8),
        simulation_input=_two_team_input(SimulationMode.FROM_SEASON_START),
        base_state=_warm_state([10, 20]))

    def _signature(result):
        return [
            (row.team_id, row.expected_points, row.expected_position,
             tuple(row.position_probabilities))
            for row in sorted(result.projections, key=lambda r: r.team_id)]

    assert _signature(first) == _signature(second)
    assert _signature(first) != _signature(third)


def test_later_round_features_depend_on_prior_round() -> None:
    captured: list[np.ndarray] = []
    call_index = {"n": 0}

    def rates_fn(inputs, batch_size):
        call_index["n"] += 1
        static = np.asarray(inputs[2], dtype=float)
        if call_index["n"] == 2:
            captured.append(static.copy())
        return np.full((batch_size, 2), [2.5, 0.5], dtype=float)

    simulator = DynamicSeasonSimulator(_mock_predictor(rates_fn))
    simulator.run(
        _config(SimulationMode.FROM_SEASON_START, seed=1),
        simulation_input=_two_team_input(SimulationMode.FROM_SEASON_START),
        base_state=_warm_state([10, 20]))

    assert len(captured) == 1
    # po losowej pierwszej kolejce triale rozjeżdżają się w cechach
    assert captured[0].shape[0] == 100
    assert not np.allclose(captured[0], captured[0][0])


def test_trial_standing_state_points_and_copy_isolation() -> None:
    state = TrialStandingState.empty([10, 20])
    clone = state.copy()
    state.apply_result(10, 20, 3, 1)
    assert state.points.tolist() == [3, 0]
    assert state.goal_difference.tolist() == [2, -2]
    assert clone.points.tolist() == [0, 0]


def test_incomplete_schedule_raises_before_inference() -> None:
    predictor = _mock_predictor()
    simulator = DynamicSeasonSimulator(predictor)
    bad_input = SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        team_ids=[10, 20],
        fixtures=[
            ResolvedFixture(
                schedule=_schedule_row(1, 10, 20, 1),
                is_fixed=False)],
        input_fingerprint="bad")

    with pytest.raises(ValueError, match="incomplete schedule"):
        simulator.run(
            _config(SimulationMode.FROM_SEASON_START),
            simulation_input=bad_input,
            base_state=_warm_state([10, 20]))
    predictor.models.goals_model.predict.assert_not_called()


def test_missing_sequence_history_fails_clearly() -> None:
    config = SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        n_trials=100)
    empty_state = build_season_start_state(
        [10, 20],
        config,
        window=2,
        sequence_feature_columns=["goals_for"],
        static_feature_columns=["elo_home"],
        prior_matches=pd.DataFrame(),
        season_anchor=date(2026, 7, 1),
        load_history=False)
    simulator = DynamicSeasonSimulator(_mock_predictor())

    with pytest.raises(ValueError, match="insufficient sequence history"):
        simulator.run(
            _config(SimulationMode.FROM_SEASON_START),
            simulation_input=_two_team_input(
                SimulationMode.FROM_SEASON_START),
            base_state=empty_state)


def test_same_round_fixtures_have_no_feature_leakage() -> None:
    """Two parallel round-1 matches must share pre-commit league state."""
    static_cols = ["elo_home", "league_avg_goals"]
    seq_cols = ["goals_for", "won"]
    teams = [10, 20, 30, 40]
    base_state = _warm_state(
        teams,
        window=1,
        sequence_feature_columns=seq_cols,
        static_feature_columns=static_cols)
    round_date = date(2026, 7, 1)
    expected_a = base_state.build_matchup_features(10, 20, round_date)
    expected_b = base_state.build_matchup_features(30, 40, round_date)
    assert expected_a is not None and expected_b is not None
    expected_league = float(expected_a.static_features[1])
    assert expected_league == float(expected_b.static_features[1])

    captured: list[np.ndarray] = []
    call_index = {"n": 0}

    def rates_fn(inputs, verbose=0):
        batch_size = inputs[0].shape[0]
        call_index["n"] += 1
        if call_index["n"] == 1:
            captured.append(np.asarray(inputs[2], dtype=float).copy())
        return np.full((batch_size, 2), [3.0, 3.0], dtype=float)

    goals = _goals_config()
    goals = goals.model_copy(update={
        "sequence_feature_columns": seq_cols,
        "static_feature_columns": static_cols
    })
    model = MagicMock()
    model.predict.side_effect = rates_fn
    predictor = FutureEventsPredictor(
        goals_config=goals,
        models=LoadedFutureModels(goals_model=model),
        feature_provider=lambda _m, _c: SequenceBatch(
            X_home=np.zeros((1, 1, 2)),
            X_away=np.zeros((1, 1, 2)),
            X_static=np.zeros((1, 2))))
    simulator = DynamicSeasonSimulator(predictor)
    result = simulator.run(
        _config(SimulationMode.FROM_SEASON_START, seed=11),
        simulation_input=_four_team_double_rr_input(
            SimulationMode.FROM_SEASON_START),
        base_state=base_state)

    assert result.processed_schedule_ids[:2] == (1, 2)
    assert len(captured) == 1
    static = captured[0]
    # round 1: 2 fixtures × 100 trials, kolejność (trial, fixture)
    assert static.shape == (200, 2)
    league_col = static[:, 1]
    assert np.allclose(league_col, expected_league)
    # w obrębie trialu oba mecze kolejki widzą ten sam agregat ligi
    for trial_index in range(100):
        first = league_col[trial_index * 2]
        second = league_col[trial_index * 2 + 1]
        assert first == pytest.approx(second)
        assert first == pytest.approx(expected_league)


def test_round_progress_wraps_each_round_once() -> None:
    seen: list[int] = []

    def progress(rounds: Sequence[int]):
        for round_number in rounds:
            seen.append(round_number)
            yield round_number

    simulator = DynamicSeasonSimulator(_mock_predictor())
    simulator.run(
        _config(SimulationMode.FROM_SEASON_START),
        simulation_input=_four_team_double_rr_input(
            SimulationMode.FROM_SEASON_START),
        base_state=_warm_state([10, 20, 30, 40]),
        round_progress=progress)
    assert seen == [1, 2, 3, 4, 5, 6]
