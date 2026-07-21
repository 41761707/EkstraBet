"""Venue-specific rolling football form known as Czech rating."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field

import numpy as np


@dataclass(frozen=True)
class CzechParams:
    """Configuration for venue-specific rolling form."""

    window: int = 8


@dataclass
class VenueResult:
    """A historical result from one team's perspective."""

    won: float
    goals_for: float
    goals_against: float


@dataclass
class CzechRating:
    """Mutable home and away form windows for one team."""

    home: deque[VenueResult] = field(default_factory=deque)
    away: deque[VenueResult] = field(default_factory=deque)


def new_czech_rating(params: CzechParams) -> CzechRating:
    """Create empty venue windows using the configured maximum length."""
    return CzechRating(
        home=deque(maxlen=params.window),
        away=deque(maxlen=params.window))


def venue_snapshot(
        rating: CzechRating,
        venue: str) -> dict[str, float]:
    """Return stable rolling statistics for a venue."""
    results = rating.home if venue == "home" else rating.away
    if not results:
        return {
            "win_pct": 0.0,
            "goals_for_avg": 0.0,
            "goals_against_avg": 0.0,
            "goals_for_std": 0.0,
            "goals_against_std": 0.0
        }
    goals_for = np.array([result.goals_for for result in results])
    goals_against = np.array([
        result.goals_against for result in results])
    return {
        "win_pct": float(np.mean([result.won for result in results])),
        "goals_for_avg": float(goals_for.mean()),
        "goals_against_avg": float(goals_against.mean()),
        "goals_for_std": float(goals_for.std()),
        "goals_against_std": float(goals_against.std())
    }


def update_czech(
        home: CzechRating,
        away: CzechRating,
        home_goals: int,
        away_goals: int) -> None:
    """Update both team windows in place after a finished match."""
    home.home.append(VenueResult(
        won=float(home_goals > away_goals),
        goals_for=float(home_goals),
        goals_against=float(away_goals)))
    away.away.append(VenueResult(
        won=float(away_goals > home_goals),
        goals_for=float(away_goals),
        goals_against=float(home_goals)))
