"""Rolling attack and defence strength ratings for football teams."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GapParams:
    """Configuration for GAP attack and defence updates."""

    initial_attack: float = 1.0
    initial_defence: float = 1.0
    learning_rate: float = 0.2


@dataclass
class GapRating:
    """Mutable attack and defence state for one team."""

    attack: float = 1.0
    defence: float = 1.0


def new_gap_rating(params: GapParams) -> GapRating:
    """Create a GAP state from configured priors."""
    return GapRating(params.initial_attack, params.initial_defence)


def update_gap(
        home: GapRating,
        away: GapRating,
        home_goals: int,
        away_goals: int,
        params: GapParams) -> tuple[GapRating, GapRating]:
    """Return updated attack and defence states after a match."""
    rate = params.learning_rate
    expected_home = max((home.attack + away.defence) / 2.0, 0.05)
    expected_away = max((away.attack + home.defence) / 2.0, 0.05)
    updated_home = GapRating(
        attack=max(home.attack + rate * (home_goals - expected_home), 0.0),
        defence=max(home.defence + rate * (away_goals - expected_away), 0.0))
    updated_away = GapRating(
        attack=max(away.attack + rate * (away_goals - expected_away), 0.0),
        defence=max(away.defence + rate * (home_goals - expected_home), 0.0))
    return updated_home, updated_away
