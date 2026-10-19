"""Season special-teams totals for NHL teams."""

from __future__ import annotations

import math
from typing import Any

from backend.repositories.hockey_special_teams_repository import (
    GAME_MISCONDUCT_EVENT_ID,
    MAJOR_PENALTY_EVENT_ID,
    MINOR_PENALTY_EVENT_ID,
    MISCONDUCT_EVENT_ID,
    fetch_special_teams_matches)


_IGNORED_EVENT_IDS = (GAME_MISCONDUCT_EVENT_ID, MISCONDUCT_EVENT_ID)
_FIGHT_MARKERS = ("Walka na pięści", "Wszczęcie bójki")
_FINAL_HORN_TIMES = ("19:59", "20:00")
_REGULATION_LAST_PERIOD = 3


def power_play_opportunities(
        goals: int,
        accuracy: float | None,
        opponent_fouls: int) -> int:
    """Return chances when the penalty list does not cover the fouls.

    A positive accuracy is goals divided by chances, stored as a
    percent, so it recovers the chance count when the foul column
    disagrees. A zero accuracy cannot, and the opponent foul count is
    the chance count.
    """
    if goals > 0 and accuracy is not None and accuracy > 0:
        return int(round(goals * 100.0 / accuracy))
    return opponent_fouls


def _is_fight(description: str) -> bool:
    """A fight is a matching major and never opens a power play."""
    return any(marker in description for marker in _FIGHT_MARKERS)


def _at_final_horn(
        penalty: dict[str, Any],
        went_to_extra_time: bool) -> bool:
    """True when the game ended on this whistle, so no advantage was played.

    The feed stores the official 20:00 horn as 19:59 or 20:00. A penalty
    at the end of the first or second period carries over, and so does
    one at the end of regulation when the match goes to extra time.
    """
    if went_to_extra_time:
        return False
    if int(penalty["period"]) < _REGULATION_LAST_PERIOD:
        return False
    return str(penalty["event_time"]) in _FINAL_HORN_TIMES


def _opens_advantage(
        penalty: dict[str, Any],
        went_to_extra_time: bool) -> bool:
    """Keep minors and non-fight majors that actually change manpower."""
    event_id = int(penalty["event_id"])
    description = str(penalty["description"])
    if event_id in _IGNORED_EVENT_IDS or _is_fight(description):
        return False
    if _at_final_horn(penalty, went_to_extra_time):
        return False
    return event_id in (MINOR_PENALTY_EVENT_ID, MAJOR_PENALTY_EVENT_ID)


def _whistle_surplus(
        rows: list[dict[str, Any]],
        home_team_id: int,
        away_team_id: int) -> tuple[int, int]:
    """Cancel equal penalties at one whistle. Return both surpluses."""
    home_minors = 0
    away_minors = 0
    home_majors = 0
    away_majors = 0
    for row in rows:
        team_id = int(row["team_id"])
        is_major = int(row["event_id"]) == MAJOR_PENALTY_EVENT_ID
        if team_id == home_team_id and is_major:
            home_majors += 1
        elif team_id == home_team_id:
            home_minors += 1
        elif team_id == away_team_id and is_major:
            away_majors += 1
        elif team_id == away_team_id:
            away_minors += 1
    home_chances = (
        max(away_minors - home_minors, 0)
        + max(away_majors - home_majors, 0))
    away_chances = (
        max(home_minors - away_minors, 0)
        + max(home_majors - away_majors, 0))
    return home_chances, away_chances


def power_play_chances_from_penalties(
        penalties: list[dict[str, Any]],
        home_team_id: int,
        away_team_id: int,
        *,
        went_to_extra_time: bool = False) -> tuple[int, int]:
    """Return home and away power-play chances for one match.

    Fights, misconducts and a penalty at the final horn do not open a
    power play. Equal minors cancel, equal majors cancel, and only the
    surplus is a power play for the other team.
    """
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for penalty in penalties:
        if not _opens_advantage(penalty, went_to_extra_time):
            continue
        key = (int(penalty["period"]), str(penalty["event_time"]))
        grouped.setdefault(key, []).append(penalty)
    home_chances = 0
    away_chances = 0
    for rows in grouped.values():
        home_added, away_added = _whistle_surplus(
            rows, home_team_id, away_team_id)
        home_chances += home_added
        away_chances += away_added
    return home_chances, away_chances


def _has_penalty_events(match: dict[str, Any]) -> bool:
    """Prefer penalty rows whenever the feed stored any.

    A short list can miss one penalty. The foul column is worse: it
    still counts fights and misconducts as power-play chances.
    """
    return bool(match.get("penalties"))


def _match_chances(match: dict[str, Any]) -> tuple[int, int]:
    """Return home and away power-play chances, with a foul fallback."""
    if _has_penalty_events(match):
        return power_play_chances_from_penalties(
            list(match["penalties"]),
            int(match["home_team_id"]),
            int(match["away_team_id"]),
            went_to_extra_time=bool(match.get("went_to_extra_time")))
    home_chances = power_play_opportunities(
        int(match["home_pp_goals"]),
        match["home_pp_accuracy"],
        int(match["away_fouls"]))
    away_chances = power_play_opportunities(
        int(match["away_pp_goals"]),
        match["away_pp_accuracy"],
        int(match["home_fouls"]))
    return home_chances, away_chances


def _rate(numerator: int, denominator: int) -> float | None:
    """Return a percent, or None when there is nothing to divide."""
    if denominator <= 0:
        return None
    return numerator * 100.0 / denominator


def _round_rate(value: float | None) -> float | None:
    """Round a percent to one decimal, with halves away from zero.

    26 kills out of 32 is 81.25. NHL prints 81.3. Python's default
    round leaves that halfway case at 81.2.
    """
    if value is None:
        return None
    scaled = value * 10.0
    if scaled >= 0:
        scaled = math.floor(scaled + 0.5)
    else:
        scaled = math.ceil(scaled - 0.5)
    return scaled / 10.0


class _Totals:
    """Running special-teams counters for one team."""

    def __init__(
            self,
            team_name: str,
            team_shortcut: str) -> None:
        self.team_name = team_name
        self.team_shortcut = team_shortcut
        self.pp_goals = 0
        self.pp_opportunities = 0
        self.pk_opportunities = 0
        self.pk_goals_against = 0
        self.matches_played = 0


def _team(
        teams: dict[int, _Totals],
        team_id: int,
        team_name: str,
        team_shortcut: str) -> _Totals:
    """Return the counters for a team, creating them on first sight."""
    existing = teams.get(team_id)
    if existing is not None:
        return existing
    created = _Totals(team_name, team_shortcut)
    teams[team_id] = created
    return created


def _apply_side(
        team: _Totals,
        pp_goals: int,
        pp_opportunities: int,
        goals_against: int,
        pk_opportunities: int) -> None:
    """Add one match to a team's season counters."""
    team.matches_played += 1
    team.pp_goals += pp_goals
    team.pp_opportunities += pp_opportunities
    team.pk_goals_against += goals_against
    team.pk_opportunities += pk_opportunities


def _add_match(teams: dict[int, _Totals], match: dict[str, Any]) -> None:
    """Split one match into a power play and a penalty kill per team."""
    home_pp_goals = int(match["home_pp_goals"])
    away_pp_goals = int(match["away_pp_goals"])
    home_opps, away_opps = _match_chances(match)
    home = _team(
        teams,
        int(match["home_team_id"]),
        str(match["home_team_name"]),
        str(match["home_team_shortcut"] or ""))
    away = _team(
        teams,
        int(match["away_team_id"]),
        str(match["away_team_name"]),
        str(match["away_team_shortcut"] or ""))
    _apply_side(home, home_pp_goals, home_opps, away_pp_goals, away_opps)
    _apply_side(away, away_pp_goals, away_opps, home_pp_goals, home_opps)


def _payload(team: _Totals) -> dict[str, Any]:
    """Turn season counters into percents and the Hitchcock sum."""
    pp_pct = _rate(team.pp_goals, team.pp_opportunities)
    kills = team.pk_opportunities - team.pk_goals_against
    pk_pct = _rate(kills, team.pk_opportunities)
    hitchcock = None
    if pp_pct is not None and pk_pct is not None:
        hitchcock = pp_pct + pk_pct
    return {
        "team_name": team.team_name,
        "team_shortcut": team.team_shortcut,
        "matches_played": team.matches_played,
        "pp_goals": team.pp_goals,
        "pp_opportunities": team.pp_opportunities,
        "pp_pct": _round_rate(pp_pct),
        "pk_kills": kills,
        "pk_opportunities": team.pk_opportunities,
        "pk_pct": _round_rate(pk_pct),
        "hitchcock": _round_rate(hitchcock)
    }


def _sort_key(row: dict[str, Any]) -> tuple[float, str]:
    """Place a higher Hitchcock sum first and a missing sum last."""
    hitchcock = row["hitchcock"]
    score = hitchcock if hitchcock is not None else float("-inf")
    return (-score, str(row["team_name"]).casefold())


def accumulate_special_teams(
        matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sum power play and penalty kill for each team in the sample."""
    teams: dict[int, _Totals] = {}
    for match in matches:
        _add_match(teams, match)
    rows = [_payload(team) for team in teams.values()]
    rows.sort(key=_sort_key)
    return rows


def get_hockey_special_teams(
        league_id: int,
        season_id: int,
        phase: int | None = None) -> list[dict[str, Any]]:
    """Return season special-teams rows for one NHL league."""
    matches = fetch_special_teams_matches(league_id, season_id, phase)
    return accumulate_special_teams(matches)
