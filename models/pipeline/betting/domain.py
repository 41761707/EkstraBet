"""Domain contracts for choosing one existing prediction-odds pair."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


DecisionKind = Literal["bet", "no_bet"]
_DECISIONS = ("bet", "no_bet")
_FINGERPRINT_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def _require_positive_id(name: str, value: int) -> None:
    """Reject ids that cannot point at an existing database row."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _require_optional_positive_id(name: str, value: int | None) -> None:
    """Allow a missing league and reject every other non-positive id."""
    if value is None:
        return
    _require_positive_id(name, value)


def _require_unit_interval(name: str, value: float) -> None:
    """Reject probabilities outside the closed unit interval."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0.0
            or value > 1.0):
        raise ValueError(f"{name} must be between 0 and 1")


def _require_model_fingerprint(value: str) -> None:
    """Reject anything other than a 64-character SHA-256 hex digest."""
    if (
            not isinstance(value, str)
            or _FINGERPRINT_HEX.fullmatch(value) is None):
        raise ValueError(
            "model_fingerprint must be a 64-character SHA-256 hex string")


@dataclass(frozen=True)
class BettingCandidate:
    """One stored prediction joined to one stored odds row.

    ``value_pct`` is the stored probability on a 0-100 scale.
    ``odds`` is the bookmaker price. ``league_id`` is ``matches.league``
    and may be missing. Values stay in the source rows.
    """

    prediction_id: int
    odds_id: int
    match_id: int
    event_id: int
    model_id: int
    bookmaker_id: int
    league_id: int | None
    kickoff: datetime
    value_pct: float
    odds: float

    def __post_init__(self) -> None:
        _require_positive_id("prediction_id", self.prediction_id)
        _require_positive_id("odds_id", self.odds_id)
        _require_positive_id("match_id", self.match_id)
        _require_positive_id("event_id", self.event_id)
        _require_positive_id("model_id", self.model_id)
        _require_positive_id("bookmaker_id", self.bookmaker_id)
        _require_optional_positive_id("league_id", self.league_id)
        if not isinstance(self.kickoff, datetime):
            raise ValueError("kickoff must be a datetime")
        if (
                isinstance(self.value_pct, bool)
                or not isinstance(self.value_pct, (int, float))
                or not math.isfinite(self.value_pct)
                or self.value_pct < 0.0
                or self.value_pct > 100.0):
            raise ValueError("value_pct must be between 0 and 100")
        if (
                isinstance(self.odds, bool)
                or not isinstance(self.odds, (int, float))
                or not math.isfinite(self.odds)
                or self.odds <= 1.0):
            raise ValueError("odds must be greater than 1")


@dataclass(frozen=True)
class SelectionDecision:
    """Bet or no-bet for one candidate.

    The decision carries the calibrated probability and a reason. It does
    not carry a stake.
    """

    decision: DecisionKind
    candidate: BettingCandidate
    calibrated_probability: float
    reason: str

    def __post_init__(self) -> None:
        if self.decision not in _DECISIONS:
            raise ValueError("decision must be 'bet' or 'no_bet'")
        if not isinstance(self.candidate, BettingCandidate):
            raise ValueError("candidate must be a BettingCandidate")
        _require_unit_interval(
            "calibrated_probability",
            self.calibrated_probability)
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty")


@dataclass(frozen=True)
class BettingRecommendation:
    """One verdict for a stored prediction-odds pair and model file.

    The row points at existing ``predictions`` and ``odds`` ids. It does
    not copy the base-model percentage or the bookmaker price.
    """

    prediction_id: int
    odds_id: int
    decision: DecisionKind
    calibrated_probability: float
    model_fingerprint: str

    def __post_init__(self) -> None:
        _require_positive_id("prediction_id", self.prediction_id)
        _require_positive_id("odds_id", self.odds_id)
        if self.decision not in _DECISIONS:
            raise ValueError("decision must be 'bet' or 'no_bet'")
        _require_unit_interval(
            "calibrated_probability",
            self.calibrated_probability)
        _require_model_fingerprint(self.model_fingerprint)
