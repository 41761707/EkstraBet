"""Hockey skater rating from ready-made box-score counters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


PRODUCTION_GOAL = 1.00
PRODUCTION_ASSIST = 1.00
EMPTY_NET_GOAL = -0.30
UNCONVERTED_SHOT = 0.05
TEAMMATE_GOAL = 0.20
FACEOFF_DIFF = 0.02
GOAL_AGAINST = -0.35
MINOR_PENALTY = -0.15
MAJOR_PENALTY = -0.30
BLOCK_ABOVE_AVERAGE = 0.04
DEFAULT_SAVE_RATE = 0.907
MIN_SEASON_SHOTS_AGAINST = 100

BLOCK_AVERAGE_DEFENSE = 1.44
BLOCK_AVERAGE_CENTER = 0.57
BLOCK_AVERAGE_LEFT_WING = 0.45
BLOCK_AVERAGE_RIGHT_WING = 0.46
BLOCK_AVERAGE_FORWARD = 0.49


@dataclass(frozen=True)
class SkaterCounts:
    """Ready-made counters. Even-strength points arrive already counted."""

    goals: int
    assists: int
    es_points: int
    empty_net_goals: int
    shots_on_goal: int
    plus_minus: int | None
    minor_penalties: int
    major_penalties: int
    blocked: int
    block_average: float
    faceoffs_taken: int
    faceoffs_won: int


@dataclass(frozen=True)
class RatingParts:
    """Nine rating leaves, each already rounded to one decimal."""

    production: Decimal
    empty_net: Decimal
    shots: Decimal
    teammate_goals: Decimal
    faceoffs: Decimal
    goals_against: Decimal
    penalties: Decimal
    blocks: Decimal
    goaltending: Decimal

    @property
    def offense(self) -> Decimal:
        """Sum the offensive leaves without rounding again."""
        return (self.production
            + self.empty_net
            + self.shots
            + self.teammate_goals
            + self.faceoffs)

    @property
    def defense(self) -> Decimal:
        """Sum the defensive leaves without rounding again."""
        return (self.goals_against
            + self.penalties
            + self.blocks
            + self.goaltending)

    @property
    def total(self) -> Decimal:
        """Sum offense and defense without rounding again."""
        return self.offense + self.defense


def _as_decimal(value: float) -> Decimal:
    """Use the decimal text of a float, so 0.15 stays 0.15."""
    return Decimal(str(value))


def _round_part(raw: Decimal) -> Decimal:
    """Round one rating leaf to a single decimal place."""
    # Iloczyn float psuje -1.05 i -0.45, więc surowiec jest Decimal.
    rounded = raw.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    # Ujemna waga razy zero zostawia -0.0, a protokół pokazuje 0.0.
    if rounded.is_zero():
        return Decimal("0.0")
    return rounded


def _on_ice_margin(counts: SkaterCounts) -> int | None:
    """Return plus/minus minus even-strength points, or None."""
    if counts.plus_minus is None:
        return None
    return counts.plus_minus - counts.es_points


def rate_skater(counts: SkaterCounts) -> RatingParts:
    """Turn ready-made skater counters into nine rounded parts.

    Goaltending stays zero. A missing plus/minus stays missing, so
    even-strength points are not treated as goals against.
    """
    margin = _on_ice_margin(counts)
    if margin is None:
        teammate_raw = Decimal("0")
        against_raw = Decimal("0")
    else:
        teammate_raw = _as_decimal(TEAMMATE_GOAL) * max(0, margin)
        against_raw = _as_decimal(GOAL_AGAINST) * max(0, -margin)
    faceoff_margin = (counts.faceoffs_won
        - (counts.faceoffs_taken - counts.faceoffs_won))
    unconverted_shots = max(0, counts.shots_on_goal - counts.goals)
    block_margin = counts.blocked - _as_decimal(counts.block_average)
    return RatingParts(
        production=_round_part(
            _as_decimal(PRODUCTION_GOAL) * counts.goals
            + _as_decimal(PRODUCTION_ASSIST) * counts.assists),
        empty_net=_round_part(
            _as_decimal(EMPTY_NET_GOAL) * counts.empty_net_goals),
        shots=_round_part(
            _as_decimal(UNCONVERTED_SHOT) * unconverted_shots),
        teammate_goals=_round_part(teammate_raw),
        faceoffs=_round_part(_as_decimal(FACEOFF_DIFF) * faceoff_margin),
        goals_against=_round_part(against_raw),
        penalties=_round_part(
            _as_decimal(MINOR_PENALTY) * counts.minor_penalties
            + _as_decimal(MAJOR_PENALTY) * counts.major_penalties),
        blocks=_round_part(_as_decimal(BLOCK_ABOVE_AVERAGE) * block_margin),
        goaltending=_round_part(Decimal("0")))
