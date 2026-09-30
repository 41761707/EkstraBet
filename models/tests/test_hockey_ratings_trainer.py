"""Synthetic checks for the NHL attack-defense baseline."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

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
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.training.hockey_ratings_trainer import (
    HockeyDixonColesParams)
from models.pipeline.training.hockey_ratings_trainer import HockeyRatingsModel
from models.pipeline.training.hockey_ratings_trainer import (
    apply_goalie_correction)
from models.pipeline.training.hockey_ratings_trainer import (
    attach_season_games_before)
from models.pipeline.training.hockey_ratings_trainer import (
    attach_team_save_average)
from models.pipeline.training.hockey_ratings_trainer import (
    latest_team_save_rates)
from models.pipeline.training.hockey_ratings_trainer import estimate_p_ot_home
from models.pipeline.training.hockey_ratings_trainer import fit_dixon_coles
from models.pipeline.training.hockey_ratings_trainer import (
    _accept_lineup_adjustment)
from models.pipeline.training.hockey_ratings_trainer import (
    _betas_before_test_season)
from models.pipeline.training.hockey_ratings_trainer import (
    _metrics_from_rows)
from models.pipeline.training.hockey_ratings_trainer import _score_one
from models.pipeline.training.hockey_ratings_trainer import (
    calibrate_tie_inflation)
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
    before_third = (0.90 * 0.5 + 0.80) / 1.5
    assert averaged.loc[2, "home_team_save_pct"] == pytest.approx(before_third)
    # Po trzecim starcie średnia jest już gotowa na następny mecz.
    carried = latest_team_save_rates(frame, half_life_days=60.0)
    next_rate = (before_third * 0.75 + 0.70) / 1.75
    assert carried[10] == pytest.approx(next_rate)
    assert carried[20] == pytest.approx(0.9)


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
    assert held_out.beta_off == 0.0
    assert held_out.beta_def == 0.0


def test_betas_before_the_test_season_use_the_last_played_matches(
        monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[pd.DataFrame] = []

    def _capture(validation, *_args, **_kwargs):
        seen.append(validation)
        return 0.0, 0.0

    monkeypatch.setattr(
        "models.pipeline.training.hockey_ratings_trainer."
        "_fit_lineup_betas",
        _capture)
    rows = []
    for index in range(1, 11):
        day = pd.Timestamp("2024-06-01") + pd.Timedelta(days=index)
        rows.append(_training_row(index, 1, 2, str(day.date()), 3, 2))
    opener = _training_row(99, 1, 2, "2025-10-05", 2, 1)
    opener["season"] = 12
    frame = pd.DataFrame(rows + [opener])
    params = replace(_flat_params(), validation_days=3)
    assert _betas_before_test_season(frame, params) == (0.0, 0.0)
    assert len(seen) == 1
    assert set(seen[0]["match_id"]) == {8, 9, 10}
    assert seen[0]["game_date"].max() < pd.Timestamp("2025-10-05")


def test_plain_variant_keeps_inflation_from_before_the_lineup() -> None:
    model = HockeyRatingsModel(
        attack={1: 0.0, 2: 0.0},
        defense={1: 0.0, 2: 0.0},
        home_adv=0.1,
        tie_inflation=1.8,
        p_ot_home=0.55,
        max_goals=8,
        mean_defense=0.0,
        beta_off=1.0,
        beta_def=0.5)
    plain = replace(model, beta_off=0.0, beta_def=0.0, tie_inflation=1.0)
    leaked = replace(model, beta_off=0.0, beta_def=0.0)
    record = _score_record()
    row = _score_one(model, record, _naive(), plain)
    assert row is not None
    fair = _markets_of(plain)
    stale = _markets_of(leaked)
    assert row["p_home_without_lineup"] == pytest.approx(
        fair["ml_home"] / 100.0)
    assert row["p_over_without_lineup"] == pytest.approx(
        fair["over_55"] / 100.0)
    assert row["p_puck_without_lineup"] == pytest.approx(
        fair["pl_home_minus_15"] / 100.0)
    assert fair["ml_home"] != pytest.approx(stale["ml_home"])


def test_rejected_lineup_metrics_follow_the_plain_variant() -> None:
    rows = [_market_row(
        y_home=1.0,
        p_home=0.9,
        p_home_without=0.6,
        y_over=1.0,
        p_over=0.2,
        p_over_without=0.8,
        y_puck=1.0,
        p_puck=0.75,
        p_puck_without=0.6)]
    metrics = _metrics_from_rows(
        rows,
        0,
        [1.8, 2.0],
        [1.1, 1.3],
        pd.DataFrame({"season": [11]}),
        _flat_params())
    assert metrics["lineup_adjustment_improves_log_loss"] is True
    assert metrics["lineup_adjustment_kept"] is False
    assert metrics["moneyline_log_loss"] == pytest.approx(-math.log(0.6))
    assert metrics["over_55_log_loss"] == pytest.approx(-math.log(0.8))
    assert metrics["puck_line_home_minus_15_log_loss"] == pytest.approx(
        -math.log(0.6))
    _assert_both_lineup_losses(
        metrics,
        "moneyline_log_loss",
        -math.log(0.9),
        -math.log(0.6))
    _assert_both_lineup_losses(
        metrics,
        "over_55_log_loss",
        -math.log(0.2),
        -math.log(0.8))
    _assert_both_lineup_losses(
        metrics,
        "puck_line_home_minus_15_log_loss",
        -math.log(0.75),
        -math.log(0.6))
    assert metrics["beats_naive_moneyline"] is True
    assert metrics["moneyline_brier"] == pytest.approx((0.6 - 1.0) ** 2)
    assert metrics["holdout_tie_inflation_mean"] == pytest.approx(1.2)


def test_kept_lineup_metrics_follow_the_adjusted_variant() -> None:
    rows = [_market_row(
        y_home=1.0,
        p_home=0.8,
        p_home_without=0.55,
        y_over=1.0,
        p_over=0.7,
        p_over_without=0.6,
        y_puck=1.0,
        p_puck=0.66,
        p_puck_without=0.6)]
    metrics = _metrics_from_rows(
        rows,
        0,
        [1.8, 2.0],
        [1.1, 1.3],
        pd.DataFrame({"season": [11]}),
        _flat_params())
    assert metrics["lineup_adjustment_kept"] is True
    assert metrics["moneyline_log_loss"] == pytest.approx(-math.log(0.8))
    assert metrics["over_55_log_loss"] == pytest.approx(-math.log(0.7))
    assert metrics["puck_line_home_minus_15_log_loss"] == pytest.approx(
        -math.log(0.66))
    _assert_both_lineup_losses(
        metrics,
        "moneyline_log_loss",
        -math.log(0.8),
        -math.log(0.55))
    _assert_both_lineup_losses(
        metrics,
        "over_55_log_loss",
        -math.log(0.7),
        -math.log(0.6))
    _assert_both_lineup_losses(
        metrics,
        "puck_line_home_minus_15_log_loss",
        -math.log(0.66),
        -math.log(0.6))
    assert metrics["holdout_tie_inflation_mean"] == pytest.approx(1.9)


def _assert_both_lineup_losses(
        metrics: dict[str, float],
        headline: str,
        with_lineup: float,
        without_lineup: float) -> None:
    assert metrics[f"{headline}_with_lineup"] == pytest.approx(with_lineup)
    assert metrics[f"{headline}_without_lineup"] == pytest.approx(
        without_lineup)
    assert metrics[f"{headline}_with_lineup"] != pytest.approx(
        metrics[f"{headline}_without_lineup"])


def test_lineup_correction_is_kept_only_when_totals_hold() -> None:
    assert _accept_lineup_adjustment(True, 0.4, 0.5, 0.4, 0.4) is True
    assert _accept_lineup_adjustment(True, 0.5, 0.5, 0.6, 0.6) is True
    assert _accept_lineup_adjustment(False, 0.4, 0.5, 0.4, 0.5) is False
    assert _accept_lineup_adjustment(True, 0.51, 0.5, 0.4, 0.5) is False
    assert _accept_lineup_adjustment(True, 0.4, 0.5, 0.61, 0.6) is False


def test_forced_betas_without_ratios_keep_the_tie_inflation() -> None:
    frame = _prior_frame()
    as_of = pd.Timestamp("2025-01-01")
    params = _flat_params()
    plain = fit_model_as_of(frame, as_of, params)
    zeros = fit_model_as_of(
        frame, as_of, params, lineup_betas=(0.0, 0.0))
    forced = fit_model_as_of(
        frame, as_of, params, lineup_betas=(1.0, 1.0))
    assert zeros.tie_inflation == pytest.approx(plain.tie_inflation)
    assert forced.tie_inflation == pytest.approx(plain.tie_inflation)
    assert zeros.beta_off == 0.0
    assert zeros.beta_def == 0.0
    assert forced.beta_off == 1.0
    assert forced.beta_def == 1.0


def test_nonzero_betas_refit_tie_inflation_on_adjusted_rates(
        monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _prior_frame()
    frame["home_lineup_off_ratio"] = 2.0
    frame["away_lineup_off_ratio"] = 2.0
    frame["home_lineup_def_ratio"] = 1.0
    frame["away_lineup_def_ratio"] = 1.0
    frame["final_home_win"] = 1.0
    calls: list[float] = []
    real = calibrate_tie_inflation

    def _record(*args, **kwargs):
        value = real(*args, **kwargs)
        calls.append(value)
        return value

    monkeypatch.setattr(
        "models.pipeline.training.hockey_ratings_trainer."
        "calibrate_tie_inflation",
        _record)
    as_of = pd.Timestamp("2025-01-01")
    model = fit_model_as_of(
        frame, as_of, _flat_params(), lineup_betas=(1.0, 0.0))
    assert model.beta_off == 1.0
    assert len(calls) == 2
    assert model.tie_inflation == pytest.approx(calls[1])


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
    assert params.lineup_baseline_games == 10
    assert params.lineup_beta_off_grid[0] == pytest.approx(0.0)
    assert params.lineup_beta_off_grid[-1] == pytest.approx(2.0)
    assert params.lineup_beta_def_grid == params.lineup_beta_off_grid
    assert params.early_season.boost == pytest.approx(1.0)
    assert get_trainer("HockeyRatingsTrainer").__class__.__name__ == (
        "HockeyRatingsTrainer")
    labeled = get_labeler("HockeyGoalsLabeler").label({
        "home_team_goals": 3,
        "away_team_goals": 3,
        "ot_winner": 3,
        "so_winner": 1})
    assert labeled.ot_home_win == 1


def _naive() -> dict[str, float]:
    return {"home": 0.5, "over": 0.5, "puck": 0.5}


def _score_record() -> SimpleNamespace:
    return SimpleNamespace(
        final_home_win=1,
        home_team=1,
        away_team=2,
        home_goalie_save_pct=None,
        away_goalie_save_pct=None,
        home_team_save_pct=None,
        away_team_save_pct=None,
        final_home_goals=4,
        final_away_goals=2,
        home_lineup_off_ratio=1.3,
        away_lineup_off_ratio=0.8,
        home_lineup_def_ratio=1.1,
        away_lineup_def_ratio=0.9)


def _markets_of(model: HockeyRatingsModel) -> dict[str, float]:
    return derive_hockey_markets(model.score_distribution(
        1,
        2,
        home_off_ratio=1.3,
        away_off_ratio=0.8,
        home_def_ratio=1.1,
        away_def_ratio=0.9))


def _market_row(
        y_home: float,
        p_home: float,
        p_home_without: float,
        y_over: float,
        p_over: float,
        p_over_without: float,
        y_puck: float,
        p_puck: float,
        p_puck_without: float) -> dict[str, float]:
    return {
        "y_home": y_home,
        "p_home": p_home,
        "p_home_without_lineup": p_home_without,
        "beta_off": 1.0,
        "beta_def": 0.5,
        "p_naive_home": 0.5,
        "y_over": y_over,
        "p_over": p_over,
        "p_over_without_lineup": p_over_without,
        "p_naive_over": 0.5,
        "y_puck": y_puck,
        "p_puck": p_puck,
        "p_puck_without_lineup": p_puck_without,
        "p_naive_puck": 0.5}


def _prior_frame() -> pd.DataFrame:
    prior = [
        _training_row(index, 1, 2, "2024-11-01", 3, 2)
        for index in range(1, 21)]
    prior += [
        _training_row(index, 2, 1, "2024-11-02", 3, 2)
        for index in range(21, 41)]
    return pd.DataFrame(prior)


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
