"""Incremental league, team-season and table context from finished matches."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from math import exp
from typing import Any

import pandas as pd

from models.pipeline.core.config import FootballContextParams


_PRIOR_HOME_GOALS = 1.5
_PRIOR_AWAY_GOALS = 1.2
# Plan nie podaje stałej udziału stron bez gola. To P(0) z Poissona
# o λ równym średniej domyślnych bramek gospodarzy i gości.
_PRIOR_ZERO_GOAL_SIDE = exp(
    -(_PRIOR_HOME_GOALS + _PRIOR_AWAY_GOALS) / 2.0)

# Plan podaje 1.35, gdy sezon nie ma jeszcze żadnego meczu drużyn.
_DEFAULT_POINTS_PER_GAME = 1.35

# Prior, gdy w oknie nie ma ani meczów ligi, ani meczów globalnych.
DEFAULT_LEAGUE_PRIOR = {
    "home_goals": _PRIOR_HOME_GOALS,
    "away_goals": _PRIOR_AWAY_GOALS,
    "btts": 0.52,
    "over_25": 0.52,
    "draw": 0.26,
    "zero_goal_side": _PRIOR_ZERO_GOAL_SIDE
}

# Klucz prioru, nazwa cechy, pole sumy w _GoalTotals.
_LEAGUE_FEATURES = (
    ("home_goals", "league_ctx_home_goals", "home_goals"),
    ("away_goals", "league_ctx_away_goals", "away_goals"),
    ("btts", "league_ctx_btts_pct", "btts"),
    ("over_25", "league_ctx_over_25_pct", "over_25"),
    ("draw", "league_ctx_draw_pct", "draws")
)

_MatchGoals = tuple[pd.Timestamp, int, int]


@dataclass(frozen=True)
class ContextMatch:
    """One finished match reduced to the fields context state needs."""

    match_id: int
    league_id: int
    season_id: int
    game_date: pd.Timestamp
    home_team: int
    away_team: int
    home_goals: int
    away_goals: int


@dataclass
class _GoalTotals:
    """Sums used both as a season total and as a prior-window mean."""

    matches: int = 0
    home_goals: int = 0
    away_goals: int = 0
    btts: int = 0
    over_25: int = 0
    draws: int = 0
    zero_goal_sides: int = 0

    def add(self, home_goals: int, away_goals: int) -> None:
        """Add one match to the running sums."""
        self.matches += 1
        self.home_goals += home_goals
        self.away_goals += away_goals
        self.btts += int(home_goals > 0 and away_goals > 0)
        self.over_25 += int(home_goals + away_goals > 2.5)
        self.draws += int(home_goals == away_goals)
        self.zero_goal_sides += int(home_goals == 0) + int(away_goals == 0)


@dataclass(frozen=True)
class _TeamGame:
    """One team-season appearance stored so a later read can filter it."""

    game_date: pd.Timestamp
    clean_sheet: int
    failed_to_score: int
    draw: int
    points: int
    goals_for: int
    goals_against: int


@dataclass
class _TeamCounts:
    """Team-season totals from games played before an as-of moment."""

    matches: int = 0
    clean_sheets: int = 0
    failed_to_score: int = 0
    draws: int = 0
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0


class FootballContextState:
    """Incremental league, team and table state from finished matches."""

    def __init__(self, params: FootballContextParams) -> None:
        self._params = params
        self._league_matches: dict[int, deque[_MatchGoals]] = {}
        self._global_matches: deque[_MatchGoals] = deque()
        self._seasons: dict[tuple[int, int], list[_MatchGoals]] = {}
        # Lista meczów, nie suma: wcześniejsze as_of na tym samym stanie
        # musi pominąć mecze dopisane później.
        self._team_games: dict[tuple[int, int, int], list[_TeamGame]] = {}
        self._season_teams: dict[tuple[int, int], list[int]] = {}
        # Daty każdej ligi: zmęczenie nie jest ograniczone do sezonu.
        self._team_dates: dict[int, list[pd.Timestamp]] = {}

    def commit(self, match: ContextMatch) -> None:
        """Append one finished match to league, team and global history."""
        game_date = pd.Timestamp(match.game_date).normalize()
        home_goals = int(match.home_goals)
        away_goals = int(match.away_goals)
        scored = (game_date, home_goals, away_goals)
        self._league_matches.setdefault(
            match.league_id, deque()).append(scored)
        self._global_matches.append(scored)
        season_key = (match.league_id, match.season_id)
        self._seasons.setdefault(season_key, []).append(scored)
        self._append_team_game(
            match.home_team, match.league_id, match.season_id,
            game_date, home_goals, away_goals)
        self._append_team_game(
            match.away_team, match.league_id, match.season_id,
            game_date, away_goals, home_goals)

    def league_features(
            self,
            league_id: int,
            season_id: int,
            as_of: pd.Timestamp) -> dict[str, float]:
        """Return season rates shrunk toward the recent league prior.

        ``league_ctx_season_matches`` is the raw season count. The five
        rates use ``(season_sum + k * prior) / (n_s + k)``.
        """
        moment = pd.Timestamp(as_of).normalize()
        prior = self._prior_rates(league_id, moment)
        totals = _accumulate(
            self._seasons.get((league_id, season_id), ()), moment, None)
        shrink_matches = self._params.league_shrink_matches
        features: dict[str, float] = {}
        for prior_key, feature_name, total_name in _LEAGUE_FEATURES:
            season_sum = float(getattr(totals, total_name))
            features[feature_name] = _shrink(
                season_sum, totals.matches, prior[prior_key],
                shrink_matches)
        features["league_ctx_season_matches"] = float(totals.matches)
        return features

    def team_features(
            self,
            team_id: int,
            side: str,
            league_id: int,
            season_id: int,
            as_of: pd.Timestamp) -> dict[str, float]:
        """Return season rates, table place and fatigue for one team.

        Clean sheets and matches without a goal use the shrunk share of
        sides that scored zero. Draws use ``league_ctx_draw_pct``.
        Rank is 0 for the leader and 0.5 when the team has not played
        or the table has fewer than two teams. Points per game fall
        back to the season average, then to 1.35. Fatigue counts every
        league in ``[as_of - fatigue_days, as_of)``.
        ``side`` selects the ``home`` or ``away`` key prefix.
        """
        if side not in ("home", "away"):
            raise ValueError("side must be 'home' or 'away'")
        moment = pd.Timestamp(as_of).normalize()
        counts = _count_team_games(
            self._team_games.get((team_id, league_id, season_id), ()),
            moment)
        zero_ref = self._zero_goal_side_rate(league_id, season_id, moment)
        draw_ref = self.league_features(
            league_id, season_id, moment)["league_ctx_draw_pct"]
        shrink = self._params.team_shrink_matches
        prefix = f"{side}_ctx"
        played = float(counts.matches)
        standings = _season_standings(
            self._team_games,
            self._season_teams.get((league_id, season_id), ()),
            league_id,
            season_id,
            moment)
        return {
            f"{prefix}_clean_sheet_pct": _shrink(
                counts.clean_sheets, counts.matches, zero_ref, shrink),
            f"{prefix}_failed_to_score_pct": _shrink(
                counts.failed_to_score, counts.matches, zero_ref, shrink),
            f"{prefix}_draw_pct": _shrink(
                counts.draws, counts.matches, draw_ref, shrink),
            f"{prefix}_matches_played": played,
            f"{prefix}_is_newcomer": self._newcomer_flag(
                team_id, league_id, season_id, moment),
            f"{prefix}_rank_pct": _rank_pct(team_id, standings),
            f"{prefix}_points_per_game": _points_per_game(
                team_id, standings),
            f"{prefix}_matches_last_14d": _matches_in_window(
                self._team_dates.get(team_id, ()),
                moment,
                self._params.fatigue_days)
        }

    def static_features(
            self,
            home_id: int,
            away_id: int,
            league_id: int,
            season_id: int,
            as_of: pd.Timestamp) -> dict[str, float]:
        """Return league features plus both teams' context features."""
        features = self.league_features(league_id, season_id, as_of)
        features.update(self.team_features(
            home_id, "home", league_id, season_id, as_of))
        features.update(self.team_features(
            away_id, "away", league_id, season_id, as_of))
        return features

    def _append_team_game(
            self,
            team_id: int,
            league_id: int,
            season_id: int,
            game_date: pd.Timestamp,
            goals_for: int,
            goals_against: int) -> None:
        game = _TeamGame(
            game_date=game_date,
            clean_sheet=int(goals_against == 0),
            failed_to_score=int(goals_for == 0),
            draw=int(goals_for == goals_against),
            points=_result_points(goals_for, goals_against),
            goals_for=goals_for,
            goals_against=goals_against)
        key = (team_id, league_id, season_id)
        games = self._team_games.get(key)
        if games is None:
            self._team_games[key] = [game]
            season_key = (league_id, season_id)
            self._season_teams.setdefault(season_key, []).append(team_id)
        else:
            games.append(game)
        self._team_dates.setdefault(team_id, []).append(game_date)

    def _zero_goal_side_rate(
            self,
            league_id: int,
            season_id: int,
            as_of: pd.Timestamp) -> float:
        """Return the shrunk share of sides that scored zero.

        A side that scores zero is the opponent's clean sheet, so the
        league rate is the same reference for both team features.
        """
        prior = self._prior_rates(league_id, as_of)["zero_goal_side"]
        totals = _accumulate(
            self._seasons.get((league_id, season_id), ()), as_of, None)
        return _shrink(
            totals.zero_goal_sides / 2.0,
            totals.matches,
            prior,
            self._params.league_shrink_matches)

    def _newcomer_flag(
            self,
            team_id: int,
            league_id: int,
            season_id: int,
            as_of: pd.Timestamp) -> float:
        previous = _previous_season_id(
            self._seasons, league_id, season_id, as_of)
        if previous is None:
            return 0.0
        played = _count_team_games(
            self._team_games.get((team_id, league_id, previous), ()),
            as_of).matches
        if played:
            return 0.0
        return 1.0

    def _prior_rates(
            self,
            league_id: int,
            as_of: pd.Timestamp) -> dict[str, float]:
        days = self._params.league_prior_days
        start = as_of - pd.Timedelta(days=days)
        league_rows = self._league_matches.get(league_id, ())
        league_totals = _accumulate(league_rows, as_of, start)
        if league_totals.matches:
            return _means(league_totals)
        global_totals = _accumulate(self._global_matches, as_of, start)
        if global_totals.matches:
            return _means(global_totals)
        # Puste okno ligi i puste okno globalne zostawiają stały prior.
        return dict(DEFAULT_LEAGUE_PRIOR)


def context_match_from_row(row: Any) -> ContextMatch:
    """Map a history row or ``itertuples`` record to a context match."""
    return ContextMatch(
        match_id=int(_field(row, "id")),
        league_id=int(_field(row, "league")),
        season_id=int(_field(row, "season")),
        game_date=pd.Timestamp(_field(row, "game_date")),
        home_team=int(_field(row, "home_team")),
        away_team=int(_field(row, "away_team")),
        home_goals=int(_field(row, "home_team_goals")),
        away_goals=int(_field(row, "away_team_goals")))


def build_context_state(
        timeline: pd.DataFrame,
        as_of: date,
        params: FootballContextParams) -> FootballContextState:
    """Commit rows with ``game_date < as_of``, ordered by date then id."""
    state = FootballContextState(params)
    if timeline.empty:
        return state
    ordered = timeline.sort_values(["game_date", "id"])
    cutoff = pd.Timestamp(as_of).normalize()
    for row in ordered.itertuples(index=False):
        game_date = pd.Timestamp(row.game_date).normalize()
        if game_date >= cutoff:
            continue
        if not _goals_known(row):
            continue
        state.commit(context_match_from_row(row))
    return state


def _field(row: Any, column: str) -> Any:
    if isinstance(row, pd.Series) or isinstance(row, Mapping):
        return row[column]
    return getattr(row, column)


def _goals_known(row: Any) -> bool:
    # NaN to brak wyniku, nie mecz 0:0. Taki wiersz nie wchodzi do stanu.
    home_goals = _field(row, "home_team_goals")
    away_goals = _field(row, "away_team_goals")
    return bool(pd.notna(home_goals) and pd.notna(away_goals))


def _accumulate(
        rows: Iterable[_MatchGoals],
        as_of: pd.Timestamp,
        start: pd.Timestamp | None) -> _GoalTotals:
    """Sum matches in ``[start, as_of)``.

    ``start is None`` keeps every match before ``as_of``. Season rates
    use that form, so a match older than the prior window still counts
    toward the current season.
    """
    totals = _GoalTotals()
    for game_date, home_goals, away_goals in rows:
        if start is not None and game_date < start:
            continue
        if game_date >= as_of:
            continue
        totals.add(home_goals, away_goals)
    return totals


def _means(totals: _GoalTotals) -> dict[str, float]:
    count = totals.matches
    return {
        "home_goals": totals.home_goals / count,
        "away_goals": totals.away_goals / count,
        "btts": totals.btts / count,
        "over_25": totals.over_25 / count,
        "draw": totals.draws / count,
        "zero_goal_side": totals.zero_goal_sides / (2 * count)
    }


def _count_team_games(
        games: Iterable[_TeamGame],
        as_of: pd.Timestamp) -> _TeamCounts:
    """Sum team games with ``game_date < as_of``."""
    counts = _TeamCounts()
    for game in games:
        if game.game_date >= as_of:
            continue
        counts.matches += 1
        counts.clean_sheets += game.clean_sheet
        counts.failed_to_score += game.failed_to_score
        counts.draws += game.draw
        counts.points += game.points
        counts.goals_for += game.goals_for
        counts.goals_against += game.goals_against
    return counts


def _result_points(goals_for: int, goals_against: int) -> int:
    """Return 3, 1 or 0 from the team's own scoreline."""
    if goals_for > goals_against:
        return 3
    if goals_for == goals_against:
        return 1
    return 0


def _season_standings(
        team_games: Mapping[tuple[int, int, int], list[_TeamGame]],
        team_ids: Iterable[int],
        league_id: int,
        season_id: int,
        as_of: pd.Timestamp) -> dict[int, _TeamCounts]:
    """Return teams that already played in this league season."""
    standings: dict[int, _TeamCounts] = {}
    for team_id in team_ids:
        counts = _count_team_games(
            team_games.get((team_id, league_id, season_id), ()),
            as_of)
        if counts.matches == 0:
            continue
        standings[team_id] = counts
    return standings


def _standing_key(
        team_id: int,
        counts: _TeamCounts) -> tuple[int, int, int, int]:
    """Order a leader first: points, goal difference, goals, then id.

    A lower team id ranks higher when the other three are equal, so a
    full tie does not depend on commit order.
    """
    goal_difference = counts.goals_for - counts.goals_against
    return (
        -counts.points,
        -goal_difference,
        -counts.goals_for,
        team_id)


def _rank_pct(
        team_id: int,
        standings: Mapping[int, _TeamCounts]) -> float:
    """Map table position to ``[0, 1]``. The leader is 0.

    A side with no match yet, or a table shorter than two teams, is 0.5.
    """
    if team_id not in standings or len(standings) < 2:
        return 0.5
    ordered = sorted(
        standings,
        key=lambda team: _standing_key(team, standings[team]))
    rank = ordered.index(team_id) + 1
    return (rank - 1) / (len(standings) - 1)


def _points_per_game(
        team_id: int,
        standings: Mapping[int, _TeamCounts]) -> float:
    """Return the team's rate, the season average, or 1.35."""
    counts = standings.get(team_id)
    if counts is not None:
        return counts.points / counts.matches
    total_points = 0
    total_matches = 0
    for row in standings.values():
        total_points += row.points
        total_matches += row.matches
    if total_matches == 0:
        return _DEFAULT_POINTS_PER_GAME
    return total_points / total_matches


def _matches_in_window(
        dates: Iterable[pd.Timestamp],
        as_of: pd.Timestamp,
        fatigue_days: int) -> float:
    """Count dates in ``[as_of - fatigue_days, as_of)``."""
    start = as_of - pd.Timedelta(days=fatigue_days)
    count = 0
    for game_date in dates:
        if game_date < start or game_date >= as_of:
            continue
        count += 1
    return float(count)


def _previous_season_id(
        seasons: Mapping[tuple[int, int], list[_MatchGoals]],
        league_id: int,
        season_id: int,
        as_of: pd.Timestamp) -> int | None:
    """Return the season that started immediately before ``season_id``.

    Order is the first match before ``as_of``, then the season id. A
    season with no match yet treats the latest visible season as its
    predecessor.
    """
    visible = _seasons_by_first_match(seasons, league_id, as_of)
    if not visible:
        return None
    if season_id not in visible:
        return visible[-1]
    index = visible.index(season_id)
    if index == 0:
        return None
    return visible[index - 1]


def _seasons_by_first_match(
        seasons: Mapping[tuple[int, int], list[_MatchGoals]],
        league_id: int,
        as_of: pd.Timestamp) -> list[int]:
    # Data pierwszego meczu, potem id, żeby remis dat był stabilny.
    ordered: list[tuple[pd.Timestamp, int]] = []
    for (league, season), rows in seasons.items():
        if league != league_id:
            continue
        first = _earliest_before(rows, as_of)
        if first is None:
            continue
        ordered.append((first, season))
    ordered.sort()
    return [season for _, season in ordered]


def _earliest_before(
        rows: Iterable[_MatchGoals],
        as_of: pd.Timestamp) -> pd.Timestamp | None:
    first: pd.Timestamp | None = None
    for game_date, _, _ in rows:
        if game_date >= as_of:
            continue
        if first is None or game_date < first:
            first = game_date
    return first


def _shrink(
        season_sum: float,
        season_matches: int,
        prior: float,
        shrink_matches: float) -> float:
    """Shrink a season sum toward ``prior`` with weight ``k``."""
    return (
        season_sum + shrink_matches * prior
    ) / (season_matches + shrink_matches)
