"""Incremental league context from finished football matches."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from models.pipeline.core.config import FootballContextParams


# Prior, gdy w oknie nie ma ani meczów ligi, ani meczów globalnych.
DEFAULT_LEAGUE_PRIOR = {
    "home_goals": 1.5,
    "away_goals": 1.2,
    "btts": 0.52,
    "over_25": 0.52,
    "draw": 0.26
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

    def add(self, home_goals: int, away_goals: int) -> None:
        """Add one match to the running sums."""
        self.matches += 1
        self.home_goals += home_goals
        self.away_goals += away_goals
        self.btts += int(home_goals > 0 and away_goals > 0)
        self.over_25 += int(home_goals + away_goals > 2.5)
        self.draws += int(home_goals == away_goals)


class FootballContextState:
    """Incremental league, team and table state from finished matches."""

    def __init__(self, params: FootballContextParams) -> None:
        self._params = params
        self._league_matches: dict[int, deque[_MatchGoals]] = {}
        self._global_matches: deque[_MatchGoals] = deque()
        self._seasons: dict[tuple[int, int], list[_MatchGoals]] = {}

    def commit(self, match: ContextMatch) -> None:
        """Append one finished match to the league and global history."""
        game_date = pd.Timestamp(match.game_date).normalize()
        scored = (game_date, int(match.home_goals), int(match.away_goals))
        self._league_matches.setdefault(
            match.league_id, deque()).append(scored)
        self._global_matches.append(scored)
        season_key = (match.league_id, match.season_id)
        self._seasons.setdefault(season_key, []).append(scored)

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
        "draw": totals.draws / count
    }


def _shrink(
        season_sum: float,
        season_matches: int,
        prior: float,
        shrink_matches: float) -> float:
    """Shrink a season sum toward ``prior`` with weight ``k``."""
    return (
        season_sum + shrink_matches * prior
    ) / (season_matches + shrink_matches)
