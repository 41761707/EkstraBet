"""In-memory chronological feature state for season simulation trials."""

from __future__ import annotations

from collections import defaultdict
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from typing import Sequence

import numpy as np
import pandas as pd

from models.pipeline.features.matchup_features import STATIC_FEATURE_COLUMNS
from models.pipeline.features.ratings.czech import CzechParams
from models.pipeline.features.ratings.elo import EloParams
from models.pipeline.features.ratings.gap import GapParams
from models.pipeline.features.ratings.state import RatingState
from models.pipeline.features.sequence_builder import DEFAULT_SEQUENCE_FEATURES
from models.pipeline.simulation.config import SeasonSimulationConfig

_CZECH_STATISTICS = [
    "win_pct",
    "goals_for_avg",
    "goals_against_avg",
    "goals_for_std",
    "goals_against_std"
]
_HISTORY_REQUIRED = {
    "home_team",
    "away_team",
    "game_date",
    "result",
    "home_team_goals",
    "away_team_goals",
    "league"
}


@dataclass(frozen=True)
class SimulatedMatchResult:
    """Goals (and optional stats) for one fixture within a round."""

    home_team_id: int
    away_team_id: int
    home_goals: int
    away_goals: int
    home_xg: float = float("nan")
    away_xg: float = float("nan")
    home_shots: float = float("nan")
    away_shots: float = float("nan")
    home_shots_on_goal: float = float("nan")
    away_shots_on_goal: float = float("nan")
    home_possession: float = float("nan")
    away_possession: float = float("nan")
    league_id: int | None = None


@dataclass(frozen=True)
class BuiltMatchupFeatures:
    """Per-matchup tensors ready to stack into a SequenceBatch."""

    home_sequence: np.ndarray
    away_sequence: np.ndarray
    static_features: np.ndarray


@dataclass
class _LeagueAggregate:
    """Rolling league totals from committed (real or simulated) matches."""

    count: int = 0
    home_goals: float = 0.0
    away_goals: float = 0.0
    btts: int = 0
    over_25: int = 0
    xg_sum: float = 0.0
    xg_count: int = 0

    def add(
            self,
            home_goals: float,
            away_goals: float,
            home_xg: float,
            away_xg: float) -> None:
        """Commit one finished match into the aggregate."""
        self.count += 1
        self.home_goals += home_goals
        self.away_goals += away_goals
        self.btts += int(home_goals > 0 and away_goals > 0)
        self.over_25 += int(home_goals + away_goals > 2.5)
        for value in (home_xg, away_xg):
            if np.isfinite(value):
                self.xg_sum += value
                self.xg_count += 1

    def features(self) -> dict[str, float]:
        """Return current rolling league features."""
        denominator = max(self.count, 1)
        return {
            "league_avg_home_goals": self.home_goals / denominator,
            "league_avg_away_goals": self.away_goals / denominator,
            "league_avg_goals": (
                self.home_goals + self.away_goals) / denominator,
            "league_btts_pct": self.btts / denominator,
            "league_over_25_pct": self.over_25 / denominator,
            "league_avg_xg": (
                self.xg_sum / self.xg_count if self.xg_count else 0.0)
        }

    def copy(self) -> _LeagueAggregate:
        """Return an independent copy of aggregate counters."""
        return _LeagueAggregate(
            count=self.count,
            home_goals=self.home_goals,
            away_goals=self.away_goals,
            btts=self.btts,
            over_25=self.over_25,
            xg_sum=self.xg_sum,
            xg_count=self.xg_count)


class ChronologicalFeatureState:
    """Season feature state with warm-start history and in-memory commits.

    Seed once from finished matches before the season anchor, then call
    ``build_matchup_features`` for every fixture of a round before
    ``commit_round`` so same-round matches never leak into each other.
    """

    def __init__(
            self,
            window: int,
            league_id: int,
            league_tier: int | None = None,
            sequence_feature_columns: list[str] | None = None,
            static_feature_columns: list[str] | None = None,
            ratings: RatingState | None = None) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        self._window = window
        self._league_id = league_id
        self._league_tier = league_tier
        self._sequence_columns = list(
            sequence_feature_columns or DEFAULT_SEQUENCE_FEATURES)
        self._static_columns = list(
            static_feature_columns or STATIC_FEATURE_COLUMNS)
        self._ratings = ratings or RatingState()
        self._team_ids: tuple[int, ...] = ()
        self._season_anchor: date | None = None
        self._team_rows: dict[int, deque[dict[str, float]]] = defaultdict(
            deque)
        self._last_dates: dict[int, pd.Timestamp] = {}
        self._h2h_rows: dict[
            tuple[int, int],
            deque[tuple[int, int, float, float]]] = defaultdict(
                lambda: deque(maxlen=5))
        self._leagues: dict[int, _LeagueAggregate] = defaultdict(
            _LeagueAggregate)

    @property
    def window(self) -> int:
        """Return the fixed sequence window length."""
        return self._window

    @property
    def league_id(self) -> int:
        """Return the league this state tracks for static aggregates."""
        return self._league_id

    @property
    def season_anchor(self) -> date | None:
        """Return the warm-start cutoff date when known."""
        return self._season_anchor

    @property
    def ratings(self) -> RatingState:
        """Return the embedded rating maps."""
        return self._ratings

    def seed_history(self, matches: pd.DataFrame) -> None:
        """Replay finished prior-season matches chronologically in memory."""
        if matches is None or matches.empty:
            return
        missing = _HISTORY_REQUIRED.difference(matches.columns)
        if missing:
            raise KeyError(
                f"Missing history columns: {sorted(missing)}")
        valid = matches.loc[
            matches["result"].astype(str).isin({"1", "X", "2"})
            & matches["home_team_goals"].notna()
            & matches["away_team_goals"].notna()].copy()
        if valid.empty:
            return
        sort_columns = ["game_date"]
        if "id" in valid.columns:
            sort_columns.append("id")
        valid = valid.sort_values(sort_columns)
        for game_date, group in valid.groupby("game_date", sort=False):
            self._commit_date_group(group, pd.Timestamp(game_date))

    def build_matchup_features(
            self,
            home_team_id: int,
            away_team_id: int,
            synthetic_date: date | datetime) -> BuiltMatchupFeatures | None:
        """Build sequences and static features without committing state.

        Returns ``None`` when either side still has fewer than ``window``
        committed matches after warm-start (e.g. a brand-new club).
        """
        match_date = pd.Timestamp(synthetic_date)
        home_sequence = self._sequence(home_team_id)
        away_sequence = self._sequence(away_team_id)
        if home_sequence is None or away_sequence is None:
            return None
        rating_snap = self._ratings.snapshot(home_team_id, away_team_id)
        static = self._static_features(
            home_team_id, away_team_id, match_date, rating_snap)
        return BuiltMatchupFeatures(
            home_sequence=home_sequence,
            away_sequence=away_sequence,
            static_features=static)

    def commit_round(
            self,
            results: Sequence[SimulatedMatchResult],
            synthetic_date: date | datetime) -> None:
        """Commit every fixture of one round after all features were built."""
        match_date = pd.Timestamp(synthetic_date)
        # najpierw wszystkie snapshoty, potem commity — bez leakage w kolejce
        snapshots = [
            self._ratings.snapshot(
                result.home_team_id, result.away_team_id)
            for result in results]
        for result, rating_snap in zip(results, snapshots):
            league_id = (
                result.league_id
                if result.league_id is not None else self._league_id)
            self._commit_one(result, match_date, rating_snap, league_id)

    def copy(self) -> ChronologicalFeatureState:
        """Return an independent deep copy for one simulation trial."""
        cloned = ChronologicalFeatureState(
            window=self._window,
            league_id=self._league_id,
            league_tier=self._league_tier,
            sequence_feature_columns=list(self._sequence_columns),
            static_feature_columns=list(self._static_columns),
            ratings=self._ratings.copy())
        cloned._team_ids = self._team_ids
        cloned._season_anchor = self._season_anchor
        cloned._team_rows = defaultdict(deque)
        for team_id, rows in self._team_rows.items():
            cloned._team_rows[team_id] = deque(
                deepcopy(row) for row in rows)
        cloned._last_dates = dict(self._last_dates)
        cloned._h2h_rows = defaultdict(lambda: deque(maxlen=5))
        for pair, rows in self._h2h_rows.items():
            cloned._h2h_rows[pair] = deque(rows, maxlen=5)
        cloned._leagues = defaultdict(_LeagueAggregate)
        for league_id, aggregate in self._leagues.items():
            cloned._leagues[league_id] = aggregate.copy()
        return cloned

    def _commit_date_group(
            self,
            group: pd.DataFrame,
            match_date: pd.Timestamp) -> None:
        items: list[tuple[SimulatedMatchResult, int]] = []
        for _, row in group.iterrows():
            items.append((
                _result_from_history_row(row),
                int(row["league"])))
        snapshots = [
            self._ratings.snapshot(
                result.home_team_id, result.away_team_id)
            for result, _ in items]
        for (result, league_id), rating_snap in zip(items, snapshots):
            self._commit_one(result, match_date, rating_snap, league_id)

    def _sequence(self, team_id: int) -> np.ndarray | None:
        history = self._team_rows[team_id]
        if len(history) < self._window:
            return None
        perspective = pd.DataFrame(list(history)[-self._window:])
        missing = set(self._sequence_columns).difference(perspective.columns)
        if missing:
            raise KeyError(
                f"Unknown sequence features: {sorted(missing)}")
        return _impute_numeric(
            perspective[self._sequence_columns]).to_numpy(dtype=np.float32)

    def _static_features(
            self,
            home_id: int,
            away_id: int,
            match_date: pd.Timestamp,
            rating_snap: dict[str, float]) -> np.ndarray:
        values = {
            "elo_home": rating_snap["home_elo"],
            "elo_away": rating_snap["away_elo"],
            "elo_diff": (
                rating_snap["home_elo"] - rating_snap["away_elo"]),
            "home_att": rating_snap["home_gap_att"],
            "home_def": rating_snap["home_gap_def"],
            "away_att": rating_snap["away_gap_att"],
            "away_def": rating_snap["away_gap_def"],
            "home_att_vs_away_def": (
                rating_snap["home_gap_att"]
                - rating_snap["away_gap_def"]),
            "away_att_vs_home_def": (
                rating_snap["away_gap_att"]
                - rating_snap["home_gap_def"])
        }
        for statistic in _CZECH_STATISTICS:
            values[f"home_czech_{statistic}"] = rating_snap[
                f"home_czech_{statistic}"]
            values[f"away_czech_{statistic}"] = rating_snap[
                f"away_czech_{statistic}"]
        values.update(self._leagues[self._league_id].features())
        values.update(self._h2h_features(home_id, away_id))
        home_rest = self._prior_rest_days(home_id, match_date)
        away_rest = self._prior_rest_days(away_id, match_date)
        values.update({
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "rest_days_diff": home_rest - away_rest,
            "league_tier": float(self._league_tier or 0)
        })
        _add_static_aliases(values)
        missing = set(self._static_columns).difference(values)
        if missing:
            raise KeyError(f"Unknown static features: {sorted(missing)}")
        return np.asarray(
            [values[column] for column in self._static_columns],
            dtype=np.float32)

    def _commit_one(
            self,
            result: SimulatedMatchResult,
            match_date: pd.Timestamp,
            rating_snap: dict[str, float],
            league_id: int) -> None:
        home_id = result.home_team_id
        away_id = result.away_team_id
        self._ratings.commit(
            home_id, away_id, result.home_goals, result.away_goals)
        for team_id in (home_id, away_id):
            history = self._team_rows[team_id]
            history.append(
                _perspective_row(result, team_id, rating_snap))
            while len(history) > self._window:
                history.popleft()
            self._last_dates[team_id] = match_date
        pair = tuple(sorted((home_id, away_id)))
        self._h2h_rows[pair].append((
            home_id,
            away_id,
            float(result.home_goals),
            float(result.away_goals)))
        self._leagues[league_id].add(
            float(result.home_goals),
            float(result.away_goals),
            result.home_xg,
            result.away_xg)

    def _h2h_features(
            self, home_id: int, away_id: int) -> dict[str, float]:
        rows = self._h2h_rows[tuple(sorted((home_id, away_id)))]
        if not rows:
            return {key: 0.0 for key in [
                "h2h_home_goals_avg", "h2h_away_goals_avg",
                "h2h_home_wins", "h2h_draws", "h2h_away_wins",
                "h2h_btts_pct"]}
        home_goals: list[float] = []
        away_goals: list[float] = []
        for row_home, _, row_home_goals, row_away_goals in rows:
            direct = row_home == home_id
            home_goals.append(
                row_home_goals if direct else row_away_goals)
            away_goals.append(
                row_away_goals if direct else row_home_goals)
        return {
            "h2h_home_goals_avg": float(np.mean(home_goals)),
            "h2h_away_goals_avg": float(np.mean(away_goals)),
            "h2h_home_wins": float(sum(
                home > away for home, away in zip(
                    home_goals, away_goals))),
            "h2h_draws": float(sum(
                home == away for home, away in zip(
                    home_goals, away_goals))),
            "h2h_away_wins": float(sum(
                away > home for home, away in zip(
                    home_goals, away_goals))),
            "h2h_btts_pct": float(np.mean([
                home > 0 and away > 0
                for home, away in zip(home_goals, away_goals)]))
        }

    def _prior_rest_days(
            self,
            team_id: int,
            match_date: pd.Timestamp) -> float:
        previous = self._last_dates.get(team_id)
        if previous is None:
            return 0.0
        return float((match_date - previous).days)


def build_season_start_state(
        team_ids: Sequence[int],
        config: SeasonSimulationConfig,
        *,
        window: int = 8,
        league_tier: int | None = None,
        sequence_feature_columns: list[str] | None = None,
        static_feature_columns: list[str] | None = None,
        elo_params: EloParams | None = None,
        gap_params: GapParams | None = None,
        czech_params: CzechParams | None = None,
        prior_matches: pd.DataFrame | None = None,
        season_anchor: date | None = None,
        load_history: bool = True) -> ChronologicalFeatureState:
    """Create day-0 standings state with warm-started features/ratings.

    Prior finished matches (``game_date < season_anchor``) are replayed
    once before trials are copied. Pass ``prior_matches`` in tests to
    avoid DB access; production leaves it ``None`` and loads history.
    """
    if not team_ids:
        raise ValueError("team_ids must not be empty")
    unique_ids = tuple(dict.fromkeys(int(team_id) for team_id in team_ids))
    if len(unique_ids) < 2:
        raise ValueError("team_ids must contain at least two teams")
    anchor = season_anchor
    if load_history:
        history, anchor = _load_warm_start_history(
            config, prior_matches, season_anchor)
    elif prior_matches is None:
        history = pd.DataFrame()
    else:
        history = prior_matches
    ratings = RatingState(elo_params, gap_params, czech_params)
    state = ChronologicalFeatureState(
        window=window,
        league_id=config.league_id,
        league_tier=league_tier,
        sequence_feature_columns=sequence_feature_columns,
        static_feature_columns=static_feature_columns,
        ratings=ratings)
    state._team_ids = unique_ids
    state._season_anchor = anchor
    state.seed_history(history)
    return state


def _load_warm_start_history(
        config: SeasonSimulationConfig,
        prior_matches: pd.DataFrame | None,
        season_anchor: date | None) -> tuple[pd.DataFrame, date]:
    # import lokalny — seed raz przed trialami, nie w pętli Monte Carlo
    from models.pipeline.data.match_history_repository import (
        fetch_finished_matches)
    from models.pipeline.data.match_history_repository import (
        resolve_season_anchor_date)

    anchor = season_anchor or resolve_season_anchor_date(
        config.season_id, config.league_id)
    if prior_matches is None:
        prior_matches = fetch_finished_matches(config.sport_id, anchor)
    return prior_matches, anchor


def _result_from_history_row(row: pd.Series) -> SimulatedMatchResult:
    return SimulatedMatchResult(
        home_team_id=int(row["home_team"]),
        away_team_id=int(row["away_team"]),
        home_goals=int(row["home_team_goals"]),
        away_goals=int(row["away_team_goals"]),
        home_xg=_optional_float(row, "home_team_xg"),
        away_xg=_optional_float(row, "away_team_xg"),
        home_shots=_optional_float(row, "home_team_sc"),
        away_shots=_optional_float(row, "away_team_sc"),
        home_shots_on_goal=_optional_float(row, "home_team_sog"),
        away_shots_on_goal=_optional_float(row, "away_team_sog"),
        home_possession=_optional_float(row, "home_team_bp"),
        away_possession=_optional_float(row, "away_team_bp"),
        league_id=int(row["league"]))


def _optional_float(row: pd.Series, column: str) -> float:
    if column not in row.index:
        return float("nan")
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else float("nan")


def _result_code(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "1"
    if home_goals < away_goals:
        return "2"
    return "X"


def _team_result(
        result: str, is_home: bool) -> tuple[float, float, float]:
    won = (is_home and result == "1") or (not is_home and result == "2")
    lost = (is_home and result == "2") or (not is_home and result == "1")
    return float(won), float(result == "X"), float(lost)


def _perspective_row(
        result: SimulatedMatchResult,
        team_id: int,
        rating_snap: dict[str, float]) -> dict[str, float]:
    is_home = result.home_team_id == team_id
    own = "home" if is_home else "away"
    goals_for = float(
        result.home_goals if is_home else result.away_goals)
    goals_against = float(
        result.away_goals if is_home else result.home_goals)
    won, drawn, lost = _team_result(
        _result_code(result.home_goals, result.away_goals), is_home)
    values = {
        "won": won,
        "drawn": drawn,
        "lost": lost,
        "result_points": won * 3.0 + drawn,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "xg_for": result.home_xg if is_home else result.away_xg,
        "xg_against": result.away_xg if is_home else result.home_xg,
        "shots_for": (
            result.home_shots if is_home else result.away_shots),
        "shots_against": (
            result.away_shots if is_home else result.home_shots),
        "shots_on_goal_for": (
            result.home_shots_on_goal
            if is_home else result.away_shots_on_goal),
        "shots_on_goal_against": (
            result.away_shots_on_goal
            if is_home else result.home_shots_on_goal),
        "possession_for": (
            result.home_possession
            if is_home else result.away_possession),
        "elo": rating_snap[f"{own}_elo"],
        "gap_att": rating_snap[f"{own}_gap_att"],
        "gap_def": rating_snap[f"{own}_gap_def"],
        "is_home": float(is_home),
        "btts": float(goals_for > 0 and goals_against > 0),
        "total_goals": goals_for + goals_against
    }
    values.update({
        "shots": values["shots_for"],
        "shots_on_goal": values["shots_on_goal_for"],
        "possession": values["possession_for"],
        "elo_before": values["elo"],
        "gap_attack_before": values["gap_att"],
        "gap_defense_before": values["gap_def"]
    })
    return values


def _impute_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    # mediana okna; gdy całe okno puste (symulacja bez xG) → 0.0
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    medians = numeric.median(axis=0).fillna(0.0)
    return numeric.fillna(medians).fillna(0.0)


def _add_static_aliases(values: dict[str, float]) -> None:
    h2h_count = max(
        values["h2h_home_wins"]
        + values["h2h_draws"]
        + values["h2h_away_wins"],
        1.0)
    values.update({
        "home_attack": values["home_att"],
        "home_defense": values["home_def"],
        "away_attack": values["away_att"],
        "away_defense": values["away_def"],
        "home_attack_away_defense": values["home_att_vs_away_def"],
        "away_attack_home_defense": values["away_att_vs_home_def"],
        "home_czech_win_rate": values["home_czech_win_pct"],
        "away_czech_win_rate": values["away_czech_win_pct"],
        "league_btts_rate": values["league_btts_pct"],
        "league_over_25_rate": values["league_over_25_pct"],
        "h2h_home_win_rate": values["h2h_home_wins"] / h2h_count,
        "h2h_draw_rate": values["h2h_draws"] / h2h_count
    })
