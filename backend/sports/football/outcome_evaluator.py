"""Domain rules for settling football prediction and bet outcomes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from backend.sports.football.event_settlement_registry import (
    LineMarketRule,
    MatchBoxscore,
    parse_line_market)


SettlementTarget = Literal["final_prediction", "bet", "tipster_leg"]
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
DOUBLE_CHANCE_HOME_EVENT_ID = 4
DOUBLE_CHANCE_AWAY_EVENT_ID = 5
HANDICAP_HOME_MINUS_15_EVENT_ID = 49
HANDICAP_HOME_PLUS_15_EVENT_ID = 50
HANDICAP_AWAY_MINUS_15_EVENT_ID = 51
HANDICAP_AWAY_PLUS_15_EVENT_ID = 52
EXACT_SCORE_EVENT_IDS = frozenset(range(198, 234))
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
_STAT_LABELS = {
    "corners": "corners",
    "fouls": "fouls",
    "yellows": "yellow cards",
    "offsides": "offsides"
}


class UnsupportedFootballEventError(ValueError):
    """Raised when an event cannot be settled by known football rules."""


class InvalidMatchResultError(ValueError):
    """Raised when match result or goals are missing or inconsistent."""


@dataclass(frozen=True)
class SettlementCandidate:
    """One pending final prediction or bet awaiting football settlement.

    ``family`` must use ``event_families.name`` values from the database
    (for example ``REZULTAT``, not an English alias). ``sport_id`` is 1
    when maintenance loaded the row; tipster legs leave it empty.
    """

    record_id: int
    target: SettlementTarget
    event_id: int
    event_name: str
    family: EventFamily
    result: str
    home_goals: int | None
    away_goals: int | None
    match_id: int | None = None
    boxscore: MatchBoxscore | None = None
    sport_id: int | None = None


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
    goal_outcome = _evaluate_known_goal_market(
        candidate, home_goals, away_goals)
    if goal_outcome is not None:
        return goal_outcome
    if candidate.target == "tipster_leg":
        return _evaluate_tipster_leg(candidate, home_goals, away_goals)
    raise UnsupportedFootballEventError(
        f"Unsupported football event_id={candidate.event_id} "
        f"family={candidate.family}")


def _evaluate_known_goal_market(
        candidate: SettlementCandidate,
        home_goals: int,
        away_goals: int
) -> int | None:
    """Settle 1X2/BTTS/OU 2.5/exact-goals/EXACT; None if not those markets."""
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
    return None


def _evaluate_tipster_leg(
        candidate: SettlementCandidate,
        home_goals: int,
        away_goals: int
) -> int:
    """Settle Double Chance, handicap, exact score by id, then line markets."""
    double_chance_outcome = _evaluate_double_chance(
        candidate.event_id, candidate.result)
    if double_chance_outcome is not None:
        return double_chance_outcome
    handicap_outcome = _evaluate_handicap(
        candidate.event_id, home_goals, away_goals)
    if handicap_outcome is not None:
        return handicap_outcome
    if candidate.event_id in EXACT_SCORE_EVENT_IDS:
        return _evaluate_exact_score(
            candidate.event_name, home_goals, away_goals)
    rule = parse_line_market(candidate.event_name)
    if rule is not None:
        return _evaluate_line_market(
            candidate, rule, home_goals, away_goals)
    raise UnsupportedFootballEventError(
        f"Unsupported football event_id={candidate.event_id} "
        f"family={candidate.family}")


def _evaluate_double_chance(event_id: int, result: str) -> int | None:
    """Settle 1X/X2 Double Chance; a draw is a win, not a void."""
    if event_id == DOUBLE_CHANCE_HOME_EVENT_ID:
        return _as_outcome(result in {"1", "X"})
    if event_id == DOUBLE_CHANCE_AWAY_EVENT_ID:
        return _as_outcome(result in {"2", "X"})
    return None


def _evaluate_handicap(
        event_id: int,
        home_goals: int,
        away_goals: int
) -> int | None:
    """Settle Asian handicap ±1.5; None when the event is not handicap."""
    home_margin = home_goals - away_goals
    away_margin = away_goals - home_goals
    if event_id == HANDICAP_HOME_MINUS_15_EVENT_ID:
        return _as_outcome(home_margin > 1.5)
    if event_id == HANDICAP_HOME_PLUS_15_EVENT_ID:
        return _as_outcome(home_margin > -1.5)
    if event_id == HANDICAP_AWAY_MINUS_15_EVENT_ID:
        return _as_outcome(away_margin > 1.5)
    if event_id == HANDICAP_AWAY_PLUS_15_EVENT_ID:
        return _as_outcome(away_margin > -1.5)
    return None


def _evaluate_line_market(
        candidate: SettlementCandidate,
        rule: LineMarketRule,
        home_goals: int,
        away_goals: int
) -> int:
    """Compare a parsed over/under rule against goals or boxscore stats."""
    value = _line_stat_value(candidate, rule, home_goals, away_goals)
    if rule.comparator == "over":
        return _as_outcome(value > rule.line)
    return _as_outcome(value < rule.line)


def _line_stat_value(
        candidate: SettlementCandidate,
        rule: LineMarketRule,
        home_goals: int,
        away_goals: int
) -> int:
    """Resolve the observed statistic for a line market."""
    # Gole są już zwalidowane na kandydacie — boxscore nie jest potrzebny.
    if rule.stat == "goals":
        return _require_side_total(
            "goals", rule.side, home_goals, away_goals)
    home_stat, away_stat = _boxscore_pair(candidate.boxscore, rule.stat)
    return _require_side_total(rule.stat, rule.side, home_stat, away_stat)


def _boxscore_pair(
        boxscore: MatchBoxscore | None,
        stat: str
) -> tuple[int | None, int | None]:
    """Return home/away counts for a non-goal boxscore statistic."""
    if boxscore is None:
        return None, None
    if stat == "corners":
        return boxscore.home_ck, boxscore.away_ck
    if stat == "fouls":
        return boxscore.home_fouls, boxscore.away_fouls
    if stat == "yellows":
        return boxscore.home_yc, boxscore.away_yc
    if stat == "offsides":
        return boxscore.home_off, boxscore.away_off
    return None, None


def _require_side_total(
        stat: str,
        side: str,
        home_stat: int | None,
        away_stat: int | None
) -> int:
    """Return the side total or raise when a required statistic is missing."""
    if side == "home":
        return _require_stat(stat, "home", home_stat)
    if side == "away":
        return _require_stat(stat, "away", away_stat)
    home_value = _require_stat(stat, "home", home_stat)
    away_value = _require_stat(stat, "away", away_stat)
    return home_value + away_value


def _require_stat(stat: str, side: str, value: int | None) -> int:
    """Validate a single non-negative boxscore count."""
    label = _STAT_LABELS.get(stat, stat)
    if value is None:
        raise InvalidMatchResultError(
            f"{side.capitalize()} {label} are required for settlement")
    if value < 0:
        raise InvalidMatchResultError(
            f"{side.capitalize()} {label} must be non-negative integers")
    return value


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
