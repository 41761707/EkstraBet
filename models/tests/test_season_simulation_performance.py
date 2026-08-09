"""Opt-in performance harness for DynamicSeasonSimulator.

Skipped unless ``EKSTRABET_SEASON_PERF=1``. Uses a mock goals model so the
loop cost (features + sampling + aggregation) is measurable without
TensorFlow. Reference production budget lives in ``perf_budget``.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
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
from models.pipeline.simulation.perf_budget import DEFAULT_PERF_TRIALS
from models.pipeline.simulation.perf_budget import MOCK_PERF_PEAK_RSS_MB_LIMIT
from models.pipeline.simulation.perf_budget import MOCK_PERF_WALL_SECONDS_LIMIT
from models.pipeline.simulation.perf_budget import REFERENCE_FIXTURE_COUNT
from models.pipeline.simulation.perf_budget import REFERENCE_TEAM_COUNT
from models.pipeline.simulation.perf_budget import WallClock
from models.pipeline.simulation.perf_budget import peak_rss_mb
from models.pipeline.simulation.perf_budget import perf_enabled
from models.pipeline.simulation.perf_budget import resolve_perf_trials
from models.pipeline.simulation.season_simulator import DynamicSeasonSimulator


pytestmark = pytest.mark.skipif(
    not perf_enabled(),
    reason=(
        "set EKSTRABET_SEASON_PERF=1 to run the season "
        "simulation performance harness"))

# mniejsza liga pod porównanie trybów (szybsze niż pełne N=18)
MODE_COMPARE_TEAM_COUNT = 8
MODE_COMPARE_FIXED_ROUNDS = 4


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


def _counting_predictor() -> tuple[FutureEventsPredictor, dict[str, int]]:
    """Return a mock predictor and a counter of inferred score rows."""
    model = MagicMock()
    stats = {"inferred_rows": 0}

    def _predict(inputs, verbose=0):
        batch_size = inputs[0].shape[0]
        stats["inferred_rows"] += int(batch_size)
        return np.full((batch_size, 2), [1.4, 1.1], dtype=float)

    model.predict.side_effect = _predict
    predictor = FutureEventsPredictor(
        goals_config=_goals_config(),
        models=LoadedFutureModels(goals_model=model),
        feature_provider=lambda _m, _c: SequenceBatch(
            X_home=np.zeros((1, 1, 2)),
            X_away=np.zeros((1, 1, 2)),
            X_static=np.zeros((1, 3))))
    return predictor, stats


def _double_rr_rounds(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Build ordered home/away pairs grouped into complete rounds."""
    remaining = {
        (home, away)
        for home in team_ids
        for away in team_ids
        if home != away
    }
    rounds: list[list[tuple[int, int]]] = []
    half = len(team_ids) // 2
    while remaining:
        used: set[int] = set()
        round_pairs: list[tuple[int, int]] = []
        for home, away in list(remaining):
            if home in used or away in used:
                continue
            round_pairs.append((home, away))
            used.add(home)
            used.add(away)
            remaining.remove((home, away))
            if len(round_pairs) == half:
                break
        if not round_pairs:
            raise RuntimeError("unable to build complete double RR rounds")
        rounds.append(round_pairs)
    return rounds


def _full_league_input(
        team_count: int = REFERENCE_TEAM_COUNT,
        *,
        mode: SimulationMode = SimulationMode.FROM_SEASON_START,
        fingerprint: str = "perf-full-league"
) -> SeasonSimulationInput:
    teams = list(range(1, team_count + 1))
    fixtures: list[ResolvedFixture] = []
    schedule_id = 1
    for round_number, pairs in enumerate(_double_rr_rounds(teams), start=1):
        for home, away in pairs:
            fixtures.append(ResolvedFixture(
                schedule=ScheduleRow(
                    id=schedule_id,
                    match_id=None,
                    league_id=1,
                    season_id=13,
                    home_team_id=home,
                    away_team_id=away,
                    round=round_number),
                is_fixed=False))
            schedule_id += 1
    assert len(fixtures) == team_count * (team_count - 1)
    return SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=mode,
        team_ids=teams,
        fixtures=fixtures,
        input_fingerprint=fingerprint)


def _with_fixed_early_rounds(
        base: SeasonSimulationInput,
        fixed_rounds: int
) -> SeasonSimulationInput:
    """Mark early rounds as played (FROM_NOW semantics)."""
    fixtures: list[ResolvedFixture] = []
    match_id = 10_000
    for item in base.fixtures:
        if item.schedule.round <= fixed_rounds:
            schedule = ScheduleRow(
                id=item.schedule.id,
                match_id=match_id,
                league_id=item.schedule.league_id,
                season_id=item.schedule.season_id,
                home_team_id=item.schedule.home_team_id,
                away_team_id=item.schedule.away_team_id,
                round=item.schedule.round)
            fixtures.append(ResolvedFixture(
                schedule=schedule,
                result="1",
                home_goals=2,
                away_goals=1,
                is_fixed=True))
            match_id += 1
        else:
            fixtures.append(item)
    return SeasonSimulationInput(
        league_id=base.league_id,
        season_id=base.season_id,
        mode=SimulationMode.FROM_NOW,
        team_ids=list(base.team_ids),
        fixtures=fixtures,
        input_fingerprint="perf-from-now-fixed")


def _as_season_start(
        from_now_input: SeasonSimulationInput
) -> SeasonSimulationInput:
    """Drop fixed outcomes — mirrors FROM_SEASON_START loader behaviour."""
    fixtures = [
        ResolvedFixture(
            schedule=ScheduleRow(
                id=item.schedule.id,
                match_id=None,
                league_id=item.schedule.league_id,
                season_id=item.schedule.season_id,
                home_team_id=item.schedule.home_team_id,
                away_team_id=item.schedule.away_team_id,
                round=item.schedule.round),
            is_fixed=False)
        for item in from_now_input.fixtures
    ]
    return SeasonSimulationInput(
        league_id=from_now_input.league_id,
        season_id=from_now_input.season_id,
        mode=SimulationMode.FROM_SEASON_START,
        team_ids=list(from_now_input.team_ids),
        fixtures=fixtures,
        input_fingerprint="perf-from-season-start")


def _warm_state(teams: list[int], n_trials: int):
    history_rows = []
    base = date(2026, 6, 1)
    row_id = 1
    for pair_index in range(0, len(teams) - 1, 2):
        history_rows.append({
            "id": row_id,
            "league": 1,
            "season": 12,
            "home_team": teams[pair_index],
            "away_team": teams[pair_index + 1],
            "game_date": base + timedelta(days=row_id - 1),
            "result": "1",
            "home_team_goals": 2,
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
    config = SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        n_trials=n_trials)
    return build_season_start_state(
        teams,
        config,
        window=1,
        sequence_feature_columns=["goals_for", "won"],
        static_feature_columns=["elo_home", "elo_away", "h2h_home_wins"],
        prior_matches=pd.DataFrame(history_rows),
        season_anchor=date(2026, 7, 1),
        load_history=False)


def test_mock_full_league_stays_within_soft_budget() -> None:
    """Full N=18 double RR with mock lambdas stays under soft limits."""
    n_trials = resolve_perf_trials(DEFAULT_PERF_TRIALS)
    simulation_input = _full_league_input()
    assert len(simulation_input.fixtures) == REFERENCE_FIXTURE_COUNT
    config = SeasonSimulationConfig(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_SEASON_START,
        n_trials=n_trials,
        seed=42)
    base_state = _warm_state(list(simulation_input.team_ids), n_trials)
    predictor, _stats = _counting_predictor()
    simulator = DynamicSeasonSimulator(predictor)

    with WallClock() as clock:
        result = simulator.run(
            config,
            simulation_input=simulation_input,
            base_state=base_state)
    rss = peak_rss_mb()

    assert result.simulated_matches == REFERENCE_FIXTURE_COUNT
    assert len(result.projections) == REFERENCE_TEAM_COUNT
    assert len(result.processed_schedule_ids) == REFERENCE_FIXTURE_COUNT
    assert clock.elapsed <= MOCK_PERF_WALL_SECONDS_LIMIT, (
        f"mock wall {clock.elapsed:.1f}s exceeds "
        f"{MOCK_PERF_WALL_SECONDS_LIMIT:.0f}s soft budget "
        f"(trials={n_trials})")
    if rss is not None:
        assert rss <= MOCK_PERF_PEAK_RSS_MB_LIMIT, (
            f"peak RSS {rss:.0f} MiB exceeds "
            f"{MOCK_PERF_PEAK_RSS_MB_LIMIT:.0f} MiB soft budget")
    # diagnostyka dla odbioru — widoczna przy -s
    print(
        f"[season-perf] trials={n_trials} "
        f"fixtures={REFERENCE_FIXTURE_COUNT} "
        f"wall_s={clock.elapsed:.2f} "
        f"peak_rss_mb={None if rss is None else round(rss, 1)}")


def test_from_now_uses_fewer_samples_than_from_season_start() -> None:
    """FROM_NOW with fixed early rounds skips inference vs full season start."""
    n_trials = 100
    open_base = _full_league_input(
        MODE_COMPARE_TEAM_COUNT,
        mode=SimulationMode.FROM_NOW,
        fingerprint="perf-mode-open")
    from_now_input = _with_fixed_early_rounds(
        open_base, MODE_COMPARE_FIXED_ROUNDS)
    from_start_input = _as_season_start(from_now_input)
    fixed_count = sum(
        1 for item in from_now_input.fixtures if item.is_fixed)
    total = len(from_now_input.fixtures)
    assert fixed_count > 0
    assert fixed_count < total

    base_state = _warm_state(list(from_now_input.team_ids), n_trials)
    mode_results: dict[SimulationMode, tuple[object, int]] = {}
    for mode, simulation_input in (
            (SimulationMode.FROM_NOW, from_now_input),
            (SimulationMode.FROM_SEASON_START, from_start_input)):
        config = SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=mode,
            n_trials=n_trials,
            seed=42)
        predictor, stats = _counting_predictor()
        result = DynamicSeasonSimulator(predictor).run(
            config,
            simulation_input=simulation_input,
            base_state=base_state.copy())
        mode_results[mode] = (result, stats["inferred_rows"])

    now_result, now_rows = mode_results[SimulationMode.FROM_NOW]
    start_result, start_rows = mode_results[
        SimulationMode.FROM_SEASON_START]

    assert now_result.fixed_matches == fixed_count
    assert now_result.simulated_matches == total - fixed_count
    assert start_result.fixed_matches == 0
    assert start_result.simulated_matches == total
    assert (
        now_result.processed_schedule_ids
        == start_result.processed_schedule_ids)
    # FROM_NOW: open fixtures × trials; FROM_SEASON_START: wszystkie × trials
    assert now_rows == (total - fixed_count) * n_trials
    assert start_rows == total * n_trials
    assert now_rows < start_rows
    print(
        f"[season-perf-modes] teams={MODE_COMPARE_TEAM_COUNT} "
        f"fixed={fixed_count}/{total} "
        f"inferred_from_now={now_rows} "
        f"inferred_from_start={start_rows}")
