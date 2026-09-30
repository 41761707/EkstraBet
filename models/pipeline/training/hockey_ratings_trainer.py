"""Time-decayed Poisson attack-defense model for NHL.

The fit is Dixon-Coles in the attack, defense and exponential-decay
sense. Tie inflation is not the 1997 low-score rho: it rescales the
regulation diagonal after the rates are known. A constant
``p_ot_home`` then assigns each tie to an overtime winner.

The latest season in the sample keeps full weight. Older seasons
are multiplied by ``history_weight``, and attack/defense gaps are
pulled toward the league mean by ``shrink_matches`` games. A
60-day half-life overreacts to recent results. A flat long memory
keeps last year's ranking, which on 2025/26 was worse than a
constant home rate. Down-weighting that history is what moves the
moneyline log loss off a coin flip.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import ModelRunConfig
from models.pipeline.core.config import TrainingReport
from models.pipeline.core.registry import register_trainer
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_matches)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.early_season import (
    early_season_multiplier)
from models.pipeline.features.hockey.goalies import GOALIE_APPEARANCE_COLUMNS
from models.pipeline.features.hockey.goalies import build_goalie_ratings
from models.pipeline.features.hockey.lineup_strength import (
    apply_lineup_adjustment)
from models.pipeline.features.hockey.lineup_strength import (
    build_lineup_ratios)
from models.pipeline.labels.hockey_goals import HockeyGoalsLabeler
from models.pipeline.prediction.hockey_markets import DEFAULT_MAX_GOALS
from models.pipeline.prediction.hockey_markets import HockeyScoreDistribution
from models.pipeline.prediction.hockey_markets import build_score_distribution
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.training.trainer import Trainer


logger = logging.getLogger(__name__)

HOCKEY_SPORT_ID = 2
_FINISHED_RESULTS = {"1", "X", "2"}
_MIN_GOALIE_FACTOR = 0.25
_MAX_GOALIE_FACTOR = 4.0
_SAVE_EPSILON = 1e-4
_PROBABILITY_CLIP = 1e-6
_MIN_GOALS = 0.05
_NEWTON_RIDGE = 1e-6
_NEWTON_TOLERANCE = 1e-8
_SHRINK_GOALS = 3.0
_MIN_OT_TIES = 30
_FIT_COLUMNS = [
    "game_date",
    "season",
    "home_team",
    "away_team",
    "goals_home",
    "goals_away",
    "ot_home_win",
    "home_games_before",
    "away_games_before",
    "home_goalie_save_pct",
    "away_goalie_save_pct",
    "home_team_save_pct",
    "away_team_save_pct"]


def _default_low_weights() -> dict[int, float]:
    # Sezon 4 w matches to 2020/21: 952 mecze, grane tylko w dywizjach.
    return {4: 0.5}


def _default_beta_grid() -> tuple[float, ...]:
    return (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


@dataclass(frozen=True)
class HockeyDixonColesParams:
    """Decay, holdout season and the tie-inflation search.

    ``test_season`` 12 is 2025/26 in ``matches.season``. Season 4
    (2020/21) is down-weighted unless the config says otherwise.
    ``half_life_days`` is long on purpose: the current season should
    not be forgotten, while ``history_weight`` cuts older seasons.
    ``shrink_matches`` is the size of the pull toward a league-average
    team. Goalie form keeps its own, shorter half-life.
    """

    half_life_days: float = 1000.0
    league_id: int = 45
    test_season: int = 12
    low_weight_seasons: dict[int, float] = field(
        default_factory=_default_low_weights)
    early_season: EarlySeasonConfig = field(
        default_factory=EarlySeasonConfig)
    validation_days: int = 90
    tie_inflation_min: float = 1.0
    tie_inflation_max: float = 1.8
    tie_inflation_step: float = 0.02
    max_goals: int = DEFAULT_MAX_GOALS
    refit_every_days: int = 7
    newton_iterations: int = 25
    history_weight: float = 0.1
    shrink_matches: float = 15.0
    goalie_half_life_days: float = 180.0
    lineup_baseline_games: int = 10
    lineup_beta_off_grid: tuple[float, ...] = field(
        default_factory=_default_beta_grid)
    lineup_beta_def_grid: tuple[float, ...] = field(
        default_factory=_default_beta_grid)

    def __post_init__(self) -> None:
        if self.half_life_days <= 0.0:
            raise ValueError("half_life_days must be positive")
        if self.validation_days <= 0:
            raise ValueError("validation_days must be positive")
        if self.refit_every_days <= 0:
            raise ValueError("refit_every_days must be positive")
        if self.tie_inflation_min <= 0.0 or self.tie_inflation_step <= 0.0:
            raise ValueError("tie inflation search must be positive")
        if self.newton_iterations < 1:
            raise ValueError("newton_iterations must be positive")
        if self.max_goals < 1:
            raise ValueError("max_goals must be at least 1")
        if not 0.0 < self.history_weight <= 1.0:
            raise ValueError("history_weight must be in (0, 1]")
        if self.shrink_matches < 0.0:
            raise ValueError("shrink_matches cannot be negative")
        if self.goalie_half_life_days <= 0.0:
            raise ValueError("goalie_half_life_days must be positive")
        if self.lineup_baseline_games < 1:
            raise ValueError("lineup_baseline_games must be positive")
        _require_beta_grid("lineup_beta_off_grid", self.lineup_beta_off_grid)
        _require_beta_grid("lineup_beta_def_grid", self.lineup_beta_def_grid)


@dataclass(frozen=True)
class HockeyRatingsModel:
    """Fitted team rates plus the two scalars applied after lambda."""

    attack: dict[int, float]
    defense: dict[int, float]
    home_adv: float
    tie_inflation: float
    p_ot_home: float
    max_goals: int
    mean_defense: float
    beta_off: float = 0.0
    beta_def: float = 0.0

    def base_lambdas(
            self,
            home_team_id: int,
            away_team_id: int) -> tuple[float, float]:
        """Return regulation goal rates before the goalie correction.

        Unknown teams get a league-average attack of 0 and the mean
        fitted defense.
        """
        attack_home = self.attack.get(int(home_team_id), 0.0)
        attack_away = self.attack.get(int(away_team_id), 0.0)
        defense_home = self.defense.get(
            int(home_team_id), self.mean_defense)
        defense_away = self.defense.get(
            int(away_team_id), self.mean_defense)
        lambda_home = math.exp(
            self.home_adv + attack_home + defense_away)
        lambda_away = math.exp(attack_away + defense_home)
        return lambda_home, lambda_away

    def score_distribution(
            self,
            home_team_id: int,
            away_team_id: int,
            home_starter_save: float | None = None,
            away_starter_save: float | None = None,
            home_team_save: float | None = None,
            away_team_save: float | None = None,
            *,
            home_off_ratio: float = 1.0,
            away_off_ratio: float = 1.0,
            home_def_ratio: float = 1.0,
            away_def_ratio: float = 1.0) -> HockeyScoreDistribution:
        """Return the final-score distribution for one matchup.

        Ratios of 1 leave the lineup terms idle. A missing probable
        lineup therefore keeps the team-average strength.
        """
        lambda_home, lambda_away = adjusted_match_rates(
            self,
            home_team_id,
            away_team_id,
            home_starter_save,
            away_starter_save,
            home_team_save,
            away_team_save,
            home_off_ratio=home_off_ratio,
            away_off_ratio=away_off_ratio,
            home_def_ratio=home_def_ratio,
            away_def_ratio=away_def_ratio)
        return build_score_distribution(
            lambda_home,
            lambda_away,
            self.tie_inflation,
            self.p_ot_home,
            self.max_goals)


def hockey_params_from_config(
        config: ModelRunConfig) -> HockeyDixonColesParams:
    """Read Dixon-Coles knobs from the config ``ratings`` object."""
    if config.sport_id != HOCKEY_SPORT_ID:
        raise ValueError("Hockey ratings trainer requires sport_id=2")
    raw = getattr(config, "ratings", None)
    if not isinstance(raw, dict):
        raw = {}
    max_goals = int(getattr(config, "max_goals", DEFAULT_MAX_GOALS))
    if "max_goals" in raw:
        max_goals = int(raw["max_goals"])
    return HockeyDixonColesParams(
        half_life_days=float(raw.get("half_life_days", 1000.0)),
        league_id=int(raw.get("league_id", 45)),
        test_season=int(raw.get("test_season", 12)),
        low_weight_seasons=_low_weight_seasons(raw),
        early_season=EarlySeasonConfig(
            games=int(raw.get("early_season_games", 8)),
            boost=float(raw.get("early_season_boost", 2.5))),
        validation_days=int(raw.get("validation_days", 90)),
        tie_inflation_min=float(raw.get("tie_inflation_min", 1.0)),
        tie_inflation_max=float(raw.get("tie_inflation_max", 1.8)),
        tie_inflation_step=float(raw.get("tie_inflation_step", 0.02)),
        max_goals=max_goals,
        refit_every_days=int(raw.get("refit_every_days", 7)),
        newton_iterations=int(raw.get("newton_iterations", 25)),
        history_weight=float(raw.get("history_weight", 0.1)),
        shrink_matches=float(raw.get("shrink_matches", 15.0)),
        goalie_half_life_days=float(
            raw.get("goalie_half_life_days", 180.0)),
        lineup_baseline_games=int(raw.get("lineup_baseline_games", 10)),
        lineup_beta_off_grid=_beta_grid(raw, "lineup_beta_off_grid"),
        lineup_beta_def_grid=_beta_grid(raw, "lineup_beta_def_grid"))


def _require_beta_grid(name: str, grid: tuple[float, ...]) -> None:
    if not grid:
        raise ValueError(f"{name} must not be empty")
    for value in grid:
        if not math.isfinite(value):
            raise ValueError(f"{name} must contain finite numbers")


def _beta_grid(raw: dict[str, Any], key: str) -> tuple[float, ...]:
    if key not in raw:
        return _default_beta_grid()
    source = raw[key]
    if not isinstance(source, list) or not source:
        raise ValueError(f"{key} must be a non-empty list")
    return tuple(float(value) for value in source)


def _low_weight_seasons(raw: dict[str, Any]) -> dict[int, float]:
    if "low_weight_seasons" not in raw:
        return _default_low_weights()
    source = raw["low_weight_seasons"]
    if not isinstance(source, dict):
        raise ValueError("low_weight_seasons must be an object")
    return {int(season): float(weight) for season, weight in source.items()}


def sample_weights(
        game_dates: np.ndarray,
        as_of: np.datetime64,
        seasons: np.ndarray,
        home_games_before: np.ndarray,
        away_games_before: np.ndarray,
        params: HockeyDixonColesParams) -> np.ndarray:
    """Return per-match likelihood weights, 0 when the match is not prior.

    Weight is exponential time decay times the average early-season
    multiplier of the two clubs times the optional season weight.
    Matches from seasons older than the latest one in the sample
    are also multiplied by ``history_weight``.
    """
    dates = np.asarray(game_dates, dtype="datetime64[ns]")
    moment = np.datetime64(as_of, "ns")
    age_days = (moment - dates) / np.timedelta64(1, "D")
    age_days = np.asarray(age_days, dtype=float)
    weights = np.zeros(age_days.shape[0], dtype=float)
    eligible = np.isfinite(age_days) & (age_days > 0.0)
    if not np.any(eligible):
        return weights
    decay = np.exp(
        -math.log(2.0) * age_days[eligible] / params.half_life_days)
    home_boost = _early_weights(
        home_games_before[eligible], params.early_season)
    away_boost = _early_weights(
        away_games_before[eligible], params.early_season)
    season_weight = np.array([
        params.low_weight_seasons.get(int(season), 1.0)
        for season in seasons[eligible]
    ], dtype=float)
    history = _history_factors(
        dates, np.asarray(seasons), eligible, params.history_weight)
    weights[eligible] = (
        decay * 0.5 * (home_boost + away_boost)
        * season_weight * history)
    return weights


def _history_factors(
        dates: np.ndarray,
        seasons: np.ndarray,
        eligible: np.ndarray,
        history_weight: float) -> np.ndarray:
    """Down-weight every season older than the latest one in the sample."""
    count = int(np.count_nonzero(eligible))
    if history_weight == 1.0:
        return np.ones(count, dtype=float)
    focus = _focus_season(dates, seasons, eligible)
    return np.array([
        1.0 if int(season) == focus else history_weight
        for season in seasons[eligible]
    ], dtype=float)


def _focus_season(
        dates: np.ndarray,
        seasons: np.ndarray,
        eligible: np.ndarray) -> int:
    # Najnowsza data w próbce wyznacza sezon, który ma pełną wagę.
    eligible_dates = dates[eligible]
    latest = eligible_dates.max()
    on_latest = seasons[eligible][eligible_dates == latest]
    values, counts = np.unique(on_latest, return_counts=True)
    return int(values[int(np.argmax(counts))])


def _early_weights(
        games_before: np.ndarray,
        config: EarlySeasonConfig) -> np.ndarray:
    return np.array([
        early_season_multiplier(int(games), config)
        for games in games_before
    ], dtype=float)


def fit_dixon_coles(
        home_team: np.ndarray,
        away_team: np.ndarray,
        home_goals: np.ndarray,
        away_goals: np.ndarray,
        weights: np.ndarray,
        iterations: int = 25,
        shrink_matches: float = 0.0
        ) -> tuple[dict[int, float], dict[int, float], float]:
    """Fit attack, defense and home advantage by Newton on Poisson NLL.

    Defense is the log of goals conceded, so a larger value is a
    weaker team. Attack is constrained to sum to zero by coding the
    last team as the negative sum of the others.
    """
    if iterations < 1:
        raise ValueError("iterations must be positive")
    active = np.asarray(weights, dtype=float) > 0.0
    if not np.any(active):
        raise ValueError("Dixon-Coles fit needs a positive sample weight")
    home = np.asarray(home_team)[active].astype(int)
    away = np.asarray(away_team)[active].astype(int)
    scored_home = np.asarray(home_goals, dtype=float)[active]
    scored_away = np.asarray(away_goals, dtype=float)[active]
    active_weights = np.asarray(weights, dtype=float)[active]
    teams = np.unique(np.concatenate([home, away]))
    if teams.size < 2:
        raise ValueError("Dixon-Coles fit needs at least two teams")
    index = {int(team): position for position, team in enumerate(teams)}
    home_idx = np.array([index[int(team)] for team in home], dtype=int)
    away_idx = np.array([index[int(team)] for team in away], dtype=int)
    design = _design_matrix(home_idx, away_idx, int(teams.size))
    targets = np.concatenate([scored_home, scored_away])
    row_weights = np.concatenate([active_weights, active_weights])
    theta = _initial_theta(
        scored_home, scored_away, active_weights, int(teams.size))
    theta = _newton_fit(
        design, targets, row_weights, theta, iterations, shrink_matches)
    return _parameters_from_theta(theta, teams)


def _design_matrix(
        home_idx: np.ndarray,
        away_idx: np.ndarray,
        n_teams: int) -> np.ndarray:
    """Build home-goal and away-goal rows for the reduced parameterization."""
    n_matches = int(home_idx.shape[0])
    design = np.zeros((2 * n_matches, 2 * n_teams), dtype=float)
    home_rows = np.arange(n_matches)
    away_rows = home_rows + n_matches
    reference = n_teams - 1
    design[home_rows, 0] = 1.0
    _set_attack(design, home_rows, home_idx, reference, n_teams)
    _set_attack(design, away_rows, away_idx, reference, n_teams)
    design[home_rows, n_teams + away_idx] = 1.0
    design[away_rows, n_teams + home_idx] = 1.0
    return design


def _set_attack(
        design: np.ndarray,
        rows: np.ndarray,
        attacking: np.ndarray,
        reference: int,
        n_teams: int) -> None:
    free = attacking < reference
    design[rows[free], 1 + attacking[free]] = 1.0
    # Ostatnia drużyna ma atak równy minus sumie pozostałych.
    design[rows[~free], 1:n_teams] = -1.0


def _initial_theta(
        home_goals: np.ndarray,
        away_goals: np.ndarray,
        weights: np.ndarray,
        n_teams: int) -> np.ndarray:
    average_home = max(
        float(np.average(home_goals, weights=weights)), _MIN_GOALS)
    average_away = max(
        float(np.average(away_goals, weights=weights)), _MIN_GOALS)
    theta = np.zeros(2 * n_teams, dtype=float)
    theta[0] = math.log(average_home) - math.log(average_away)
    theta[n_teams:] = math.log(average_away)
    return theta


def _newton_fit(
        design: np.ndarray,
        targets: np.ndarray,
        weights: np.ndarray,
        theta: np.ndarray,
        iterations: int,
        shrink_matches: float = 0.0) -> np.ndarray:
    width = design.shape[1]
    n_teams = width // 2
    for _ in range(iterations):
        eta = np.clip(design @ theta, -20.0, 20.0)
        lam = np.exp(eta)
        gradient = design.T @ (weights * (targets - lam))
        curvature = design.T @ (design * (weights * lam)[:, None])
        curvature.flat[:: width + 1] += _NEWTON_RIDGE
        if shrink_matches > 0.0:
            _add_shrinkage(
                gradient, curvature, theta, n_teams, shrink_matches)
        step = _solve_step(curvature, gradient, width)
        if float(np.max(np.abs(step))) < _NEWTON_TOLERANCE:
            break
        theta = _line_search(
            theta, step, design, targets, weights,
            shrink_matches, n_teams)
    return theta


def _add_shrinkage(
        gradient: np.ndarray,
        curvature: np.ndarray,
        theta: np.ndarray,
        n_teams: int,
        shrink_matches: float) -> None:
    """Pull attacks to 0 and defenses toward their mean.

    The penalty matches ``shrink_matches`` games at a typical NHL
    scoring rate, so a short season cannot invent a large gap.
    """
    strength = shrink_matches * _SHRINK_GOALS
    attacks = theta[1:n_teams]
    gradient[1:n_teams] -= strength * (attacks + float(attacks.sum()))
    attack_width = n_teams - 1
    attack_penalty = strength * (
        np.eye(attack_width) + np.ones((attack_width, attack_width)))
    curvature[1:n_teams, 1:n_teams] += attack_penalty
    defense = theta[n_teams:]
    centered = defense - float(np.mean(defense))
    gradient[n_teams:] -= strength * centered
    share = np.ones((n_teams, n_teams)) / n_teams
    curvature[n_teams:, n_teams:] += strength * (np.eye(n_teams) - share)


def _solve_step(
        curvature: np.ndarray,
        gradient: np.ndarray,
        width: int) -> np.ndarray:
    try:
        return np.linalg.solve(curvature, gradient)
    except np.linalg.LinAlgError:
        curvature.flat[:: width + 1] += 1e-3
        return np.linalg.solve(curvature, gradient)


def _line_search(
        theta: np.ndarray,
        step: np.ndarray,
        design: np.ndarray,
        targets: np.ndarray,
        weights: np.ndarray,
        shrink_matches: float = 0.0,
        n_teams: int = 0) -> np.ndarray:
    current = _penalized_nll(
        theta, design, targets, weights, shrink_matches, n_teams)
    trial = step
    for _ in range(10):
        candidate = theta + trial
        score = _penalized_nll(
            candidate, design, targets, weights, shrink_matches, n_teams)
        if np.isfinite(score) and score <= current + 1e-8:
            return candidate
        trial = trial * 0.5
    return theta + trial


def _penalized_nll(
        theta: np.ndarray,
        design: np.ndarray,
        targets: np.ndarray,
        weights: np.ndarray,
        shrink_matches: float,
        n_teams: int) -> float:
    nll = _weighted_nll(theta, design, targets, weights)
    if shrink_matches <= 0.0 or n_teams < 2:
        return nll
    return nll + _shrink_penalty(theta, shrink_matches, n_teams)


def _shrink_penalty(
        theta: np.ndarray,
        shrink_matches: float,
        n_teams: int) -> float:
    strength = shrink_matches * _SHRINK_GOALS
    attacks = theta[1:n_teams]
    attack_ss = float(np.dot(attacks, attacks) + attacks.sum() ** 2)
    defense = theta[n_teams:]
    centered = defense - float(np.mean(defense))
    defense_ss = float(np.dot(centered, centered))
    return 0.5 * strength * (attack_ss + defense_ss)


def _weighted_nll(
        theta: np.ndarray,
        design: np.ndarray,
        targets: np.ndarray,
        weights: np.ndarray) -> float:
    eta = np.clip(design @ theta, -20.0, 20.0)
    lam = np.exp(eta)
    return float(np.sum(weights * (lam - targets * eta)))


def _parameters_from_theta(
        theta: np.ndarray,
        teams: np.ndarray) -> tuple[dict[int, float], dict[int, float], float]:
    n_teams = len(teams)
    attack = np.zeros(n_teams, dtype=float)
    attack[:-1] = theta[1:n_teams]
    attack[-1] = -float(attack[:-1].sum())
    defense = theta[n_teams:2 * n_teams]
    attack_map = {
        int(team): float(value)
        for team, value in zip(teams, attack)}
    defense_map = {
        int(team): float(value)
        for team, value in zip(teams, defense)}
    return attack_map, defense_map, float(theta[0])


def goalie_lambda_factor(
        starter_save: float | None,
        team_save: float | None) -> float:
    """Return ``(1 - sv_starter) / (1 - sv_team_avg)``, or 1 if unknown.

    The ratio is clamped so a corrupt save percentage cannot zero
    the goal rate or explode it.
    """
    starter = _save_rate(starter_save)
    team = _save_rate(team_save)
    if starter is None or team is None:
        return 1.0
    conceded = 1.0 - team
    if conceded <= _SAVE_EPSILON:
        return 1.0
    factor = (1.0 - starter) / conceded
    if factor < _MIN_GOALIE_FACTOR:
        return _MIN_GOALIE_FACTOR
    if factor > _MAX_GOALIE_FACTOR:
        return _MAX_GOALIE_FACTOR
    return factor


def apply_goalie_correction(
        lambda_home: float,
        lambda_away: float,
        home_starter_save: float | None,
        away_starter_save: float | None,
        home_team_save: float | None,
        away_team_save: float | None) -> tuple[float, float]:
    """Scale each rate by the goalie who faces those shots.

    Home goals are against the away starter, so the away save
    percentage changes ``lambda_home``.
    """
    adjusted_home = lambda_home * goalie_lambda_factor(
        away_starter_save, away_team_save)
    adjusted_away = lambda_away * goalie_lambda_factor(
        home_starter_save, home_team_save)
    return adjusted_home, adjusted_away


def adjusted_match_rates(
        model: HockeyRatingsModel,
        home_team_id: int,
        away_team_id: int,
        home_starter_save: float | None = None,
        away_starter_save: float | None = None,
        home_team_save: float | None = None,
        away_team_save: float | None = None,
        *,
        home_off_ratio: float = 1.0,
        away_off_ratio: float = 1.0,
        home_def_ratio: float = 1.0,
        away_def_ratio: float = 1.0) -> tuple[float, float]:
    """Return goal rates after the goalie and lineup corrections.

    Home goals face the away goalie and the away defence. Zero betas
    leave only the goalie factor.
    """
    base_home, base_away = model.base_lambdas(home_team_id, away_team_id)
    lambda_home = apply_lineup_adjustment(
        base_home,
        home_off_ratio,
        away_def_ratio,
        goalie_lambda_factor(away_starter_save, away_team_save),
        model.beta_off,
        model.beta_def)
    lambda_away = apply_lineup_adjustment(
        base_away,
        away_off_ratio,
        home_def_ratio,
        goalie_lambda_factor(home_starter_save, home_team_save),
        model.beta_off,
        model.beta_def)
    return lambda_home, lambda_away


def _save_rate(value: float | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(rate) or rate < 0.0 or rate >= 1.0:
        return None
    return rate


def calibrate_tie_inflation(
        lambda_home: np.ndarray,
        lambda_away: np.ndarray,
        goals_home: np.ndarray,
        goals_away: np.ndarray,
        params: HockeyDixonColesParams) -> float:
    """Pick the diagonal multiplier with the lowest regulation score NLL."""
    usable = _within_grid(goals_home, goals_away, params.max_goals)
    if not np.any(usable):
        return params.tie_inflation_min
    home_mass, away_mass = _batch_pmf(
        np.asarray(lambda_home, dtype=float)[usable],
        np.asarray(lambda_away, dtype=float)[usable],
        params.max_goals)
    scored_home = np.asarray(goals_home, dtype=int)[usable]
    scored_away = np.asarray(goals_away, dtype=int)[usable]
    return _best_inflation(
        home_mass, away_mass, scored_home, scored_away, params)


def _within_grid(
        goals_home: np.ndarray,
        goals_away: np.ndarray,
        max_goals: int) -> np.ndarray:
    home = np.asarray(goals_home)
    away = np.asarray(goals_away)
    return (
        (home >= 0) & (away >= 0)
        & (home <= max_goals) & (away <= max_goals))


def _batch_pmf(
        lambda_home: np.ndarray,
        lambda_away: np.ndarray,
        max_goals: int) -> tuple[np.ndarray, np.ndarray]:
    goals = np.arange(max_goals + 1, dtype=float)
    log_factorial = np.zeros(max_goals + 1, dtype=float)
    if max_goals:
        log_factorial[1:] = np.cumsum(np.log(goals[1:]))
    return (
        _pmf_rows(lambda_home, goals, log_factorial),
        _pmf_rows(lambda_away, goals, log_factorial))


def _pmf_rows(
        rates: np.ndarray,
        goals: np.ndarray,
        log_factorial: np.ndarray) -> np.ndarray:
    safe = np.clip(rates, 1e-8, None)
    log_mass = (
        -safe[:, None]
        + np.log(safe)[:, None] * goals[None, :]
        - log_factorial[None, :])
    return np.exp(log_mass)


def _best_inflation(
        home_mass: np.ndarray,
        away_mass: np.ndarray,
        goals_home: np.ndarray,
        goals_away: np.ndarray,
        params: HockeyDixonColesParams) -> float:
    mass = home_mass.sum(axis=1) * away_mass.sum(axis=1)
    diagonal = np.sum(home_mass * away_mass, axis=1)
    rows = np.arange(goals_home.shape[0])
    actual = home_mass[rows, goals_home] * away_mass[rows, goals_away]
    tied = goals_home == goals_away
    best_value = params.tie_inflation_min
    best_nll = math.inf
    inflation = params.tie_inflation_min
    while inflation <= params.tie_inflation_max + 1e-9:
        scale = np.where(tied, inflation, 1.0)
        normalizer = mass + (inflation - 1.0) * diagonal
        probability = actual * scale / np.clip(normalizer, 1e-15, None)
        nll = float(-np.mean(np.log(np.clip(probability, 1e-15, None))))
        if nll < best_nll:
            best_nll = nll
            best_value = inflation
        inflation += params.tie_inflation_step
    return float(best_value)


def estimate_p_ot_home(
        goals_home: np.ndarray,
        goals_away: np.ndarray,
        ot_home_win: np.ndarray) -> float:
    """Return the home overtime win rate among known regulation ties."""
    labels = pd.to_numeric(pd.Series(ot_home_win), errors="coerce")
    ties = np.asarray(goals_home) == np.asarray(goals_away)
    known = labels.loc[ties].dropna()
    if known.empty:
        return 0.5
    return float(known.mean())


def _known_ot_ties(
        goals_home: np.ndarray,
        goals_away: np.ndarray,
        ot_home_win: np.ndarray) -> int:
    labels = pd.to_numeric(pd.Series(ot_home_win), errors="coerce")
    ties = np.asarray(goals_home) == np.asarray(goals_away)
    return int(labels.loc[ties].dropna().shape[0])


def attach_season_games_before(frame: pd.DataFrame) -> pd.DataFrame:
    """Add matches already played by each club in the current season."""
    ordered = frame.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)
    pieces = []
    for side, column in (("home", "home_team"), ("away", "away_team")):
        part = ordered.loc[
            :, ["match_id", "season", "game_date", column]].copy()
        part.columns = ["match_id", "season", "game_date", "team"]
        part["side"] = side
        pieces.append(part)
    long = pd.concat(pieces, ignore_index=True)
    long = long.sort_values(
        ["season", "team", "game_date", "match_id", "side"])
    long["played_before"] = long.groupby(
        ["season", "team"], sort=False).cumcount()
    return _merge_games_before(ordered, long)


def _merge_games_before(
        ordered: pd.DataFrame,
        long: pd.DataFrame) -> pd.DataFrame:
    home = long.loc[long["side"] == "home", ["match_id", "played_before"]]
    away = long.loc[long["side"] == "away", ["match_id", "played_before"]]
    home = home.rename(columns={"played_before": "home_games_before"})
    away = away.rename(columns={"played_before": "away_games_before"})
    merged = ordered.merge(home, on="match_id", how="left")
    return merged.merge(away, on="match_id", how="left")


def attach_team_save_average(
        frame: pd.DataFrame,
        half_life_days: float) -> pd.DataFrame:
    """Add each club's decayed mean of previous starter save rates.

    The current match is not included. A club with no prior starter
    gets a missing average, and the goalie factor then stays 1.
    """
    ordered, home_average, away_average, _state = _walk_team_saves(
        frame, half_life_days)
    ordered["home_team_save_pct"] = home_average
    ordered["away_team_save_pct"] = away_average
    return ordered


def latest_team_save_rates(
        frame: pd.DataFrame,
        half_life_days: float) -> dict[int, float]:
    """Return the save rate each club would carry into its next match.

    This is the average after the last starter in ``frame``, which is
    what a match without a projected lineup should use.
    """
    _ordered, _home, _away, state = _walk_team_saves(frame, half_life_days)
    return {
        team_id: average
        for team_id, (_moment, average, _weight) in state.items()}


def _walk_team_saves(
        frame: pd.DataFrame,
        half_life_days: float) -> tuple[
            pd.DataFrame,
            list[float | None],
            list[float | None],
            dict[int, tuple[pd.Timestamp, float, float]]]:
    """Walk starters in order and keep the pre-match average of each row."""
    if half_life_days <= 0.0:
        raise ValueError("half_life_days must be positive")
    ordered = frame.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)
    state: dict[int, tuple[pd.Timestamp, float, float]] = {}
    home_average: list[float | None] = []
    away_average: list[float | None] = []
    for row in ordered.itertuples(index=False):
        moment = pd.Timestamp(row.game_date)
        home_average.append(_snapshot_save(state, int(row.home_team)))
        away_average.append(_snapshot_save(state, int(row.away_team)))
        _update_team_save(
            state, int(row.home_team), moment,
            _save_rate(_float_or_none(row.home_goalie_save_pct)),
            half_life_days)
        _update_team_save(
            state, int(row.away_team), moment,
            _save_rate(_float_or_none(row.away_goalie_save_pct)),
            half_life_days)
    return ordered, home_average, away_average, state


def _snapshot_save(
        state: dict[int, tuple[pd.Timestamp, float, float]],
        team_id: int) -> float | None:
    previous = state.get(team_id)
    if previous is None:
        return None
    return previous[1]


def _update_team_save(
        state: dict[int, tuple[pd.Timestamp, float, float]],
        team_id: int,
        moment: pd.Timestamp,
        save: float | None,
        half_life_days: float) -> None:
    if save is None:
        return
    previous = state.get(team_id)
    if previous is None:
        state[team_id] = (moment, save, 1.0)
        return
    last, average, weight = previous
    age_days = max((moment - last).total_seconds() / 86400.0, 0.0)
    decay = math.exp(-math.log(2.0) * age_days / half_life_days)
    decayed = weight * decay
    new_weight = decayed + 1.0
    new_average = (average * decayed + save) / new_weight
    state[team_id] = (moment, new_average, new_weight)


def fit_model_as_of(
        frame: pd.DataFrame,
        as_of: pd.Timestamp,
        params: HockeyDixonColesParams,
        lineup_betas: tuple[float, float] | None = None,
        *,
        validation_matches: int | None = None) -> HockeyRatingsModel:
    """Fit rates on matches strictly before ``as_of`` and calibrate scalars.

    ``lineup_betas`` skips the grid and uses that pair. Tie inflation
    on the returned model is refit after that correction.
    ``validation_matches`` scores that many latest games and does not
    fall back to the whole history.
    """
    model, _tie_before = _calibrated_model(
        frame, as_of, params, lineup_betas, validation_matches)
    return model


def _calibrated_model(
        frame: pd.DataFrame,
        as_of: pd.Timestamp,
        params: HockeyDixonColesParams,
        lineup_betas: tuple[float, float] | None,
        validation_matches: int | None) -> tuple[HockeyRatingsModel, float]:
    """Model plus tie inflation from before the lineup betas."""
    prepared = _require_columns(frame, _FIT_COLUMNS)
    moment = pd.Timestamp(as_of)
    prior = prepared.loc[prepared["game_date"] < moment].copy()
    if prior.empty:
        raise ValueError("No finished matches before the fit date")
    weights = sample_weights(
        prior["game_date"].to_numpy(),
        np.datetime64(moment.to_datetime64(), "ns"),
        prior["season"].to_numpy(),
        prior["home_games_before"].to_numpy(),
        prior["away_games_before"].to_numpy(),
        params)
    attack, defense, home_adv = fit_dixon_coles(
        prior["home_team"].to_numpy(),
        prior["away_team"].to_numpy(),
        prior["goals_home"].to_numpy(),
        prior["goals_away"].to_numpy(),
        weights,
        params.newton_iterations,
        params.shrink_matches)
    mean_defense = float(np.mean(list(defense.values())))
    validation = _validation_window(
        prior, moment, params, validation_matches)
    lambda_home, lambda_away = _adjusted_rates(
        validation, attack, defense, home_adv, mean_defense)
    tie_before = calibrate_tie_inflation(
        lambda_home,
        lambda_away,
        validation["goals_home"].to_numpy(),
        validation["goals_away"].to_numpy(),
        params)
    p_ot_home = _p_ot_for_fit(validation, prior)
    if lineup_betas is None:
        beta_off, beta_def = _fit_lineup_betas(
            validation,
            attack,
            defense,
            home_adv,
            mean_defense,
            tie_before,
            p_ot_home,
            params)
    else:
        beta_off, beta_def = (
            float(lineup_betas[0]), float(lineup_betas[1]))
    tie_after = _inflation_after_lineup(
        validation,
        attack,
        defense,
        home_adv,
        mean_defense,
        tie_before,
        beta_off,
        beta_def,
        params)
    model = HockeyRatingsModel(
        attack=attack,
        defense=defense,
        home_adv=home_adv,
        tie_inflation=tie_after,
        p_ot_home=p_ot_home,
        max_goals=params.max_goals,
        mean_defense=mean_defense,
        beta_off=beta_off,
        beta_def=beta_def)
    return model, tie_before


def _validation_window(
        prior: pd.DataFrame,
        as_of: pd.Timestamp,
        params: HockeyDixonColesParams,
        validation_matches: int | None) -> pd.DataFrame:
    if validation_matches is None:
        return _validation_slice(prior, as_of, params.validation_days)
    return _last_played_matches(prior, validation_matches)


def _last_played_matches(prior: pd.DataFrame, count: int) -> pd.DataFrame:
    """Latest ``count`` games. A short window is not widened."""
    if count < 1:
        raise ValueError("validation match count must be positive")
    ordered = prior.sort_values(["game_date", "match_id"])
    return ordered.tail(count).copy()


def _validation_slice(
        prior: pd.DataFrame,
        as_of: pd.Timestamp,
        validation_days: int) -> pd.DataFrame:
    start = as_of - pd.Timedelta(days=validation_days)
    recent = prior.loc[prior["game_date"] >= start]
    if len(recent) >= 40:
        return recent
    return prior


def _p_ot_for_fit(validation: pd.DataFrame, prior: pd.DataFrame) -> float:
    # Małe okno OT bywa jednostronne, więc wtedy bierzemy całą historię.
    home = validation["goals_home"].to_numpy()
    away = validation["goals_away"].to_numpy()
    labels = validation["ot_home_win"].to_numpy()
    if _known_ot_ties(home, away, labels) >= _MIN_OT_TIES:
        return estimate_p_ot_home(home, away, labels)
    return estimate_p_ot_home(
        prior["goals_home"].to_numpy(),
        prior["goals_away"].to_numpy(),
        prior["ot_home_win"].to_numpy())


def _adjusted_rates(
        frame: pd.DataFrame,
        attack: dict[int, float],
        defense: dict[int, float],
        home_adv: float,
        mean_defense: float) -> tuple[np.ndarray, np.ndarray]:
    model = HockeyRatingsModel(
        attack=attack,
        defense=defense,
        home_adv=home_adv,
        tie_inflation=1.0,
        p_ot_home=0.5,
        max_goals=DEFAULT_MAX_GOALS,
        mean_defense=mean_defense)
    lambda_home = np.empty(len(frame), dtype=float)
    lambda_away = np.empty(len(frame), dtype=float)
    for index, row in enumerate(frame.itertuples(index=False)):
        base_home, base_away = model.base_lambdas(
            int(row.home_team), int(row.away_team))
        lambda_home[index], lambda_away[index] = apply_goalie_correction(
            base_home,
            base_away,
            _float_or_none(row.home_goalie_save_pct),
            _float_or_none(row.away_goalie_save_pct),
            _float_or_none(row.home_team_save_pct),
            _float_or_none(row.away_team_save_pct))
    return lambda_home, lambda_away


def _inflation_after_lineup(
        validation: pd.DataFrame,
        attack: dict[int, float],
        defense: dict[int, float],
        home_adv: float,
        mean_defense: float,
        tie_inflation: float,
        beta_off: float,
        beta_def: float,
        params: HockeyDixonColesParams) -> float:
    """Refit the diagonal once lambdas include the lineup correction."""
    if beta_off == 0.0 and beta_def == 0.0:
        return tie_inflation
    if not _lineup_columns_ready(validation):
        return tie_inflation
    model = HockeyRatingsModel(
        attack=attack,
        defense=defense,
        home_adv=home_adv,
        tie_inflation=1.0,
        p_ot_home=0.5,
        max_goals=params.max_goals,
        mean_defense=mean_defense,
        beta_off=beta_off,
        beta_def=beta_def)
    lambda_home, lambda_away = _frame_rates(validation, model)
    return calibrate_tie_inflation(
        lambda_home,
        lambda_away,
        validation["goals_home"].to_numpy(),
        validation["goals_away"].to_numpy(),
        params)


def _fit_lineup_betas(
        validation: pd.DataFrame,
        attack: dict[int, float],
        defense: dict[int, float],
        home_adv: float,
        mean_defense: float,
        tie_inflation: float,
        p_ot_home: float,
        params: HockeyDixonColesParams) -> tuple[float, float]:
    """Pick betas on the validation window. Ties keep the smaller pair."""
    if not _lineup_columns_ready(validation):
        return 0.0, 0.0
    scored = validation.loc[validation["final_home_win"].notna()]
    if scored.empty:
        return 0.0, 0.0
    best = (0.0, 0.0)
    best_key = (math.inf, math.inf, math.inf)
    for beta_off in params.lineup_beta_off_grid:
        for beta_def in params.lineup_beta_def_grid:
            loss = _lineup_moneyline_loss(
                scored,
                attack,
                defense,
                home_adv,
                mean_defense,
                tie_inflation,
                p_ot_home,
                params.max_goals,
                float(beta_off),
                float(beta_def))
            key = (loss, abs(beta_off) + abs(beta_def), abs(beta_off))
            if key < best_key:
                best_key = key
                best = (float(beta_off), float(beta_def))
    return best


def _lineup_columns_ready(frame: pd.DataFrame) -> bool:
    required = (
        "home_lineup_off_ratio",
        "away_lineup_off_ratio",
        "home_lineup_def_ratio",
        "away_lineup_def_ratio",
        "final_home_win")
    return all(column in frame.columns for column in required)


def _lineup_moneyline_loss(
        frame: pd.DataFrame,
        attack: dict[int, float],
        defense: dict[int, float],
        home_adv: float,
        mean_defense: float,
        tie_inflation: float,
        p_ot_home: float,
        max_goals: int,
        beta_off: float,
        beta_def: float) -> float:
    model = HockeyRatingsModel(
        attack=attack,
        defense=defense,
        home_adv=home_adv,
        tie_inflation=tie_inflation,
        p_ot_home=p_ot_home,
        max_goals=max_goals,
        mean_defense=mean_defense,
        beta_off=beta_off,
        beta_def=beta_def)
    lambda_home, lambda_away = _frame_rates(frame, model)
    probability = _moneyline_home_probability(
        lambda_home, lambda_away, tie_inflation, p_ot_home, max_goals)
    target = frame["final_home_win"].to_numpy(dtype=float)
    return _log_loss(target, probability)


def _frame_rates(
        frame: pd.DataFrame,
        model: HockeyRatingsModel) -> tuple[np.ndarray, np.ndarray]:
    lambda_home = np.empty(len(frame), dtype=float)
    lambda_away = np.empty(len(frame), dtype=float)
    for index, row in enumerate(frame.itertuples(index=False)):
        lambda_home[index], lambda_away[index] = adjusted_match_rates(
            model,
            int(row.home_team),
            int(row.away_team),
            _float_or_none(row.home_goalie_save_pct),
            _float_or_none(row.away_goalie_save_pct),
            _float_or_none(row.home_team_save_pct),
            _float_or_none(row.away_team_save_pct),
            home_off_ratio=_ratio_field(row, "home_lineup_off_ratio"),
            away_off_ratio=_ratio_field(row, "away_lineup_off_ratio"),
            home_def_ratio=_ratio_field(row, "home_lineup_def_ratio"),
            away_def_ratio=_ratio_field(row, "away_lineup_def_ratio"))
    return lambda_home, lambda_away


def _ratio_field(row: Any, name: str) -> float:
    if not hasattr(row, name):
        return 1.0
    value = _float_or_none(getattr(row, name))
    if value is None:
        return 1.0
    return value


def _record_ratios(record: Any) -> dict[str, float]:
    return {
        "home_off_ratio": _ratio_field(record, "home_lineup_off_ratio"),
        "away_off_ratio": _ratio_field(record, "away_lineup_off_ratio"),
        "home_def_ratio": _ratio_field(record, "home_lineup_def_ratio"),
        "away_def_ratio": _ratio_field(record, "away_lineup_def_ratio")}


def _moneyline_home_probability(
        lambda_home: np.ndarray,
        lambda_away: np.ndarray,
        tie_inflation: float,
        p_ot_home: float,
        max_goals: int) -> np.ndarray:
    """Return P(home wins including overtime) for each rate pair.

    The diagonal is inflated and the grid is renormalized the same
    way as ``build_score_distribution``. Overtime then gives each tie
    to the home club with weight ``p_ot_home``.
    """
    home_mass, away_mass = _batch_pmf(
        np.clip(np.asarray(lambda_home, dtype=float), 0.0, None),
        np.clip(np.asarray(lambda_away, dtype=float), 0.0, None),
        max_goals)
    joint = home_mass[:, :, None] * away_mass[:, None, :]
    goals = np.arange(max_goals + 1)
    joint[:, goals, goals] *= tie_inflation
    totals = np.clip(joint.sum(axis=(1, 2)), 1e-15, None)
    home_goals = goals[:, None]
    away_goals = goals[None, :]
    home_win = (joint * (home_goals > away_goals)).sum(axis=(1, 2))
    tied = (joint * (home_goals == away_goals)).sum(axis=(1, 2))
    return home_win / totals + tied / totals * p_ot_home


def walk_forward_metrics(
        frame: pd.DataFrame,
        params: HockeyDixonColesParams,
        lineup_betas: tuple[float, float] | None = None) -> dict[str, Any]:
    """Score the test season in blocks that never see their own results.

    ``lineup_betas`` is the one pair judged on the holdout. Each block
    still refits attack and defense, then applies that pair.
    """
    prepared = _require_columns(
        frame, _FIT_COLUMNS + [
            "final_home_win", "final_home_goals", "final_away_goals"])
    test = prepared.loc[
        prepared["season"] == params.test_season].sort_values(
        ["game_date", "match_id"])
    if test.empty:
        raise ValueError(
            f"No finished matches for test season {params.test_season}")
    test = test.copy()
    test["_bucket"] = _bucket_keys(
        test["game_date"], params.refit_every_days)
    scored: list[dict[str, float]] = []
    skipped = 0
    inflations: list[float] = []
    inflations_before: list[float] = []
    for bucket, group in test.groupby("_bucket", sort=True):
        as_of = pd.Timestamp(int(bucket))
        model, tie_before = _calibrated_model(
            prepared, as_of, params, lineup_betas, None)
        # Bety 0 dostają inflację sprzed korekty składu.
        plain = replace(
            model,
            beta_off=0.0,
            beta_def=0.0,
            tie_inflation=tie_before)
        inflations.append(model.tie_inflation)
        inflations_before.append(tie_before)
        naive = _naive_rates(prepared, as_of)
        for record in group.drop(columns=["_bucket"]).itertuples(index=False):
            row = _score_one(model, record, naive, plain)
            if row is None:
                skipped += 1
                continue
            scored.append(row)
        logger.info(
            "Hockey holdout refit at %s, scored %s matches so far",
            as_of.isoformat(), len(scored))
    if not scored:
        raise ValueError("Hockey holdout produced no scored matches")
    return _metrics_from_rows(
        scored,
        skipped,
        inflations,
        inflations_before,
        prepared,
        params)


def _bucket_keys(dates: pd.Series, every_days: int) -> list[int]:
    starts: list[int] = []
    current: pd.Timestamp | None = None
    span = pd.Timedelta(days=every_days)
    for value in dates:
        moment = pd.Timestamp(value)
        if current is None or moment >= current + span:
            current = moment
        starts.append(int(current.value))
    return starts


def _naive_rates(frame: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, float]:
    """Constant pre-match frequencies: home win, over 5.5, home -1.5."""
    prior = frame.loc[
        (frame["game_date"] < as_of) & frame["final_home_win"].notna()]
    if prior.empty:
        return {"home": 0.5, "over": 0.5, "puck": 0.5}
    home = prior["final_home_goals"].to_numpy(dtype=float)
    away = prior["final_away_goals"].to_numpy(dtype=float)
    return {
        "home": float(prior["final_home_win"].astype(float).mean()),
        "over": float(np.mean(home + away > 5.5)),
        "puck": float(np.mean(home - away > 1.5))}


def _score_one(
        model: HockeyRatingsModel,
        record: Any,
        naive: dict[str, float],
        plain: HockeyRatingsModel) -> dict[str, float] | None:
    if _missing(record.final_home_win):
        return None
    ratios = _record_ratios(record)
    distribution = model.score_distribution(
        int(record.home_team),
        int(record.away_team),
        _float_or_none(record.home_goalie_save_pct),
        _float_or_none(record.away_goalie_save_pct),
        _float_or_none(record.home_team_save_pct),
        _float_or_none(record.away_team_save_pct),
        **ratios)
    plain_distribution = plain.score_distribution(
        int(record.home_team),
        int(record.away_team),
        _float_or_none(record.home_goalie_save_pct),
        _float_or_none(record.away_goalie_save_pct),
        _float_or_none(record.home_team_save_pct),
        _float_or_none(record.away_team_save_pct),
        **ratios)
    markets = derive_hockey_markets(distribution)
    plain_markets = derive_hockey_markets(plain_distribution)
    home_goals = int(record.final_home_goals)
    away_goals = int(record.final_away_goals)
    return {
        "y_home": float(record.final_home_win),
        "p_home": markets["ml_home"] / 100.0,
        "p_home_without_lineup": plain_markets["ml_home"] / 100.0,
        "beta_off": float(model.beta_off),
        "beta_def": float(model.beta_def),
        "p_naive_home": naive["home"],
        "y_over": 1.0 if home_goals + away_goals > 5.5 else 0.0,
        "p_over": markets["over_55"] / 100.0,
        "p_over_without_lineup": plain_markets["over_55"] / 100.0,
        "p_naive_over": naive["over"],
        "y_puck": 1.0 if home_goals - away_goals > 1.5 else 0.0,
        "p_puck": markets["pl_home_minus_15"] / 100.0,
        "p_puck_without_lineup": (
            plain_markets["pl_home_minus_15"] / 100.0),
        "p_naive_puck": naive["puck"]}


def _metrics_from_rows(
        rows: list[dict[str, float]],
        skipped: int,
        inflations: list[float],
        inflations_before: list[float],
        frame: pd.DataFrame,
        params: HockeyDixonColesParams) -> dict[str, Any]:
    table = pd.DataFrame(rows)
    y_home = table["y_home"].to_numpy(dtype=float)
    p_home = table["p_home"].to_numpy(dtype=float)
    p_naive_home = table["p_naive_home"].to_numpy(dtype=float)
    y_over = table["y_over"].to_numpy(dtype=float)
    p_over = table["p_over"].to_numpy(dtype=float)
    y_puck = table["y_puck"].to_numpy(dtype=float)
    p_puck = table["p_puck"].to_numpy(dtype=float)
    candidate_moneyline = _log_loss(y_home, p_home)
    without_lineup = _log_loss(
        y_home, table["p_home_without_lineup"].to_numpy(dtype=float))
    candidate_over = _log_loss(y_over, p_over)
    over_without = _log_loss(
        y_over, table["p_over_without_lineup"].to_numpy(dtype=float))
    candidate_puck = _log_loss(y_puck, p_puck)
    puck_without = _log_loss(
        y_puck, table["p_puck_without_lineup"].to_numpy(dtype=float))
    naive = _log_loss(y_home, p_naive_home)
    improves_moneyline = bool(candidate_moneyline < without_lineup)
    kept = _accept_lineup_adjustment(
        improves_moneyline,
        candidate_over,
        over_without,
        candidate_puck,
        puck_without)
    reported = _reported_market_probabilities(table, kept)
    if kept:
        moneyline = candidate_moneyline
        over_loss = candidate_over
        puck_loss = candidate_puck
    else:
        # Nagłówek to artefakt. Seria z betą zostaje obok.
        moneyline = without_lineup
        over_loss = over_without
        puck_loss = puck_without
    # Średnia inflacji z wariantu, z którego liczone są log-lossy.
    if kept:
        reported_inflation = inflations
    else:
        reported_inflation = inflations_before
    return {
        "test_season": int(params.test_season),
        "n_scored": int(len(table)),
        "n_skipped": int(skipped),
        "n_train": int((frame["season"] != params.test_season).sum()),
        "refit_count": int(len(inflations)),
        "moneyline_log_loss": moneyline,
        "moneyline_log_loss_with_lineup": candidate_moneyline,
        "moneyline_log_loss_without_lineup": without_lineup,
        "lineup_adjustment_improves_log_loss": improves_moneyline,
        "lineup_adjustment_kept": kept,
        "lineup_holdout_beta_off_mean": float(table["beta_off"].mean()),
        "lineup_holdout_beta_def_mean": float(table["beta_def"].mean()),
        "naive_home_log_loss": naive,
        "moneyline_brier": _brier(y_home, reported["home"]),
        "naive_home_brier": _brier(y_home, p_naive_home),
        "over_55_log_loss": over_loss,
        "over_55_log_loss_with_lineup": candidate_over,
        "over_55_log_loss_without_lineup": over_without,
        "over_55_brier": _brier(y_over, reported["over"]),
        "naive_over_55_log_loss": _log_loss(
            y_over, table["p_naive_over"].to_numpy(dtype=float)),
        "puck_line_home_minus_15_log_loss": puck_loss,
        "puck_line_home_minus_15_log_loss_with_lineup": candidate_puck,
        "puck_line_home_minus_15_log_loss_without_lineup": puck_without,
        "puck_line_home_minus_15_brier": _brier(y_puck, reported["puck"]),
        "naive_puck_line_log_loss": _log_loss(
            y_puck, table["p_naive_puck"].to_numpy(dtype=float)),
        "beats_naive_moneyline": bool(moneyline < naive),
        "holdout_tie_inflation_mean": float(np.mean(reported_inflation)),
        "moneyline_reliability": _reliability(y_home, reported["home"])}


def _reported_market_probabilities(
        table: pd.DataFrame,
        kept: bool) -> dict[str, np.ndarray]:
    """Probabilities of the variant that would be saved."""
    if kept:
        return {
            "home": table["p_home"].to_numpy(dtype=float),
            "over": table["p_over"].to_numpy(dtype=float),
            "puck": table["p_puck"].to_numpy(dtype=float)}
    return {
        "home": table["p_home_without_lineup"].to_numpy(dtype=float),
        "over": table["p_over_without_lineup"].to_numpy(dtype=float),
        "puck": table["p_puck_without_lineup"].to_numpy(dtype=float)}


def _accept_lineup_adjustment(
        improves_moneyline: bool,
        over_loss: float,
        over_without: float,
        puck_loss: float,
        puck_without: float) -> bool:
    """Keep the correction when moneyline falls and totals do not rise.

    Over 5.5 and the home puck line may stay level. Either one getting
    worse rejects the pair, even if the winner's log loss improved.
    """
    if not improves_moneyline:
        return False
    if over_loss > over_without:
        return False
    if puck_loss > puck_without:
        return False
    return True


def _betas_before_test_season(
        frame: pd.DataFrame,
        params: HockeyDixonColesParams) -> tuple[float, float]:
    """Betas from the last played matches before the test season."""
    test = frame.loc[frame["season"] == params.test_season]
    if test.empty:
        return 0.0, 0.0
    as_of = pd.Timestamp(test["game_date"].min())
    # Liczba meczów, nie dni. Pusta przerwa nie wciąga całej historii.
    model = fit_model_as_of(
        frame,
        as_of,
        params,
        validation_matches=params.validation_days)
    return float(model.beta_off), float(model.beta_def)


def _log_loss(target: np.ndarray, probability: np.ndarray) -> float:
    clipped = np.clip(probability, _PROBABILITY_CLIP, 1.0 - _PROBABILITY_CLIP)
    loss = target * np.log(clipped) + (1.0 - target) * np.log(1.0 - clipped)
    return float(-np.mean(loss))


def _brier(target: np.ndarray, probability: np.ndarray) -> float:
    return float(np.mean((probability - target) ** 2))


def _reliability(
        target: np.ndarray,
        probability: np.ndarray,
        bins: int = 10) -> list[dict[str, float]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    table: list[dict[str, float]] = []
    for start, end in zip(edges[:-1], edges[1:]):
        if end == 1.0:
            mask = (probability >= start) & (probability <= end)
        else:
            mask = (probability >= start) & (probability < end)
        count = int(mask.sum())
        if count == 0:
            continue
        table.append({
            "lower": float(start),
            "upper": float(end),
            "n": count,
            "p_mean": float(probability[mask].mean()),
            "y_rate": float(target[mask].mean())})
    return table


def load_training_frame(
        league_id: int,
        half_life_days: float = 180.0,
        baseline_games: int | None = None) -> pd.DataFrame:
    """Load finished NHL matches with as-of goalie save rates.

    ``baseline_games`` also attaches lineup ratios. Prediction omits
    it and keeps the goalie load unchanged.
    """
    matches = _finished_matches(fetch_hockey_matches(league_id))
    labeled = matches.join(HockeyGoalsLabeler().build_labels(matches))
    with_games = attach_season_games_before(labeled)
    player_stats = fetch_hockey_player_stats(league_id)
    rosters = fetch_hockey_match_rosters(league_id)
    with_goalies = _attach_starter_saves(
        with_games, player_stats, rosters)
    averaged = attach_team_save_average(
        with_goalies, half_life_days=half_life_days)
    finished = _attach_final_scores(averaged)
    if finished["match_id"].duplicated().any():
        raise ValueError("Starter join duplicated hockey matches")
    if baseline_games is not None:
        finished = _attach_lineup_ratios(
            finished, rosters, player_stats, baseline_games)
    logger.info(
        "Loaded %s finished NHL matches for league %s",
        len(finished), league_id)
    return finished


def _attach_lineup_ratios(
        frame: pd.DataFrame,
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int) -> pd.DataFrame:
    ratios = build_lineup_ratios(rosters, player_stats, baseline_games)
    return _merge_lineup_ratios(frame, ratios)


def _merge_lineup_ratios(
        frame: pd.DataFrame,
        ratios: pd.DataFrame) -> pd.DataFrame:
    home = _side_ratios(ratios, "home")
    away = _side_ratios(ratios, "away")
    merged = frame.merge(home, on=["match_id", "home_team"], how="left")
    merged = merged.merge(away, on=["match_id", "away_team"], how="left")
    columns = [
        "home_lineup_off_ratio",
        "home_lineup_def_ratio",
        "away_lineup_off_ratio",
        "away_lineup_def_ratio"]
    missing = int(merged[columns].isna().any(axis=1).sum())
    if missing:
        logger.warning(
            "Lineup ratios missing for %s matches; using average strength",
            missing)
    for column in columns:
        merged[column] = merged[column].fillna(1.0)
    return merged


def _side_ratios(ratios: pd.DataFrame, side: str) -> pd.DataFrame:
    team_column = "home_team" if side == "home" else "away_team"
    if ratios.empty:
        return pd.DataFrame(columns=[
            "match_id",
            team_column,
            f"{side}_lineup_off_ratio",
            f"{side}_lineup_def_ratio"])
    renamed = ratios.loc[:, [
        "match_id",
        "team_id",
        "lineup_off_ratio",
        "lineup_def_ratio"]].rename(columns={
            "team_id": team_column,
            "lineup_off_ratio": f"{side}_lineup_off_ratio",
            "lineup_def_ratio": f"{side}_lineup_def_ratio"})
    return renamed.drop_duplicates(["match_id", team_column])


def _finished_matches(matches: pd.DataFrame) -> pd.DataFrame:
    frame = matches.copy()
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    if frame["game_date"].dt.tz is not None:
        frame["game_date"] = frame["game_date"].dt.tz_localize(None)
    result = frame["result"].astype(str).str.strip()
    ready = frame.loc[result.isin(_FINISHED_RESULTS)].copy()
    ready = ready.loc[
        ready["home_team_goals"].notna() & ready["away_team_goals"].notna()]
    ready = ready.loc[ready["home_team"] != ready["away_team"]]
    ready["season"] = ready["season"].astype(int)
    ready["home_team"] = ready["home_team"].astype(int)
    ready["away_team"] = ready["away_team"].astype(int)
    if ready.empty:
        raise ValueError("No finished hockey matches were loaded")
    return ready.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)


def _attach_starter_saves(
        matches: pd.DataFrame,
        player_stats: pd.DataFrame,
        rosters: pd.DataFrame) -> pd.DataFrame:
    appearances = _goalie_appearances(player_stats)
    ratings = build_goalie_ratings(appearances)
    starters = _starter_save_table(ratings, rosters)
    home = starters.rename(columns={
        "team_id": "home_team",
        "goalie_save_pct": "home_goalie_save_pct"})
    away = starters.rename(columns={
        "team_id": "away_team",
        "goalie_save_pct": "away_goalie_save_pct"})
    merged = matches.merge(home, on=["match_id", "home_team"], how="left")
    return merged.merge(away, on=["match_id", "away_team"], how="left")


def _goalie_appearances(player_stats: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty:
        return pd.DataFrame(columns=GOALIE_APPEARANCE_COLUMNS)
    shots = pd.to_numeric(player_stats["shots_against"], errors="coerce")
    mask = shots.notna() & (shots > 0)
    columns = [
        column for column in GOALIE_APPEARANCE_COLUMNS
        if column in player_stats.columns]
    return player_stats.loc[mask, columns].copy()


def _starter_save_table(
        ratings: pd.DataFrame,
        rosters: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=[
        "match_id", "team_id", "goalie_save_pct"])
    if ratings.empty or rosters.empty:
        return empty
    line = pd.to_numeric(rosters["line"], errors="coerce")
    position = rosters["position"].astype(str).str.strip()
    starters = rosters.loc[
        (position == "G") & line.eq(1),
        ["match_id", "player_id", "team_id"]]
    merged = ratings.merge(
        starters, on=["match_id", "player_id", "team_id"], how="inner")
    if merged.empty:
        return empty
    ordered = merged.sort_values(
        ["match_id", "team_id", "shots_against", "player_id"],
        ascending=[True, True, False, True])
    kept = ordered.drop_duplicates(["match_id", "team_id"], keep="first")
    return kept.loc[:, ["match_id", "team_id", "goalie_save_pct"]]


def _attach_final_scores(frame: pd.DataFrame) -> pd.DataFrame:
    wins: list[float] = []
    home_goals: list[float] = []
    away_goals: list[float] = []
    for row in frame.itertuples(index=False):
        winner = _final_winner(
            int(row.goals_home), int(row.goals_away), row.ot_home_win)
        if winner is None:
            wins.append(np.nan)
            home_goals.append(np.nan)
            away_goals.append(np.nan)
            continue
        scored_home, scored_away = _final_totals(
            int(row.goals_home), int(row.goals_away), winner)
        wins.append(float(winner))
        home_goals.append(float(scored_home))
        away_goals.append(float(scored_away))
    finished = frame.copy()
    finished["final_home_win"] = wins
    finished["final_home_goals"] = home_goals
    finished["final_away_goals"] = away_goals
    return finished


def _final_winner(home: int, away: int, ot_home_win: object) -> int | None:
    if home > away:
        return 1
    if home < away:
        return 0
    decided = _maybe_int(ot_home_win)
    if decided not in (0, 1):
        return None
    return decided


def _final_totals(home: int, away: int, winner: int) -> tuple[int, int]:
    if home != away:
        return home, away
    if winner == 1:
        return home + 1, away
    return home, away + 1


def _maybe_int(value: object) -> int | None:
    if _missing(value) or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def _float_or_none(value: object) -> float | None:
    if _missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None
    if not math.isfinite(number):
        return None
    return number


def _missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing hockey training columns: {missing}")
    return frame


def _production_metrics(
        model: HockeyRatingsModel,
        frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "home_adv": float(model.home_adv),
        "tie_inflation": float(model.tie_inflation),
        "p_ot_home": float(model.p_ot_home),
        "beta_off": float(model.beta_off),
        "beta_def": float(model.beta_def),
        "n_teams": int(len(model.attack)),
        "n_production_matches": int(len(frame))}


def _save_run(
        config: ModelRunConfig,
        model: HockeyRatingsModel,
        metrics: dict[str, Any],
        params: HockeyDixonColesParams) -> None:
    artifacts.save_model_artifact(config.artifact_dir, model)
    artifacts.save_metrics(config.artifact_dir, metrics)
    artifacts.save_meta(config.artifact_dir, {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "task_type": config.task_type,
        "trainer": "HockeyRatingsTrainer",
        "home_adv": model.home_adv,
        "tie_inflation": model.tie_inflation,
        "p_ot_home": model.p_ot_home,
        "max_goals": model.max_goals,
        "mean_defense": model.mean_defense,
        "attack": _string_key_map(model.attack),
        "defense": _string_key_map(model.defense),
        "output": ["lambda_home", "lambda_away"],
        "loss": "time_decayed_poisson_attack_defense",
        "half_life_days": params.half_life_days,
        "history_weight": params.history_weight,
        "shrink_matches": params.shrink_matches,
        "goalie_half_life_days": params.goalie_half_life_days,
        "goalie_correction": "(1 - sv_starter) / (1 - sv_team_avg)",
        "beta_off": model.beta_off,
        "beta_def": model.beta_def,
        "lineup_adjustment": (
            "lambda * off_ratio^beta_off"
            " * opp_def_ratio^(-beta_def) * goalie_factor"),
        "holdout": "walk_forward_before_each_refit_block",
        "production_fit": "all_finished_matches"})


def _string_key_map(values: dict[int, float]) -> dict[str, float]:
    return {
        str(team): float(values[team])
        for team in sorted(values)}


def _report_feature_columns() -> list[str]:
    return [
        "attack",
        "defense",
        "home_adv",
        "tie_inflation",
        "p_ot_home"]


@register_trainer("HockeyRatingsTrainer")
class HockeyRatingsTrainer(Trainer):
    """Train HOCKEY_RATINGS_POISSON_V1 and score a season holdout."""

    def train(self, config: ModelRunConfig) -> TrainingReport:
        """Fit the production artifact and write holdout metrics."""
        params = hockey_params_from_config(config)
        frame = load_training_frame(
            params.league_id,
            params.goalie_half_life_days,
            baseline_games=params.lineup_baseline_games)
        holdout_betas = _betas_before_test_season(frame, params)
        metrics = walk_forward_metrics(
            frame, params, lineup_betas=holdout_betas)
        as_of = pd.Timestamp(frame["game_date"].max()) + pd.Timedelta(days=1)
        production = fit_model_as_of(frame, as_of, params)
        kept = bool(metrics["lineup_adjustment_kept"])
        # Zapisana para jest tą z holdoutu. Odrzucenie zostawia bety 0
        # i inflację policzoną na λ bez korekty składu.
        saved_betas = holdout_betas if kept else (0.0, 0.0)
        model = fit_model_as_of(
            frame, as_of, params, lineup_betas=saved_betas)
        metrics["lineup_holdout_beta_off"] = holdout_betas[0]
        metrics["lineup_holdout_beta_def"] = holdout_betas[1]
        metrics["lineup_production_beta_off"] = float(production.beta_off)
        metrics["lineup_production_beta_def"] = float(production.beta_def)
        metrics["lineup_beta_off"] = float(model.beta_off)
        metrics["lineup_beta_def"] = float(model.beta_def)
        metrics.update(_production_metrics(model, frame))
        _save_run(config, model, metrics, params)
        logger.info(
            "NHL moneyline log loss %.4f with lineup, %.4f without, "
            "artifact %.4f, naive %.4f on %s matches",
            metrics["moneyline_log_loss_with_lineup"],
            metrics["moneyline_log_loss_without_lineup"],
            metrics["moneyline_log_loss"],
            metrics["naive_home_log_loss"],
            metrics["n_scored"])
        if kept:
            logger.info(
                "Keeping lineup adjustment beta_off=%.2f beta_def=%.2f",
                model.beta_off,
                model.beta_def)
        else:
            logger.info(
                "Lineup adjustment was not kept; betas set to 0")
        if not metrics["beats_naive_moneyline"]:
            logger.warning(
                "Hockey moneyline log loss did not beat the naive home rate")
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=_report_feature_columns(),
            n_train=int(metrics["n_train"]),
            n_test=int(metrics["n_scored"]),
            skipped_matches=int(metrics["n_skipped"]))

    def evaluate(self, config: ModelRunConfig) -> EvaluationReport:
        """Recompute the walk-forward holdout without saving artifacts."""
        params = hockey_params_from_config(config)
        frame = load_training_frame(
            params.league_id,
            params.goalie_half_life_days,
            baseline_games=params.lineup_baseline_games)
        holdout_betas = _betas_before_test_season(frame, params)
        metrics = walk_forward_metrics(
            frame, params, lineup_betas=holdout_betas)
        metrics["lineup_holdout_beta_off"] = holdout_betas[0]
        metrics["lineup_holdout_beta_def"] = holdout_betas[1]
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=int(metrics["n_scored"]),
            skipped_matches=int(metrics["n_skipped"]))

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: ModelRunConfig,
            sample_weight: pd.Series | None = None) -> HockeyRatingsModel:
        """Fit attack and defense. Tie inflation stays 1 until ``train``."""
        params = hockey_params_from_config(config)
        goals = _label_frame(labels)
        if sample_weight is None:
            weights = np.ones(len(features), dtype=float)
        else:
            weights = sample_weight.to_numpy(dtype=float)
        attack, defense, home_adv = fit_dixon_coles(
            features["home_team"].to_numpy(),
            features["away_team"].to_numpy(),
            goals["goals_home"].to_numpy(),
            goals["goals_away"].to_numpy(),
            weights,
            params.newton_iterations)
        return HockeyRatingsModel(
            attack=attack,
            defense=defense,
            home_adv=home_adv,
            tie_inflation=1.0,
            p_ot_home=0.5,
            max_goals=params.max_goals,
            mean_defense=float(np.mean(list(defense.values()))))


def _label_frame(labels: pd.Series | pd.DataFrame) -> pd.DataFrame:
    if isinstance(labels, pd.DataFrame):
        missing = [
            column for column in ("goals_home", "goals_away")
            if column not in labels.columns]
        if missing:
            raise KeyError(f"Missing goal label columns: {missing}")
        return labels
    raise TypeError(
        "HockeyRatingsTrainer.fit expects a DataFrame of goal labels")
