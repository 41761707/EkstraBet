"""Recent-match series for a team bet, in the same shape as a prop strip.

Match-level markets (totals, BTTS, draw, exact goal count, exact
score, and totals of corners, fouls, cards and offsides) draw two
strips: the home team's recent games, then the away team's. Each
strip has one subject. Exact score is a 0/1 flag read from that
team's side: 1:0 is a hit when they scored one and conceded none,
including away. Team markets follow the named side only, and each
past match is read from that team's point of view. Hockey bars use
the settled score: a regulation tie adds one goal for the overtime
or shootout winner.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

from backend.sports.football.event_settlement_registry import (
    parse_line_market)
from backend.sports.football.markets import (
    EXACT_SCORE_EVENT_IDS,
    GOALS_6_PLUS_EVENT_ID,
    GOALS_EXACT_TOTAL_EVENTS)
from backend.sports.football.outcome_evaluator import EXACT_SCORE_PATTERN
from backend.sports.hockey.markets import HOCKEY_MARKET_RULES
from backend.sports.hockey.outcome_evaluator import (
    InvalidMatchResultError,
    final_score)


FOOTBALL_SPORT_ID = 1
HOCKEY_SPORT_ID = 2

SampleSide = Literal["home", "away"]
StatKind = Literal[
    "goals_for",
    "total_goals",
    "margin",
    "win",
    "draw",
    "not_loss",
    "btts",
    "corners_for",
    "corners_total",
    "fouls_for",
    "fouls_total",
    "yellows_for",
    "yellows_total",
    "offsides_for",
    "offsides_total",
    "flag",
    "exact_score"]
Comparator = Literal["over", "under"]
TeamSide = Literal["home", "away"]

_LINE_STATS: dict[tuple[str, str], tuple[SampleSide, StatKind]] = {
    ("goals", "home"): ("home", "goals_for"),
    ("goals", "away"): ("away", "goals_for"),
    ("goals", "total"): ("home", "total_goals"),
    ("corners", "home"): ("home", "corners_for"),
    ("corners", "away"): ("away", "corners_for"),
    ("corners", "total"): ("home", "corners_total"),
    ("fouls", "home"): ("home", "fouls_for"),
    ("fouls", "away"): ("away", "fouls_for"),
    ("fouls", "total"): ("home", "fouls_total"),
    ("yellows", "home"): ("home", "yellows_for"),
    ("yellows", "away"): ("away", "yellows_for"),
    ("yellows", "total"): ("home", "yellows_total"),
    ("offsides", "home"): ("home", "offsides_for"),
    ("offsides", "away"): ("away", "offsides_for"),
    ("offsides", "total"): ("home", "offsides_total")}


class PastMatch(NamedTuple):
    """One finished match used as a bar on the history strip."""

    home_team_id: int
    away_team_id: int
    home_goals: int
    away_goals: int
    result: str
    home_corners: int | None
    away_corners: int | None
    home_fouls: int | None
    away_fouls: int | None
    home_yellows: int | None
    away_yellows: int | None
    home_offsides: int | None
    away_offsides: int | None
    ot_winner: int | None = None
    so_winner: int | None = None


class TeamHistoryRule(NamedTuple):
    """How to turn one past match into a bar and a hit."""

    sample: SampleSide
    stat: StatKind
    line: float
    comparator: Comparator
    flag_total: int | None = None
    flag_at_least: int | None = None
    score_home: str | None = None
    score_away: str | None = None


def history_rule(
        sport_id: int,
        event_id: int,
        event_name: str) -> TeamHistoryRule | None:
    """Return the strip rule, or None when the event has no series."""
    if sport_id == HOCKEY_SPORT_ID:
        return _hockey_rule(event_id)
    if sport_id == FOOTBALL_SPORT_ID:
        return _football_rule(event_id, event_name)
    return None


def sample_team_id(
        rule: TeamHistoryRule,
        home_team_id: int,
        away_team_id: int) -> int:
    """Return the team whose recent matches feed one strip."""
    if rule.sample == "away":
        return away_team_id
    return home_team_id


def history_samples(rule: TeamHistoryRule) -> tuple[SampleSide, ...]:
    """Return the sides drawn for this rule, home before away."""
    if names_sampled_team(rule):
        return ("home", "away")
    return (rule.sample,)


def sampled_teams(
        rule: TeamHistoryRule,
        home_team_id: int,
        away_team_id: int) -> list[tuple[SampleSide, int]]:
    """Return each strip subject and that team's id, home first."""
    pairs: list[tuple[SampleSide, int]] = []
    for sample in history_samples(rule):
        team_id = away_team_id if sample == "away" else home_team_id
        pairs.append((sample, team_id))
    return pairs


def history_stat_filter(rule: TeamHistoryRule) -> str:
    """Return the history-query filter. Goal stats share one window."""
    if rule.stat in _GOAL_STATS:
        return "goals"
    return rule.stat


def names_sampled_team(rule: TeamHistoryRule) -> bool:
    """Return whether the event draws both teams and names them.

    The event title does not say whose games those are, so the strip
    shows the home side and the away side.
    """
    return rule.stat in _MATCH_SAMPLE_STATS


def stat_value(
        rule: TeamHistoryRule,
        team_id: int,
        match: PastMatch) -> float | None:
    """Return the bar height, or None when the stat is missing."""
    settled = _with_settled_score(match)
    if rule.stat == "flag":
        return _flag_value(rule, settled)
    if rule.stat == "exact_score":
        return _exact_score_value(rule, team_id, settled)
    if rule.stat in {"win", "not_loss", "margin", "goals_for"}:
        return _team_result_value(rule.stat, team_id, settled)
    if rule.stat in {"draw", "btts", "total_goals"}:
        return _match_result_value(rule.stat, settled)
    return _count_value(rule.stat, team_id, settled)


def is_history_hit(
        value: float,
        line: float,
        comparator: Comparator) -> bool:
    """Return whether the bar clears the line. Equality is a miss."""
    if comparator == "over":
        return value > line
    return value < line


def _football_rule(
        event_id: int,
        event_name: str) -> TeamHistoryRule | None:
    """Map a football catalog event onto a strip rule."""
    explicit = _EXPLICIT_FOOTBALL.get(event_id)
    if explicit is not None:
        return explicit
    exact = _exact_total_rule(event_id)
    if exact is not None:
        return exact
    if event_id in EXACT_SCORE_EVENT_IDS:
        return _exact_score_rule(event_name)
    parsed = parse_line_market(event_name)
    if parsed is None:
        return None
    mapped = _LINE_STATS.get((parsed.stat, parsed.side))
    if mapped is None:
        return None
    sample, stat = mapped
    return TeamHistoryRule(sample, stat, parsed.line, parsed.comparator)


def _exact_total_rule(event_id: int) -> TeamHistoryRule | None:
    """Encode an exact total as a 0/1 flag so the strip stays green on hits."""
    if event_id in GOALS_EXACT_TOTAL_EVENTS:
        return TeamHistoryRule(
            "home",
            "flag",
            0.5,
            "over",
            flag_total=GOALS_EXACT_TOTAL_EVENTS[event_id])
    if event_id == GOALS_6_PLUS_EVENT_ID:
        return TeamHistoryRule(
            "home", "flag", 0.5, "over", flag_at_least=6)
    return None


def _hockey_rule(event_id: int) -> TeamHistoryRule | None:
    """Map a hockey market rule onto the shared strip shape."""
    market = HOCKEY_MARKET_RULES.get(event_id)
    if market is None:
        return None
    sample: SampleSide = "away" if market.side == "away" else "home"
    if market.stat == "margin":
        stat: StatKind = "margin"
    elif market.side == "total":
        stat = "total_goals"
    else:
        stat = "goals_for"
    return TeamHistoryRule(
        sample, stat, market.line, market.comparator)


def _exact_score_rule(event_name: str) -> TeamHistoryRule | None:
    """Encode an exact score as a 0/1 flag from the sampled team's side."""
    parsed = EXACT_SCORE_PATTERN.fullmatch(event_name.strip())
    if parsed is None:
        return None
    return TeamHistoryRule(
        "home",
        "exact_score",
        0.5,
        "over",
        score_home=parsed.group("home"),
        score_away=parsed.group("away"))


def _with_settled_score(match: PastMatch) -> PastMatch:
    """Add one overtime or shootout goal when the add-table names it."""
    if match.ot_winner is None:
        return match
    try:
        home_goals, away_goals = final_score(
            match.home_goals,
            match.away_goals,
            match.ot_winner,
            match.so_winner)
    except InvalidMatchResultError:
        # Remis bez rozstrzygnięcia nie może przerwać całej historii.
        return match
    if (
            home_goals == match.home_goals
            and away_goals == match.away_goals):
        return match
    return match._replace(
        home_goals=home_goals,
        away_goals=away_goals)


def _exact_score_value(
        rule: TeamHistoryRule,
        team_id: int,
        match: PastMatch) -> float | None:
    """Return 1 when the sampled team posted the named scoreline."""
    if rule.score_home is None or rule.score_away is None:
        return 0.0
    side = _team_side(team_id, match)
    if side is None:
        return None
    scored, conceded = _goal_pair(side, match)
    matched = (
        _score_token_matches(rule.score_home, scored)
        and _score_token_matches(rule.score_away, conceded))
    return 1.0 if matched else 0.0


def _score_token_matches(token: str, goals: int) -> bool:
    """Match a score token. A trailing plus means that many or more."""
    if token.endswith("+"):
        return goals >= int(token[:-1])
    return goals == int(token)


def _flag_value(rule: TeamHistoryRule, match: PastMatch) -> float:
    """Return 1 when the exact-total flag matches this match."""
    total = match.home_goals + match.away_goals
    if rule.flag_at_least is not None:
        return 1.0 if total >= rule.flag_at_least else 0.0
    return 1.0 if total == rule.flag_total else 0.0


def _team_result_value(
        stat: StatKind,
        team_id: int,
        match: PastMatch) -> float | None:
    """Read a result stat from the sampled team's side of the match."""
    side = _team_side(team_id, match)
    if side is None:
        return None
    scored, conceded = _goal_pair(side, match)
    if stat == "goals_for":
        return float(scored)
    if stat == "margin":
        return float(scored - conceded)
    won = _won(side, match.result)
    if stat == "win":
        return 1.0 if won else 0.0
    lost = _lost(side, match.result)
    return 0.0 if lost else 1.0


def _match_result_value(stat: StatKind, match: PastMatch) -> float:
    """Read a match-level stat that does not flip with the team's side."""
    if stat == "draw":
        return 1.0 if match.result == "X" else 0.0
    if stat == "btts":
        both = match.home_goals > 0 and match.away_goals > 0
        return 1.0 if both else 0.0
    return float(match.home_goals + match.away_goals)


def _count_value(
        stat: StatKind,
        team_id: int,
        match: PastMatch) -> float | None:
    """Read corners, fouls, cards or offsides, or None when uncounted."""
    home_value, away_value = _count_pair(stat, match)
    if stat.endswith("_total"):
        if home_value is None or away_value is None:
            return None
        return float(home_value + away_value)
    side = _team_side(team_id, match)
    if side is None:
        return None
    value = home_value if side == "home" else away_value
    if value is None:
        return None
    return float(value)


def _count_pair(
        stat: StatKind,
        match: PastMatch) -> tuple[int | None, int | None]:
    """Return the home and away counts for a non-goal stat."""
    if stat.startswith("corners"):
        return match.home_corners, match.away_corners
    if stat.startswith("fouls"):
        return match.home_fouls, match.away_fouls
    if stat.startswith("yellows"):
        return match.home_yellows, match.away_yellows
    return match.home_offsides, match.away_offsides


def _team_side(team_id: int, match: PastMatch) -> TeamSide | None:
    """Return which side the sampled team took in this past match."""
    if team_id == match.home_team_id:
        return "home"
    if team_id == match.away_team_id:
        return "away"
    return None


def _goal_pair(side: TeamSide, match: PastMatch) -> tuple[int, int]:
    """Return goals scored and conceded by the given side."""
    if side == "home":
        return match.home_goals, match.away_goals
    return match.away_goals, match.home_goals


def _won(side: TeamSide, result: str) -> bool:
    """Return whether that side won the match."""
    if side == "home":
        return result == "1"
    return result == "2"


def _lost(side: TeamSide, result: str) -> bool:
    """Return whether that side lost the match."""
    if side == "home":
        return result == "2"
    return result == "1"


_GOAL_STATS = frozenset({
    "goals_for",
    "total_goals",
    "margin",
    "win",
    "draw",
    "not_loss",
    "btts",
    "flag",
    "exact_score"})

_MATCH_SAMPLE_STATS = frozenset({
    "total_goals",
    "draw",
    "btts",
    "flag",
    "exact_score",
    "corners_total",
    "fouls_total",
    "yellows_total",
    "offsides_total"})

_EXPLICIT_FOOTBALL: dict[int, TeamHistoryRule] = {
    1: TeamHistoryRule("home", "win", 0.5, "over"),
    2: TeamHistoryRule("home", "draw", 0.5, "over"),
    3: TeamHistoryRule("away", "win", 0.5, "over"),
    4: TeamHistoryRule("home", "not_loss", 0.5, "over"),
    5: TeamHistoryRule("away", "not_loss", 0.5, "over"),
    6: TeamHistoryRule("home", "btts", 0.5, "over"),
    172: TeamHistoryRule("home", "btts", 0.5, "under"),
    8: TeamHistoryRule("home", "total_goals", 2.5, "over"),
    12: TeamHistoryRule("home", "total_goals", 2.5, "under"),
    49: TeamHistoryRule("home", "margin", 1.5, "over"),
    50: TeamHistoryRule("home", "margin", -1.5, "over"),
    51: TeamHistoryRule("away", "margin", 1.5, "over"),
    52: TeamHistoryRule("away", "margin", -1.5, "over")}
