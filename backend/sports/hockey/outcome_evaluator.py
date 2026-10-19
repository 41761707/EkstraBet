"""Domain rules for settling hockey markets including overtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.sports.hockey.markets import HOCKEY_MARKET_RULES
from backend.sports.hockey.markets import HockeyMarketRule


SettlementTarget = Literal["final_prediction", "bet", "tipster_leg"]
HockeyEventFamily = Literal["HOCKEY_ML", "HOCKEY_OU_55", "HOCKEY_OU_65",
    "HOCKEY_PL_HOME", "HOCKEY_PL_AWAY", "HOCKEY_HOME_TT_25",
    "HOCKEY_HOME_TT_35", "HOCKEY_AWAY_TT_25", "HOCKEY_AWAY_TT_35"]
ExtraTimeSide = Literal["home", "away"]

VALID_MATCH_RESULTS = frozenset({"1", "X", "2"})
OT_WINNER_HOME = 1
OT_WINNER_AWAY = 2
OT_WINNER_SHOOTOUT = 3
SO_WINNER_HOME = 1
SO_WINNER_AWAY = 2


class UnsupportedHockeyEventError(ValueError):
    """Raised when an event cannot be settled by known hockey rules."""


class InvalidMatchResultError(ValueError):
    """Raised when match result, goals or overtime data are unusable."""


@dataclass(frozen=True)
class HockeySettlementCandidate:
    """One pending final prediction or bet awaiting settlement.

    ``family`` uses ``event_families.name`` from the database.
    Goals are regulation totals. ``ot_winner`` is 1 home, 2 away
    or 3 shootout, matching ``hockey_matches_add``. ``sport_id``
    is 2 when maintenance loaded the row.
    """

    record_id: int
    target: SettlementTarget
    event_id: int
    event_name: str
    family: HockeyEventFamily
    result: str
    home_goals: int | None
    away_goals: int | None
    ot_winner: int | None = None
    so_winner: int | None = None
    match_id: int | None = None
    sport_id: int | None = None


def final_score(
    home_goals: int,
    away_goals: int,
    ot_winner: int | None,
    so_winner: int | None) -> tuple[int, int]:
    """Return regulation goals plus one overtime or shootout goal.

    A regulation winner is unchanged. A tie requires ``ot_winner``.
    Shootouts (``ot_winner`` 3) take the winner from ``so_winner``.
    """
    _require_non_negative_goals(home_goals, away_goals)
    if home_goals != away_goals:
        return home_goals, away_goals
    winner = _extra_time_winner(ot_winner, so_winner)
    if winner == "home":
        return home_goals + 1, away_goals
    return home_goals, away_goals + 1


def evaluate_hockey_outcome(candidate: HockeySettlementCandidate) -> int:
    """Return 1 when the candidate wins, otherwise 0.

    Raises UnsupportedHockeyEventError for unknown markets and
    InvalidMatchResultError for invalid finished-match payloads.
    """
    home_goals, away_goals = _require_regulation_score(candidate)
    settled_home, settled_away = final_score(
        home_goals,
        away_goals,
        candidate.ot_winner,
        candidate.so_winner)
    rule = HOCKEY_MARKET_RULES.get(candidate.event_id)
    if rule is None:
        raise UnsupportedHockeyEventError(
            f"Unsupported hockey event_id={candidate.event_id}")
    return _compare_market(rule, settled_home, settled_away)


def _extra_time_winner(
    ot_winner: int | None,
    so_winner: int | None) -> ExtraTimeSide:
    """Resolve who receives the extra goal after a regulation tie."""
    # Remis bez OTwinner zostaje pending, jak brak wyniku w piłce.
    if ot_winner is None:
        raise InvalidMatchResultError(
            "Overtime winner is required when regulation goals are tied")
    if ot_winner == OT_WINNER_HOME:
        return "home"
    if ot_winner == OT_WINNER_AWAY:
        return "away"
    if ot_winner == OT_WINNER_SHOOTOUT:
        return _shootout_winner(so_winner)
    raise InvalidMatchResultError(
        f"Overtime winner must be 1, 2 or 3, got {ot_winner}")


def _shootout_winner(so_winner: int | None) -> ExtraTimeSide:
    """Map SOwinner onto the side that receives the shootout goal."""
    if so_winner == SO_WINNER_HOME:
        return "home"
    if so_winner == SO_WINNER_AWAY:
        return "away"
    raise InvalidMatchResultError(
        "Shootout winner is required when overtime winner is 3")


def _require_regulation_score(
    candidate: HockeySettlementCandidate) -> tuple[int, int]:
    """Validate finished-match fields shared by every hockey market."""
    if candidate.result not in VALID_MATCH_RESULTS:
        raise InvalidMatchResultError(
            f"Match result must be one of 1/X/2, got {candidate.result!r}")
    if candidate.home_goals is None or candidate.away_goals is None:
        raise InvalidMatchResultError(
            "Home and away goals are required for settlement")
    _require_non_negative_goals(candidate.home_goals, candidate.away_goals)
    return candidate.home_goals, candidate.away_goals


def _require_non_negative_goals(home_goals: int, away_goals: int) -> None:
    """Reject negative regulation totals before comparison."""
    if home_goals < 0 or away_goals < 0:
        raise InvalidMatchResultError(
            "Home and away goals must be non-negative integers")


def _compare_market(
    rule: HockeyMarketRule,
    home_goals: int,
    away_goals: int) -> int:
    """Compare one market rule with the final score."""
    value = _observed_value(rule, home_goals, away_goals)
    if rule.comparator == "over":
        return _as_outcome(value > rule.line)
    return _as_outcome(value < rule.line)


def _observed_value(
    rule: HockeyMarketRule,
    home_goals: int,
    away_goals: int) -> int:
    """Return the statistic named by the market rule."""
    if rule.stat == "goals":
        return _goal_total(rule.side, home_goals, away_goals)
    return _goal_margin(rule.side, home_goals, away_goals)


def _goal_total(side: str, home_goals: int, away_goals: int) -> int:
    """Return home, away or combined goals."""
    if side == "home":
        return home_goals
    if side == "away":
        return away_goals
    if side == "total":
        return home_goals + away_goals
    raise UnsupportedHockeyEventError(
        f"Unsupported hockey goal side {side!r}")


def _goal_margin(side: str, home_goals: int, away_goals: int) -> int:
    """Return the signed goal margin for one side."""
    if side == "home":
        return home_goals - away_goals
    if side == "away":
        return away_goals - home_goals
    raise UnsupportedHockeyEventError(
        f"Unsupported hockey margin side {side!r}")


def _as_outcome(won: bool) -> int:
    """Normalize boolean settlement to the stored 0/1 outcome scale."""
    return 1 if won else 0
