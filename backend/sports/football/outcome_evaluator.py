"""Domain rules for settling football prediction and bet outcomes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


SettlementTarget = Literal["final_prediction", "bet"]
# Wartości zgodne z event_families.name w DB (bez mapowania DB→domena).
EventFamily = Literal["REZULTAT", "BTTS", "OU", "GOALS", "EXACT"]

VALID_MATCH_RESULTS = frozenset({"1", "X", "2"})
BET_MARKET_EVENT_IDS = frozenset({1, 2, 3, 6, 8, 12, 172})

RESULT_EVENT_OUTCOMES = {
    1: "1",
    2: "X",
    3: "2"
}
BTTS_YES_EVENT_IDS = frozenset({6})
BTTS_NO_EVENT_IDS = frozenset({172})
OVER_25_EVENT_IDS = frozenset({8})
UNDER_25_EVENT_IDS = frozenset({12})
GOALS_EXACT_TOTAL_EVENTS = {
    174: 0,
    175: 1,
    176: 2,
    177: 3,
    178: 4,
    179: 5
}
GOALS_6_PLUS_EVENT_ID = 180
EXACT_SCORE_PATTERN = re.compile(
    r"^(?P<home>0|1|2|3|4|5\+):(?P<away>0|1|2|3|4|5\+)$")


class UnsupportedFootballEventError(ValueError):
    """Raised when an event cannot be settled by known football rules."""


class InvalidMatchResultError(ValueError):
    """Raised when match result or goals are missing or inconsistent."""


@dataclass(frozen=True)
class SettlementCandidate:
    """One pending final prediction or bet awaiting football settlement.

    ``family`` must use ``event_families.name`` values from the database
    (for example ``REZULTAT``, not an English alias).
    """

    record_id: int
    target: SettlementTarget
    event_id: int
    event_name: str
    family: EventFamily
    result: str
    home_goals: int | None
    away_goals: int | None


def evaluate_football_outcome(candidate: SettlementCandidate) -> int:
    """Return 1 when the candidate wins, otherwise 0.

    Raises UnsupportedFootballEventError for unknown markets and
    InvalidMatchResultError for invalid finished-match payloads.
    """
    home_goals, away_goals = _require_valid_match_payload(candidate)
    if (
            candidate.target == "bet"
            and candidate.event_id not in BET_MARKET_EVENT_IDS):
        raise UnsupportedFootballEventError(
            f"Event {candidate.event_id} is outside bet settlement markets")
    if candidate.event_id in RESULT_EVENT_OUTCOMES:
        return _as_outcome(
            candidate.result == RESULT_EVENT_OUTCOMES[candidate.event_id])
    if candidate.event_id in BTTS_YES_EVENT_IDS:
        return _as_outcome(home_goals > 0 and away_goals > 0)
    if candidate.event_id in BTTS_NO_EVENT_IDS:
        return _as_outcome(not (home_goals > 0 and away_goals > 0))
    if candidate.event_id in OVER_25_EVENT_IDS:
        return _as_outcome(home_goals + away_goals > 2.5)
    if candidate.event_id in UNDER_25_EVENT_IDS:
        return _as_outcome(home_goals + away_goals < 2.5)
    if candidate.event_id in GOALS_EXACT_TOTAL_EVENTS:
        expected = GOALS_EXACT_TOTAL_EVENTS[candidate.event_id]
        return _as_outcome(home_goals + away_goals == expected)
    if candidate.event_id == GOALS_6_PLUS_EVENT_ID:
        return _as_outcome(home_goals + away_goals >= 6)
    if candidate.family == "EXACT":
        return _evaluate_exact_score(
            candidate.event_name, home_goals, away_goals)
    raise UnsupportedFootballEventError(
        f"Unsupported football event_id={candidate.event_id} "
        f"family={candidate.family}")


def _require_valid_match_payload(
        candidate: SettlementCandidate
) -> tuple[int, int]:
    """Validate finished-match fields used by every settlement family."""
    if candidate.result not in VALID_MATCH_RESULTS:
        raise InvalidMatchResultError(
            f"Match result must be one of 1/X/2, got {candidate.result!r}")
    if candidate.home_goals is None or candidate.away_goals is None:
        raise InvalidMatchResultError(
            "Home and away goals are required for settlement")
    if candidate.home_goals < 0 or candidate.away_goals < 0:
        raise InvalidMatchResultError(
            "Home and away goals must be non-negative integers")
    return candidate.home_goals, candidate.away_goals


def _evaluate_exact_score(
        event_name: str,
        home_goals: int,
        away_goals: int
) -> int:
    """Settle EXACT markets from strict score labels such as 1:5+."""
    match = EXACT_SCORE_PATTERN.fullmatch(event_name.strip())
    if match is None:
        raise UnsupportedFootballEventError(
            f"Unsupported EXACT event name {event_name!r}")
    return _as_outcome(
        _side_matches(match.group("home"), home_goals)
        and _side_matches(match.group("away"), away_goals))


def _side_matches(token: str, goals: int) -> bool:
    """Match a score side token against observed goals."""
    if token.endswith("+"):
        return goals >= int(token[:-1])
    return goals == int(token)


def _as_outcome(won: bool) -> int:
    """Normalize boolean settlement to the stored 0/1 outcome scale."""
    return 1 if won else 0
