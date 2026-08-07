"""Dynamic Monte Carlo season simulator (two modes)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from typing import Callable
from typing import Sequence

import numpy as np

from models.pipeline.core.config import SequenceBatch
from models.pipeline.features.chronological_state import (
    BuiltMatchupFeatures)
from models.pipeline.features.chronological_state import (
    ChronologicalFeatureState)
from models.pipeline.features.chronological_state import (
    SimulatedMatchResult)
from models.pipeline.features.chronological_state import (
    build_season_start_state)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)
from models.pipeline.simulation.aggregation import BaselineStanding
from models.pipeline.simulation.aggregation import TeamSeasonProjection
from models.pipeline.simulation.aggregation import aggregate_projection
from models.pipeline.simulation.aggregation import baseline_from_standings
from models.pipeline.simulation.config import ResolvedFixture
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.outcome_sampler import sample_poisson_scores


StateBuilder = Callable[
    [SeasonSimulationConfig, SeasonSimulationInput],
    ChronologicalFeatureState]
InputLoader = Callable[
    [int, int, SimulationMode],
    SeasonSimulationInput]


@dataclass
class TrialStandingState:
    """Vectorized W/D/L / GF / GA / points for one trial."""

    team_ids: tuple[int, ...]
    wins: np.ndarray
    draws: np.ndarray
    losses: np.ndarray
    goals_for: np.ndarray
    goals_against: np.ndarray

    @classmethod
    def empty(cls, team_ids: Sequence[int]) -> TrialStandingState:
        """Return day-0 standings for the stable roster order."""
        ids = tuple(int(team_id) for team_id in team_ids)
        zeros = np.zeros(len(ids), dtype=int)
        return cls(
            team_ids=ids,
            wins=zeros.copy(),
            draws=zeros.copy(),
            losses=zeros.copy(),
            goals_for=zeros.copy(),
            goals_against=zeros.copy())

    @property
    def points(self) -> np.ndarray:
        """Return points as ``3 * W + D``."""
        return 3 * self.wins + self.draws

    @property
    def goal_difference(self) -> np.ndarray:
        """Return goals for minus goals against."""
        return self.goals_for - self.goals_against

    def copy(self) -> TrialStandingState:
        """Return an independent copy of all counters."""
        return TrialStandingState(
            team_ids=self.team_ids,
            wins=self.wins.copy(),
            draws=self.draws.copy(),
            losses=self.losses.copy(),
            goals_for=self.goals_for.copy(),
            goals_against=self.goals_against.copy())

    def apply_result(
            self,
            home_team_id: int,
            away_team_id: int,
            home_goals: int,
            away_goals: int) -> None:
        """Commit one finished match into the standings vectors."""
        home_index = self._index(home_team_id)
        away_index = self._index(away_team_id)
        self.goals_for[home_index] += home_goals
        self.goals_against[home_index] += away_goals
        self.goals_for[away_index] += away_goals
        self.goals_against[away_index] += home_goals
        if home_goals > away_goals:
            self.wins[home_index] += 1
            self.losses[away_index] += 1
        elif home_goals < away_goals:
            self.wins[away_index] += 1
            self.losses[home_index] += 1
        else:
            self.draws[home_index] += 1
            self.draws[away_index] += 1

    def _index(self, team_id: int) -> int:
        try:
            return self.team_ids.index(team_id)
        except ValueError as exc:
            raise KeyError(f"unknown team_id={team_id}") from exc


@dataclass(frozen=True)
class SeasonSimulationResult:
    """Completed Monte Carlo run ready for aggregation / persistence."""

    config: SeasonSimulationConfig
    projections: list[TeamSeasonProjection]
    input_fingerprint: str
    fixed_matches: int
    simulated_matches: int
    processed_schedule_ids: tuple[int, ...]


class DynamicSeasonSimulator:
    """Run independent trials over schedule rounds for both modes."""

    def __init__(
            self,
            predictor: FutureEventsPredictor,
            *,
            input_loader: InputLoader | None = None,
            state_builder: StateBuilder | None = None) -> None:
        if predictor.goals_config is None:
            raise ValueError("goals Poisson config is required")
        self._predictor = predictor
        if input_loader is not None:
            self._input_loader = input_loader
        else:
            # lokalny import — unikamy cyklu z schedule_repository
            from models.pipeline.data.schedule_repository import (
                fetch_season_simulation_input as _fetch_input)
            self._input_loader = _fetch_input
        self._state_builder = state_builder

    def run(
            self,
            config: SeasonSimulationConfig,
            *,
            simulation_input: SeasonSimulationInput | None = None,
            base_state: ChronologicalFeatureState | None = None
    ) -> SeasonSimulationResult:
        """Simulate the season and aggregate end-of-season projections.

        Pass ``simulation_input`` / ``base_state`` in tests to avoid DB.
        Production leaves them ``None`` and loads schedule + warm-start.
        """
        from models.pipeline.data.schedule_repository import (
            validate_fixture_completeness)

        loaded = simulation_input or self._input_loader(
            config.league_id, config.season_id, config.mode)
        _assert_input_matches_config(loaded, config)
        validation = validate_fixture_completeness(loaded)
        if not validation.is_valid:
            raise ValueError(
                validation.error_message or "incomplete schedule")
        if base_state is not None:
            state = base_state
        elif self._state_builder is not None:
            state = self._state_builder(config, loaded)
        else:
            state = self._build_default_state(config, loaded)
        return self._run_trials(config, loaded, state)

    def _build_default_state(
            self,
            config: SeasonSimulationConfig,
            simulation_input: SeasonSimulationInput
    ) -> ChronologicalFeatureState:
        goals = self._predictor.goals_config
        assert goals is not None  # sprawdzone w __init__
        return build_season_start_state(
            simulation_input.team_ids,
            config,
            window=goals.window_size,
            sequence_feature_columns=(
                list(goals.sequence_feature_columns)
                if goals.sequence_feature_columns else None),
            static_feature_columns=(
                list(goals.static_feature_columns)
                if goals.static_feature_columns else None))

    def _run_trials(
            self,
            config: SeasonSimulationConfig,
            simulation_input: SeasonSimulationInput,
            base_state: ChronologicalFeatureState
    ) -> SeasonSimulationResult:
        fixtures = simulation_input.fixtures
        team_ids = tuple(simulation_input.team_ids)
        rounds = _group_fixtures_by_round(fixtures)
        first_round = min(rounds)
        season_anchor = _require_season_anchor(base_state)
        rng = np.random.default_rng(config.seed)
        feature_states = [
            base_state.copy() for _ in range(config.n_trials)]
        standings = [
            TrialStandingState.empty(team_ids)
            for _ in range(config.n_trials)]
        processed_ids: list[int] = []
        fixed_count = sum(1 for item in fixtures if item.is_fixed)
        simulated_count = len(fixtures) - fixed_count

        for round_number in sorted(rounds):
            round_fixtures = rounds[round_number]
            synthetic_date = season_anchor + timedelta(
                days=(round_number - first_round) * config.days_per_round)
            self._simulate_round(
                config=config,
                round_fixtures=round_fixtures,
                synthetic_date=synthetic_date,
                feature_states=feature_states,
                standings=standings,
                rng=rng)
            processed_ids.extend(
                fixture.schedule.id for fixture in round_fixtures)

        _assert_each_schedule_row_once(fixtures, processed_ids)
        baseline = _build_baseline(
            config.mode, fixtures, team_ids)
        final_points = np.stack([row.points for row in standings])
        final_gd = np.stack([row.goal_difference for row in standings])
        projections = aggregate_projection(
            final_points, final_gd, team_ids, baseline)
        return SeasonSimulationResult(
            config=config,
            projections=projections,
            input_fingerprint=simulation_input.input_fingerprint,
            fixed_matches=fixed_count,
            simulated_matches=simulated_count,
            processed_schedule_ids=tuple(processed_ids))

    def _simulate_round(
            self,
            *,
            config: SeasonSimulationConfig,
            round_fixtures: list[ResolvedFixture],
            synthetic_date: date,
            feature_states: list[ChronologicalFeatureState],
            standings: list[TrialStandingState],
            rng: np.random.Generator) -> None:
        sampled = self._sample_open_fixtures(
            config=config,
            round_fixtures=round_fixtures,
            synthetic_date=synthetic_date,
            feature_states=feature_states,
            rng=rng)
        for trial_index, feature_state in enumerate(feature_states):
            results = _round_results_for_trial(
                round_fixtures, sampled[trial_index])
            feature_state.commit_round(results, synthetic_date)
            for result in results:
                standings[trial_index].apply_result(
                    result.home_team_id,
                    result.away_team_id,
                    result.home_goals,
                    result.away_goals)

    def _sample_open_fixtures(
            self,
            *,
            config: SeasonSimulationConfig,
            round_fixtures: list[ResolvedFixture],
            synthetic_date: date,
            feature_states: list[ChronologicalFeatureState],
            rng: np.random.Generator
    ) -> list[dict[int, tuple[int, int]]]:
        """Return per-trial score map for non-fixed fixtures of the round."""
        open_fixtures = [
            fixture for fixture in round_fixtures if not fixture.is_fixed]
        n_trials = len(feature_states)
        if not open_fixtures:
            return [{} for _ in range(n_trials)]
        built_rows: list[BuiltMatchupFeatures] = []
        keys: list[tuple[int, int]] = []
        for trial_index, feature_state in enumerate(feature_states):
            for fixture in open_fixtures:
                built = feature_state.build_matchup_features(
                    fixture.schedule.home_team_id,
                    fixture.schedule.away_team_id,
                    synthetic_date)
                if built is None:
                    raise ValueError(
                        "insufficient sequence history for team pair "
                        f"({fixture.schedule.home_team_id}, "
                        f"{fixture.schedule.away_team_id}) "
                        f"on {synthetic_date}")
                built_rows.append(built)
                keys.append((trial_index, fixture.schedule.id))
        rates = self._predictor.predict_goal_rates(
            _stack_features(built_rows),
            batch_size=config.inference_batch_size)
        scores = sample_poisson_scores(rates, rng)
        per_trial: list[dict[int, tuple[int, int]]] = [
            {} for _ in range(n_trials)]
        for row_index, (trial_index, schedule_id) in enumerate(keys):
            per_trial[trial_index][schedule_id] = (
                int(scores[row_index, 0]),
                int(scores[row_index, 1]))
        return per_trial


def _assert_input_matches_config(
        simulation_input: SeasonSimulationInput,
        config: SeasonSimulationConfig) -> None:
    if simulation_input.league_id != config.league_id:
        raise ValueError("simulation_input.league_id does not match config")
    if simulation_input.season_id != config.season_id:
        raise ValueError("simulation_input.season_id does not match config")
    if simulation_input.mode is not config.mode:
        raise ValueError("simulation_input.mode does not match config")


def _require_season_anchor(state: ChronologicalFeatureState) -> date:
    if state.season_anchor is None:
        raise ValueError("base_state.season_anchor is required")
    return state.season_anchor


def _group_fixtures_by_round(
        fixtures: list[ResolvedFixture]
) -> dict[int, list[ResolvedFixture]]:
    grouped: dict[int, list[ResolvedFixture]] = defaultdict(list)
    for fixture in fixtures:
        grouped[fixture.schedule.round].append(fixture)
    return dict(grouped)


def _round_results_for_trial(
        round_fixtures: list[ResolvedFixture],
        sampled: dict[int, tuple[int, int]]
) -> list[SimulatedMatchResult]:
    results: list[SimulatedMatchResult] = []
    for fixture in round_fixtures:
        schedule = fixture.schedule
        if fixture.is_fixed:
            if fixture.home_goals is None or fixture.away_goals is None:
                raise ValueError(
                    "fixed fixture is missing goals "
                    f"(schedule_id={schedule.id})")
            home_goals = fixture.home_goals
            away_goals = fixture.away_goals
        else:
            home_goals, away_goals = sampled[schedule.id]
        results.append(SimulatedMatchResult(
            home_team_id=schedule.home_team_id,
            away_team_id=schedule.away_team_id,
            home_goals=home_goals,
            away_goals=away_goals,
            league_id=schedule.league_id))
    return results


def _stack_features(
        rows: list[BuiltMatchupFeatures]) -> SequenceBatch:
    return SequenceBatch(
        X_home=np.stack([row.home_sequence for row in rows]),
        X_away=np.stack([row.away_sequence for row in rows]),
        X_static=np.stack([row.static_features for row in rows]))


def _assert_each_schedule_row_once(
        fixtures: list[ResolvedFixture],
        processed_ids: list[int]) -> None:
    expected = [fixture.schedule.id for fixture in fixtures]
    if len(processed_ids) != len(expected):
        raise RuntimeError(
            "schedule rows processed count mismatch: "
            f"expected {len(expected)}, got {len(processed_ids)}")
    if sorted(processed_ids) != sorted(expected):
        raise RuntimeError(
            "schedule row id set diverged from input fixtures")
    if len(set(processed_ids)) != len(processed_ids):
        raise RuntimeError("duplicate schedule row processing detected")


def _build_baseline(
        mode: SimulationMode,
        fixtures: list[ResolvedFixture],
        team_ids: tuple[int, ...]
) -> list[BaselineStanding]:
    standings = TrialStandingState.empty(team_ids)
    if mode is SimulationMode.FROM_NOW:
        for fixture in fixtures:
            if not fixture.is_fixed:
                continue
            if fixture.home_goals is None or fixture.away_goals is None:
                raise ValueError(
                    "fixed fixture is missing goals "
                    f"(schedule_id={fixture.schedule.id})")
            standings.apply_result(
                fixture.schedule.home_team_id,
                fixture.schedule.away_team_id,
                fixture.home_goals,
                fixture.away_goals)
    return baseline_from_standings(
        team_ids, standings.points, standings.goal_difference)
