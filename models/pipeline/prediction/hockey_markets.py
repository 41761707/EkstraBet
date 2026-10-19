"""Regulation and final-score matrices for NHL team markets.

Lambdas are regulation goal rates. Ties on that grid are inflated,
then each tie is given to the overtime or shootout winner as one
extra goal. Every market below is read from that final grid, so
moneyline, totals and puck line stay consistent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


DEFAULT_MAX_GOALS = 12

HOCKEY_MARKET_KEYS = (
    "ml_home",
    "ml_away",
    "over_55",
    "under_55",
    "over_65",
    "under_65",
    "pl_home_minus_15",
    "pl_home_plus_15",
    "pl_away_minus_15",
    "pl_away_plus_15",
    "home_over_25",
    "home_under_25",
    "home_over_35",
    "home_under_35",
    "away_over_25",
    "away_under_25",
    "away_over_35",
    "away_under_35")

# Pary komplementarne: home -1.5 gra przeciwko away +1.5.
HOCKEY_MARKET_FAMILIES: dict[str, list[str]] = {
    "HOCKEY_ML": ["ml_home", "ml_away"],
    "HOCKEY_OU_55": ["over_55", "under_55"],
    "HOCKEY_OU_65": ["over_65", "under_65"],
    "HOCKEY_PL_HOME": ["pl_home_minus_15", "pl_away_plus_15"],
    "HOCKEY_PL_AWAY": ["pl_away_minus_15", "pl_home_plus_15"],
    "HOCKEY_HOME_TT_25": ["home_over_25", "home_under_25"],
    "HOCKEY_HOME_TT_35": ["home_over_35", "home_under_35"],
    "HOCKEY_AWAY_TT_25": ["away_over_25", "away_under_25"],
    "HOCKEY_AWAY_TT_35": ["away_over_35", "away_under_35"]}

HOCKEY_HOME_BUCKET_KEYS = ("0", "1", "2", "3", "4", "5+")
HOCKEY_TOTAL_BUCKET_KEYS = ("3-", "4", "5", "6", "7", "8+")
EXACT_SCORE_MAX_GOALS = 7
EXACT_SCORE_LIMIT = 5
EXACT_SCORE_BASE_ID = 270
EXACT_SCORE_LAST_ID = (
    EXACT_SCORE_BASE_ID
    + EXACT_SCORE_MAX_GOALS * (EXACT_SCORE_MAX_GOALS + 1)
    + EXACT_SCORE_MAX_GOALS)


@dataclass(frozen=True)
class HockeyScoreDistribution:
    """Regulation grid, final grid after overtime, and P(home in OT).

    Both matrices are indexed ``[home_goals, away_goals]`` and include
    scores ``0`` through ``max_goals``. A regulation tie at the last
    row is folded onto the neighbouring cells so the final grid keeps
    the same shape.
    """

    regulation_matrix: np.ndarray
    final_matrix: np.ndarray
    p_ot_home: float


def build_score_distribution(
        lambda_home: float,
        lambda_away: float,
        tie_inflation: float,
        p_ot_home: float,
        max_goals: int = DEFAULT_MAX_GOALS) -> HockeyScoreDistribution:
    """Build a renormalized score grid and move ties to an OT winner.

    ``tie_inflation`` multiplies the regulation diagonal before the
    grid is scaled back to 1. ``1`` leaves an independent Poisson.
    Each tie ``(i, i)`` then moves to ``(i+1, i)`` with weight
    ``p_ot_home`` and to ``(i, i+1)`` with the rest.
    """
    _validate_distribution_args(
        lambda_home, lambda_away, tie_inflation, p_ot_home, max_goals)
    home = _poisson_pmf(float(lambda_home), max_goals)
    away = _poisson_pmf(float(lambda_away), max_goals)
    regulation = np.outer(home, away)
    diagonal = np.arange(max_goals + 1)
    regulation[diagonal, diagonal] *= float(tie_inflation)
    regulation = _normalize(regulation)
    final = _final_matrix(regulation, float(p_ot_home))
    return HockeyScoreDistribution(
        regulation_matrix=regulation,
        final_matrix=final,
        p_ot_home=float(p_ot_home))


def derive_hockey_markets(
        distribution: HockeyScoreDistribution) -> dict[str, float]:
    """Return final-score market probabilities on a 0-100 scale.

    Comparisons match settlement: a half-goal line wins on a strict
    inequality, so integer scores never push.
    """
    matrix = _validated_probability_matrix(distribution.final_matrix)
    home, away = _goal_grids(matrix.shape[0])
    home_margin = home - away
    away_margin = away - home
    total = home + away
    return {
        "ml_home": _percent(matrix, home_margin > 0),
        "ml_away": _percent(matrix, away_margin > 0),
        "over_55": _percent(matrix, total > 5.5),
        "under_55": _percent(matrix, total < 5.5),
        "over_65": _percent(matrix, total > 6.5),
        "under_65": _percent(matrix, total < 6.5),
        "pl_home_minus_15": _percent(matrix, home_margin > 1.5),
        "pl_home_plus_15": _percent(matrix, home_margin > -1.5),
        "pl_away_minus_15": _percent(matrix, away_margin > 1.5),
        "pl_away_plus_15": _percent(matrix, away_margin > -1.5),
        "home_over_25": _percent(matrix, home > 2.5),
        "home_under_25": _percent(matrix, home < 2.5),
        "home_over_35": _percent(matrix, home > 3.5),
        "home_under_35": _percent(matrix, home < 3.5),
        "away_over_25": _percent(matrix, away > 2.5),
        "away_under_25": _percent(matrix, away < 2.5),
        "away_over_35": _percent(matrix, away > 3.5),
        "away_under_35": _percent(matrix, away < 3.5)}


@dataclass(frozen=True)
class HockeyScoreChart:
    """Goal buckets and the five likeliest final scores.

    Club keys follow ``HOCKEY_HOME_BUCKET_KEYS``. Match keys follow
    ``HOCKEY_TOTAL_BUCKET_KEYS``. Every value is a percent from 0
    to 100, on the same scale as the market lines.
    """

    home_buckets: dict[str, float]
    away_buckets: dict[str, float]
    total_buckets: dict[str, float]
    exact_scores: tuple[tuple[str, float], ...]


def exact_score_event_id(home_goals: int, away_goals: int) -> int:
    """Return the catalog id for one final score.

    Ids run from 270 as ``270 + home * 8 + away`` while both sides
    stay between 0 and 7 goals.
    """
    if not _is_catalog_score(home_goals, away_goals):
        raise ValueError(
            "Exact score must use 0 through "
            f"{EXACT_SCORE_MAX_GOALS} goals on each side")
    return (
        EXACT_SCORE_BASE_ID
        + home_goals * (EXACT_SCORE_MAX_GOALS + 1)
        + away_goals)


def derive_hockey_score_chart(
        distribution: HockeyScoreDistribution) -> HockeyScoreChart:
    """Return goal buckets and the five likeliest final scores.

    The regulation grid is ignored. Overtime has already moved each
    tie onto the winner, so a draw cannot appear in the five.
    """
    matrix = _validated_probability_matrix(distribution.final_matrix)
    return HockeyScoreChart(
        home_buckets=_team_goal_buckets(matrix.sum(axis=1)),
        away_buckets=_team_goal_buckets(matrix.sum(axis=0)),
        total_buckets=_total_goal_buckets(matrix),
        exact_scores=_top_exact_scores(matrix))


def select_hockey_finals(
        market_probs: dict[str, float],
        families: dict[str, list[str]]) -> list[str]:
    """Pick the higher probability in each binary market family.

    Equal probabilities keep the first key listed for that family.
    """
    selected: list[str] = []
    for family, keys in families.items():
        if len(keys) < 2:
            raise ValueError(
                f"Family {family} needs at least two markets")
        missing = [key for key in keys if key not in market_probs]
        if missing:
            raise KeyError(
                f"Missing market probabilities: {missing}")
        selected.append(max(
            keys, key=lambda key: float(market_probs[key])))
    return selected


def _validate_distribution_args(
        lambda_home: float,
        lambda_away: float,
        tie_inflation: float,
        p_ot_home: float,
        max_goals: int) -> None:
    if max_goals < 1:
        raise ValueError("max_goals must be at least 1")
    for name, value in (
            ("lambda_home", lambda_home),
            ("lambda_away", lambda_away)):
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be a finite non-negative rate")
    if not np.isfinite(tie_inflation) or tie_inflation <= 0.0:
        raise ValueError("tie_inflation must be a finite positive number")
    if not np.isfinite(p_ot_home) or not 0.0 <= p_ot_home <= 1.0:
        raise ValueError("p_ot_home must be between 0 and 1")


def _poisson_pmf(rate: float, max_goals: int) -> np.ndarray:
    """Return Poisson probabilities for scores 0 through max_goals."""
    if rate == 0.0:
        masses = np.zeros(max_goals + 1, dtype=float)
        masses[0] = 1.0
        return masses
    goals = np.arange(max_goals + 1, dtype=float)
    log_factorial = np.zeros(max_goals + 1, dtype=float)
    log_factorial[1:] = np.cumsum(np.log(goals[1:]))
    log_mass = -rate + goals * np.log(rate) - log_factorial
    return np.exp(log_mass)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    total = float(matrix.sum())
    if total <= 0.0 or not np.isfinite(total):
        raise ValueError("Score matrix could not be normalized")
    return matrix / total


def _final_matrix(
        regulation: np.ndarray,
        p_ot_home: float) -> np.ndarray:
    """Move every regulation tie onto the overtime winner."""
    final = regulation.copy()
    size = final.shape[0]
    ties = np.diag(final).copy()
    np.fill_diagonal(final, 0.0)
    if size < 2:
        return final
    movable = np.arange(size - 1)
    final[movable + 1, movable] += ties[movable] * p_ot_home
    final[movable, movable + 1] += ties[movable] * (1.0 - p_ot_home)
    # 12:12 nie mieści się jako 13 goli; masa idzie na krawędź siatki.
    final[size - 1, size - 2] += ties[size - 1] * p_ot_home
    final[size - 2, size - 1] += ties[size - 1] * (1.0 - p_ot_home)
    return final


def _goal_grids(size: int) -> tuple[np.ndarray, np.ndarray]:
    """Return home and away goal indexes broadcast to the full grid."""
    goals = np.arange(size)
    home = np.repeat(goals[:, None], size, axis=1)
    away = np.repeat(goals[None, :], size, axis=0)
    return home, away


def _validated_probability_matrix(matrix: np.ndarray) -> np.ndarray:
    grid = np.asarray(matrix, dtype=float)
    if grid.ndim != 2 or grid.shape[0] != grid.shape[1]:
        raise ValueError("Score matrix must be square")
    if grid.shape[0] < 2:
        raise ValueError("Score matrix must cover at least 0 and 1 goal")
    if np.any(grid < 0.0) or not np.all(np.isfinite(grid)):
        raise ValueError("Score matrix must be finite and non-negative")
    if not np.isclose(float(grid.sum()), 1.0, atol=1e-8):
        raise ValueError("Score matrix must sum to one")
    return grid


def _percent(matrix: np.ndarray, mask: np.ndarray) -> float:
    return 100.0 * float(matrix[mask].sum())


def _is_catalog_score(home_goals: int, away_goals: int) -> bool:
    return (
        _in_exact_catalog(home_goals)
        and _in_exact_catalog(away_goals))


def _in_exact_catalog(goals: int) -> bool:
    if isinstance(goals, bool) or not isinstance(goals, int):
        return False
    return 0 <= goals <= EXACT_SCORE_MAX_GOALS


def _team_goal_buckets(margin: np.ndarray) -> dict[str, float]:
    """Collapse one club's margin into 0-4 and a 5+ tail."""
    buckets = {
        key: _margin_percent(margin, int(key))
        for key in HOCKEY_HOME_BUCKET_KEYS
        if key != "5+"}
    # 5+ to cała reszta siatki, aż do max_goals (domyślnie 12).
    buckets["5+"] = 100.0 * float(margin[5:].sum())
    return buckets


def _margin_percent(margin: np.ndarray, index: int) -> float:
    if index >= int(margin.shape[0]):
        return 0.0
    return 100.0 * float(margin[index])


def _total_goal_buckets(matrix: np.ndarray) -> dict[str, float]:
    """Collapse the match total into <=3, 4-7 and an 8+ tail."""
    size = int(matrix.shape[0])
    home = np.arange(size)[:, None]
    away = np.arange(size)[None, :]
    total = home + away
    return {
        "3-": _percent(matrix, total <= 3),
        "4": _percent(matrix, total == 4),
        "5": _percent(matrix, total == 5),
        "6": _percent(matrix, total == 6),
        "7": _percent(matrix, total == 7),
        "8+": _percent(matrix, total >= 8)}


def _top_exact_scores(
        matrix: np.ndarray) -> tuple[tuple[str, float], ...]:
    """Five likeliest non-tie scores inside the 0-7 catalog."""
    limit = min(EXACT_SCORE_MAX_GOALS + 1, int(matrix.shape[0]))
    ranked = _catalog_cells(matrix, limit)
    ranked.sort()
    chosen = ranked[:EXACT_SCORE_LIMIT]
    return tuple(
        (f"{home}:{away}", 100.0 * (-negative_mass))
        for negative_mass, home, away in chosen)


def _catalog_cells(
        matrix: np.ndarray,
        limit: int) -> list[tuple[float, int, int]]:
    """Sort key is negative mass, then lower home, then lower away."""
    cells: list[tuple[float, int, int]] = []
    for home in range(limit):
        for away in range(limit):
            # Remis nie jest wynikiem końcowym: dogrywka już dodała gola.
            if home == away:
                continue
            cells.append((-float(matrix[home, away]), home, away))
    return cells
