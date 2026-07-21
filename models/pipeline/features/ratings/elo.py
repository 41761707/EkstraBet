"""Leakage-safe Elo rating calculations for football matches."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EloParams:
    """Configuration for football Elo updates."""

    initial_rating: float = 1500.0
    k_factor: float = 32.0
    home_advantage: float = 80.0
    second_tier_coefficient: float = 0.9


def initial_elo(tier: int | None, params: EloParams) -> float:
    """Return an initial rating adjusted for second-tier competitions."""
    if tier == 2:
        return params.initial_rating * params.second_tier_coefficient
    return params.initial_rating


def expected_home_score(
        home_rating: float,
        away_rating: float,
        home_advantage: float = 80.0) -> float:
    """Return the expected home score on the Elo logistic scale."""
    exponent = (away_rating - home_rating - home_advantage) / 400.0
    return 1.0 / (1.0 + 10.0 ** exponent)


def goal_difference_multiplier(goal_difference: int) -> float:
    """Return a smooth multiplier that rewards decisive results."""
    difference = abs(goal_difference)
    if difference <= 1:
        return 1.0
    if difference == 2:
        return 1.5
    if difference == 3:
        return 1.75
    return 1.75 + (difference - 3) / 8.0


def update_elo(
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
        params: EloParams) -> tuple[float, float]:
    """Return post-match Elo values for both teams."""
    expected_home = expected_home_score(
        home_rating, away_rating, params.home_advantage)
    if home_goals > away_goals:
        actual_home = 1.0
    elif home_goals < away_goals:
        actual_home = 0.0
    else:
        actual_home = 0.5
    multiplier = goal_difference_multiplier(home_goals - away_goals)
    adjustment = params.k_factor * multiplier * (
        actual_home - expected_home)
    return home_rating + adjustment, away_rating - adjustment
