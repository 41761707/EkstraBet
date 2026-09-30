"""Synthetic checks for the NHL attack-defense baseline."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import get_labeler
from models.pipeline.core.registry import get_trainer
from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.labels.hockey_goals import label_hockey_goals
from models.pipeline.prediction.hockey_markets import build_score_distribution
from models.pipeline.training.hockey_ratings_trainer import (
    HockeyDixonColesParams)
from models.pipeline.training.hockey_ratings_trainer import HockeyRatingsModel
from models.pipeline.training.hockey_ratings_trainer import (
    apply_goalie_correction)
from models.pipeline.training.hockey_ratings_trainer import (
    attach_season_games_before)
from models.pipeline.training.hockey_ratings_trainer import (
    attach_team_save_average)
from models.pipeline.training.hockey_ratings_trainer import estimate_p_ot_home
from models.pipeline.training.hockey_ratings_trainer import fit_dixon_coles
from models.pipeline.training.hockey_ratings_trainer import fit_model_as_of
from models.pipeline.training.hockey_ratings_trainer import (
    goalie_lambda_factor)
from models.pipeline.training.hockey_ratings_trainer import (
    hockey_params_from_config)
from models.pipeline.training.hockey_ratings_trainer import sample_weights


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_CONFIG = (
    REPO_ROOT / "models" / "configs" / "training"
    / "hockey_ratings_poisson_v1.json")
PREDICTION_CONFIG = (
    REPO_ROOT / "models" / "configs" / "prediction"
    / "hockey_ratings_poisson_v1.json")


def _flat_params(
        early_season: EarlySeasonConfig | None = None
        ) -> HockeyDixonColesParams:
    settings = early_season or EarlySeasonConfig(games=8, boost=1.0)
    return HockeyDixonColesParams(
        half_life_days=60.0,
        early_season=settings,
        low_weight_seasons={4: 0.5},
        history_weight=1.0,
        shrink_matches=0.0)


def test_sample_weights_decay_early_season_and_covid_season() -> None:
    as_of = np.datetime64("2025-03-02T00:00:00")
    dates = np.array([
        "2025-03-01T00:00:00",
        "2025-01-01T00:00:00",
        "2025-03-02T00:00:00"], dtype="datetime64[ns]")
    seasons = np.array([12, 12, 12])
    games = np.zeros(3, dtype=int)
    flat = _flat_params()
    weights = sample_weights(dates, as_of, seasons, games, games, flat)
    fresh = math.exp(-math.log(2.0) * 1.0 / flat.half_life_days)
    assert weights[0] == pytest.approx(fresh)
    assert weights[1] == pytest.approx(0.5)
    assert weights[2] == 0.0

    boosted = _flat_params(EarlySeasonConfig(games=8, boost=2.5))
    early = sample_weights(
        dates[:1], as_of, seasons[:1],
        np.array([0]), np.array([0]), boosted)
    late = sample_weights(
        dates[:1], as_of, seasons[:1],
        np.array([8]), np.array([8]), boosted)
    assert early[0] == pytest.approx(late[0] * 2.5)

    covid = sample_weights(
        dates[:1], as_of, np.array([4]),
        np.array([8]), np.array([8]), flat)
    regular = sample_weights(
        dates[:1], as_of, np.array([12]),
        np.array([8]), np.array([8]), flat)
    assert covid[0] == pytest.approx(regular[0] * 0.5)


def test_history_weight_downweights_the_older_season() -> None:
    as_of = np.datetime64("2025-10-15T00:00:00")
    dates = np.array([
        "2025-10-10T00:00:00",
        "2025-04-10T00:00:00"], dtype="datetime64[ns]")
    seasons = np.array([12, 11])
    games = np.array([20, 20])
    params = HockeyDixonColesParams(
        half_life_days=1.0e9,
        history_weight=0.25,
        early_season=EarlySeasonConfig(games=8, boost=1.0),
        low_weight_seasons={})
    weights = sample_weights(
        dates, as_of, seasons, games, games, params)
    assert weights[1] == pytest.approx(weights[0] * 0.25)


def test_shrink_matches_pulls_attack_toward_zero() -> None:
    home = np.array([0, 0, 1, 1] * 40)
    away = np.array([1, 1, 0, 0] * 40)
    home_goals = np.array([6, 6, 1, 1] * 40)
    away_goals = np.array([1, 1, 2, 2] * 40)
    weights = np.ones(len(home))
    plain = fit_dixon_coles(home, away, home_goals, away_goals, weights)
    shrunk = fit_dixon_coles(
        home, away, home_goals, away_goals, weights,
        shrink_matches=40.0)
    assert abs(shrunk[0][0]) < abs(plain[0][0])


def test_goalie_factor_shrinks_goals_against_a_better_starter() -> None:
    assert goalie_lambda_factor(0.93, 0.90) == pytest.approx(0.7)
    assert goalie_lambda_factor(0.90, 0.90) == pytest.approx(1.0)
    assert goalie_lambda_factor(None, 0.90) == 1.0
    assert goalie_lambda_factor(0.93, None) == 1.0
    assert goalie_lambda_factor(1.0, 0.90) == 1.0
    adjusted_home, adjusted_away = apply_goalie_correction(
        3.0, 2.5, 0.93, 0.90, 0.90, 0.90)
    assert adjusted_home == pytest.approx(3.0)
    assert adjusted_away == pytest.approx(1.75)


def test_score_distribution_uses_the_goalie_adjustment() -> None:
    model = HockeyRatingsModel(
        attack={1: 0.0, 2: 0.0},
        defense={1: math.log(3.0), 2: math.log(3.0)},
        home_adv=0.0,
        tie_inflation=1.15,
        p_ot_home=0.52,
        max_goals=8,
        mean_defense=math.log(3.0))
    base_home, base_away = model.base_lambdas(1, 2)
    adjusted_home, adjusted_away = apply_goalie_correction(
        base_home, base_away, 0.93, 0.90, 0.90, 0.90)
    distribution = model.score_distribution(
        1, 2, 0.93, 0.90, 0.90, 0.90)
    expected = build_score_distribution(
        adjusted_home, adjusted_away, 1.15, 0.52, max_goals=8)

    assert np.allclose(
        distribution.regulation_matrix, expected.regulation_matrix)


def test_fit_recovers_directed_scoring_rates() -> None:
    rng = np.random.default_rng(7)
    attack = {0: 0.30, 1: 0.0, 2: -0.30}
    defense = {0: math.log(2.7), 1: math.log(3.0), 2: math.log(3.2)}
    home_adv = 0.10
    home_team: list[int] = []
    away_team: list[int] = []
    home_goals: list[int] = []
    away_goals: list[int] = []
    for home in range(3):
        for away in range(3):
            if home == away:
                continue
            lambda_home = math.exp(
                home_adv + attack[home] + defense[away])
            lambda_away = math.exp(attack[away] + defense[home])
            for _ in range(100):
                home_team.append(home)
                away_team.append(away)
                home_goals.append(int(rng.poisson(lambda_home)))
                away_goals.append(int(rng.poisson(lambda_away)))
    fitted_attack, fitted_defense, fitted_adv = fit_dixon_coles(
        np.array(home_team),
        np.array(away_team),
        np.array(home_goals),
        np.array(away_goals),
        np.ones(len(home_team)))
    for home in range(3):
        for away in range(3):
            if home == away:
                continue
            expected_home = math.exp(
                home_adv + attack[home] + defense[away])
            expected_away = math.exp(attack[away] + defense[home])
            got_home = math.exp(
                fitted_adv + fitted_attack[home] + fitted_defense[away])
            got_away = math.exp(fitted_attack[away] + fitted_defense[home])
            assert got_home == pytest.approx(expected_home, abs=0.45)
            assert got_away == pytest.approx(expected_away, abs=0.45)


def test_zero_weight_match_does_not_move_the_fit() -> None:
    home = np.array([1, 1, 2, 2])
    away = np.array([2, 2, 1, 1])
    home_goals = np.array([3, 3, 2, 2])
    away_goals = np.array([2, 2, 3, 3])
    weights = np.ones(4)
    baseline = fit_dixon_coles(home, away, home_goals, away_goals, weights)
    ignored = fit_dixon_coles(
        np.append(home, 1),
        np.append(away, 2),
        np.append(home_goals, 15),
        np.append(away_goals, 0),
        np.append(weights, 0.0))
    assert ignored[2] == pytest.approx(baseline[2])
    assert ignored[0][1] == pytest.approx(baseline[0][1])
    assert ignored[1][2] == pytest.approx(baseline[1][2])


def test_season_games_reset_and_count_both_venues() -> None:
    frame = pd.DataFrame([
        _match(1, 10, 20, "2024-10-01", season=1),
        _match(2, 20, 10, "2024-10-03", season=1),
        _match(3, 10, 30, "2024-10-05", season=1),
        _match(4, 10, 20, "2025-10-01", season=2)])
    counted = attach_season_games_before(frame)

    assert counted.loc[0, "home_games_before"] == 0
    assert counted.loc[1, "home_games_before"] == 1
    assert counted.loc[1, "away_games_before"] == 1
    assert counted.loc[2, "home_games_before"] == 2
    assert counted.loc[3, "home_games_before"] == 0


def test_team_save_average_is_prior_and_decays() -> None:
    frame = pd.DataFrame([
        _match(1, 10, 20, "2025-01-01", home_save=0.90),
        _match(2, 10, 20, "2025-03-02", home_save=0.80),
        _match(3, 10, 20, "2025-05-01", home_save=0.70)])
    averaged = attach_team_save_average(frame, half_life_days=60.0)

    assert pd.isna(averaged.loc[0, "home_team_save_pct"])
    assert averaged.loc[1, "home_team_save_pct"] == pytest.approx(0.90)
    assert averaged.loc[2, "home_team_save_pct"] == pytest.approx(
        (0.90 * 0.5 + 0.80) / 1.5)


def test_later_matches_do_not_leak_into_an_as_of_fit() -> None:
    prior = [
        _training_row(index, 1, 2, "2024-11-01", 3, 2)
        for index in range(1, 21)]
    prior += [
        _training_row(index, 2, 1, "2024-11-02", 3, 2)
        for index in range(21, 41)]
    future = [
        _training_row(100, 1, 2, "2025-02-01", 12, 0)]
    frame = pd.DataFrame(prior + future)
    as_of = pd.Timestamp("2025-01-01")
    held_out = fit_model_as_of(frame, as_of, _flat_params())
    clean = fit_model_as_of(
        pd.DataFrame(prior), as_of, _flat_params())

    assert held_out.base_lambdas(1, 2) == pytest.approx(
        clean.base_lambdas(1, 2))


def test_ot_labels_and_home_ot_rate() -> None:
    regulation = label_hockey_goals({
        "home_team_goals": 4,
        "away_team_goals": 2,
        "ot_winner": 2,
        "so_winner": None})
    overtime = label_hockey_goals({
        "home_team_goals": 2,
        "away_team_goals": 2,
        "ot_winner": 1,
        "so_winner": None})
    shootout = label_hockey_goals({
        "home_team_goals": 1,
        "away_team_goals": 1,
        "ot_winner": 3,
        "so_winner": 2})
    assert regulation.ot_home_win is None
    assert overtime.ot_home_win == 1
    assert shootout.ot_home_win == 0
    rate = estimate_p_ot_home(
        np.array([2, 1, 3]),
        np.array([2, 1, 1]),
        np.array([1, 0, None], dtype=object))
    assert rate == pytest.approx(0.5)
    with pytest.raises(ValueError, match="Missing goal"):
        label_hockey_goals({
            "home_team_goals": None,
            "away_team_goals": 1})


def test_configs_load_and_components_register() -> None:
    training = load_model_config(TRAINING_CONFIG)
    prediction = load_model_config(PREDICTION_CONFIG)
    assert isinstance(training, FutureEventsRunConfig)
    assert training.model_name == "HOCKEY_RATINGS_POISSON_V1"
    assert training.trainer == "HockeyRatingsTrainer"
    assert training.labeler == "HockeyGoalsLabeler"
    assert training.max_goals == 12
    assert prediction.artifact_dir == training.artifact_dir
    params = hockey_params_from_config(training)
    assert params.test_season == 12
    assert params.low_weight_seasons[4] == pytest.approx(0.5)
    assert params.half_life_days == pytest.approx(1000.0)
    assert params.history_weight == pytest.approx(0.1)
    assert params.shrink_matches == pytest.approx(15.0)
    assert params.goalie_half_life_days == pytest.approx(180.0)
    assert params.early_season.boost == pytest.approx(1.0)
    assert get_trainer("HockeyRatingsTrainer").__class__.__name__ == (
        "HockeyRatingsTrainer")
    labeled = get_labeler("HockeyGoalsLabeler").label({
        "home_team_goals": 3,
        "away_team_goals": 3,
        "ot_winner": 3,
        "so_winner": 1})
    assert labeled.ot_home_win == 1


def _match(
        match_id: int,
        home_team: int,
        away_team: int,
        game_date: str,
        season: int = 1,
        home_save: float | None = None) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season": season,
        "game_date": pd.Timestamp(game_date),
        "home_team": home_team,
        "away_team": away_team,
        "home_goalie_save_pct": home_save,
        "away_goalie_save_pct": 0.9}


def _training_row(
        match_id: int,
        home_team: int,
        away_team: int,
        game_date: str,
        goals_home: int,
        goals_away: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season": 11,
        "game_date": pd.Timestamp(game_date),
        "home_team": home_team,
        "away_team": away_team,
        "goals_home": goals_home,
        "goals_away": goals_away,
        "ot_home_win": None,
        "home_games_before": 10,
        "away_games_before": 10,
        "home_goalie_save_pct": np.nan,
        "away_goalie_save_pct": np.nan,
        "home_team_save_pct": np.nan,
        "away_team_save_pct": np.nan}
