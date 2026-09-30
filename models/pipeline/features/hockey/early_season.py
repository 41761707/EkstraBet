"""Early-season sensitivity for hockey ratings."""

from __future__ import annotations

from dataclasses import dataclass


EARLY_SEASON_ALPHA_CAP = 0.5


@dataclass(frozen=True)
class EarlySeasonConfig:
    """How many games stay sensitive, and how strong the boost is.

    ``games`` is the count of matches already played after which the
    multiplier returns to 1. ``boost`` is ``M`` in the ramp below.
    """

    games: int = 8
    boost: float = 2.5


def early_season_multiplier(
        games_played: int,
        config: EarlySeasonConfig | None = None) -> float:
    """Return the sensitivity multiplier for a team or player.

    ``m(g) = 1 + (boost - 1) * (1 - g / games)`` while
    ``g < games``. From ``games`` played onward the result is 1.
    ``g`` is matches already finished, so the ninth game of a
    season is the first one at baseline when ``games`` is 8.
    """
    settings = config or EarlySeasonConfig()
    if games_played < 0:
        raise ValueError("games_played must be non-negative")
    if settings.games <= 0:
        raise ValueError("early_season.games must be positive")
    if games_played >= settings.games:
        return 1.0
    remaining = 1.0 - (games_played / settings.games)
    return 1.0 + (settings.boost - 1.0) * remaining


def early_season_alpha(
        alpha: float,
        games_played: int,
        config: EarlySeasonConfig | None = None) -> float:
    """Return an EWMA alpha boosted by the early-season multiplier.

    The product is capped at 0.5 so a strong boost cannot make the
    average forget almost all of the previous state.
    """
    boosted = alpha * early_season_multiplier(games_played, config)
    if boosted > EARLY_SEASON_ALPHA_CAP:
        return EARLY_SEASON_ALPHA_CAP
    return boosted
