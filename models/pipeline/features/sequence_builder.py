"""Build fixed football history windows from a team's perspective."""

from __future__ import annotations

from collections import defaultdict
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime

import numpy as np
import pandas as pd

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.registry import register_feature_builder
from models.pipeline.data.match_history_repository import fetch_finished_matches
from models.pipeline.data.match_history_repository import fetch_league_context
from models.pipeline.features.matchup_features import STATIC_FEATURE_COLUMNS
from models.pipeline.features.matchup_features import build_matchup_static
from models.pipeline.features.ratings import compute_ratings_timeline

DEFAULT_SEQUENCE_FEATURES = [
    "won",
    "drawn",
    "lost",
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "shots_for",
    "shots_against",
    "shots_on_goal_for",
    "shots_on_goal_against",
    "possession_for",
    "elo",
    "gap_att",
    "gap_def",
    "is_home",
    "btts",
    "total_goals"
]

_CZECH_STATISTICS = [
    "win_pct",
    "goals_for_avg",
    "goals_against_avg",
    "goals_for_std",
    "goals_against_std"
]


@dataclass
class _LeagueAggregate:
    """Maintain league statistics from committed historical matches."""

    count: int = 0
    home_goals: float = 0.0
    away_goals: float = 0.0
    btts: int = 0
    over_25: int = 0
    xg_sum: float = 0.0
    xg_count: int = 0

    def add(self, row: pd.Series) -> None:
        """Commit one finished match to the aggregate."""
        home_goals = _numeric_value(row, "home_team_goals", 0.0)
        away_goals = _numeric_value(row, "away_team_goals", 0.0)
        self.count += 1
        self.home_goals += home_goals
        self.away_goals += away_goals
        self.btts += int(home_goals > 0 and away_goals > 0)
        self.over_25 += int(home_goals + away_goals > 2.5)
        for column in ["home_team_xg", "away_team_xg"]:
            value = _numeric_value(row, column)
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


@dataclass
class _TrainingHistory:
    """Store bounded and cumulative state for chronological feature building."""

    window: int
    team_rows: dict[int, deque[dict[str, float]]] = field(
        default_factory=lambda: defaultdict(deque))
    last_dates: dict[int, pd.Timestamp] = field(default_factory=dict)
    h2h_rows: dict[
        tuple[int, int],
        deque[tuple[int, int, float, float]]] = field(
            default_factory=lambda: defaultdict(lambda: deque(maxlen=5)))
    leagues: dict[int, _LeagueAggregate] = field(
        default_factory=lambda: defaultdict(_LeagueAggregate))

    def sequence(
            self,
            team_id: int,
            columns: list[str]) -> np.ndarray | None:
        """Build one sequence from the bounded team history."""
        history = self.team_rows[team_id]
        if len(history) < self.window:
            return None
        perspective = pd.DataFrame(list(history)[-self.window:])
        missing = set(columns).difference(perspective.columns)
        if missing:
            raise KeyError(f"Unknown sequence features: {sorted(missing)}")
        return _impute_numeric(
            perspective[columns]).to_numpy(dtype=np.float32)

    def commit(self, row: pd.Series) -> None:
        """Commit one row after every sample at its date was built."""
        home_id = int(row["home_team"])
        away_id = int(row["away_team"])
        match_date = pd.Timestamp(row["game_date"])
        for team_id in [home_id, away_id]:
            history = self.team_rows[team_id]
            history.append(_perspective_row(row, team_id))
            while len(history) > self.window:
                history.popleft()
            self.last_dates[team_id] = match_date
        home_goals = _numeric_value(row, "home_team_goals", 0.0)
        away_goals = _numeric_value(row, "away_team_goals", 0.0)
        pair = tuple(sorted((home_id, away_id)))
        self.h2h_rows[pair].append(
            (home_id, away_id, home_goals, away_goals))
        self.leagues[int(row["league"])].add(row)


def _team_result(result: str, is_home: bool) -> tuple[float, float, float]:
    won = (is_home and result == "1") or (not is_home and result == "2")
    lost = (is_home and result == "2") or (not is_home and result == "1")
    return float(won), float(result == "X"), float(lost)


def _numeric_value(row: pd.Series, column: str, default: float = np.nan) -> float:
    value = row.get(column, default)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(numeric) if pd.notna(numeric) else float(default)


def _perspective_row(row: pd.Series, team_id: int) -> dict[str, float]:
    is_home = int(row["home_team"]) == team_id
    own = "home" if is_home else "away"
    opponent = "away" if is_home else "home"
    goals_for = _numeric_value(row, f"{own}_team_goals", 0.0)
    goals_against = _numeric_value(row, f"{opponent}_team_goals", 0.0)
    won, drawn, lost = _team_result(str(row["result"]), is_home)
    values = {
        "won": won,
        "drawn": drawn,
        "lost": lost,
        "result_points": won * 3.0 + drawn,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "xg_for": _numeric_value(row, f"{own}_team_xg"),
        "xg_against": _numeric_value(row, f"{opponent}_team_xg"),
        "shots_for": _numeric_value(row, f"{own}_team_sc"),
        "shots_against": _numeric_value(row, f"{opponent}_team_sc"),
        "shots_on_goal_for": _numeric_value(row, f"{own}_team_sog"),
        "shots_on_goal_against": _numeric_value(
            row, f"{opponent}_team_sog"),
        "possession_for": _numeric_value(row, f"{own}_team_bp"),
        "elo": _numeric_value(row, f"{own}_elo", 1500.0),
        "gap_att": _numeric_value(row, f"{own}_gap_att", 1.0),
        "gap_def": _numeric_value(row, f"{own}_gap_def", 1.0),
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
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    medians = numeric.median(axis=0).fillna(0.0)
    return numeric.fillna(medians).fillna(0.0)


def _target_rating_features(
        row: pd.Series,
        side: str) -> dict[str, float]:
    values = {
        "elo": _numeric_value(row, f"{side}_elo", 1500.0),
        "att": _numeric_value(row, f"{side}_gap_att", 1.0),
        "def": _numeric_value(row, f"{side}_gap_def", 1.0)
    }
    for statistic in _CZECH_STATISTICS:
        values[statistic] = _numeric_value(
            row, f"{side}_czech_{statistic}", 0.0)
    return values


def _h2h_features(
        history: _TrainingHistory,
        home_id: int,
        away_id: int) -> dict[str, float]:
    rows = history.h2h_rows[tuple(sorted((home_id, away_id)))]
    if not rows:
        return {key: 0.0 for key in [
            "h2h_home_goals_avg", "h2h_away_goals_avg",
            "h2h_home_wins", "h2h_draws", "h2h_away_wins",
            "h2h_btts_pct"]}
    home_goals: list[float] = []
    away_goals: list[float] = []
    for row_home, _, row_home_goals, row_away_goals in rows:
        direct = row_home == home_id
        home_goals.append(row_home_goals if direct else row_away_goals)
        away_goals.append(row_away_goals if direct else row_home_goals)
    return {
        "h2h_home_goals_avg": float(np.mean(home_goals)),
        "h2h_away_goals_avg": float(np.mean(away_goals)),
        "h2h_home_wins": float(sum(
            home > away for home, away in zip(home_goals, away_goals))),
        "h2h_draws": float(sum(
            home == away for home, away in zip(home_goals, away_goals))),
        "h2h_away_wins": float(sum(
            away > home for home, away in zip(home_goals, away_goals))),
        "h2h_btts_pct": float(np.mean([
            home > 0 and away > 0
            for home, away in zip(home_goals, away_goals)]))
    }


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


def _training_static(
        row: pd.Series,
        history: _TrainingHistory,
        league_tier: int | None,
        feature_cols: list[str]) -> np.ndarray:
    home_id = int(row["home_team"])
    away_id = int(row["away_team"])
    match_date = pd.Timestamp(row["game_date"])
    home = _target_rating_features(row, "home")
    away = _target_rating_features(row, "away")
    values = {
        "elo_home": home["elo"],
        "elo_away": away["elo"],
        "elo_diff": home["elo"] - away["elo"],
        "home_att": home["att"],
        "home_def": home["def"],
        "away_att": away["att"],
        "away_def": away["def"],
        "home_att_vs_away_def": home["att"] - away["def"],
        "away_att_vs_home_def": away["att"] - home["def"]
    }
    for statistic in _CZECH_STATISTICS:
        values[f"home_czech_{statistic}"] = home[statistic]
        values[f"away_czech_{statistic}"] = away[statistic]
    values.update(history.leagues[int(row["league"])].features())
    values.update(_h2h_features(history, home_id, away_id))
    home_rest = _prior_rest_days(history, home_id, match_date)
    away_rest = _prior_rest_days(history, away_id, match_date)
    values.update({
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "rest_days_diff": home_rest - away_rest,
        "league_tier": float(league_tier or 0)
    })
    _add_static_aliases(values)
    missing = set(feature_cols).difference(values)
    if missing:
        raise KeyError(f"Unknown static features: {sorted(missing)}")
    return np.asarray(
        [values[column] for column in feature_cols],
        dtype=np.float32)


def _prior_rest_days(
        history: _TrainingHistory,
        team_id: int,
        match_date: pd.Timestamp) -> float:
    previous = history.last_dates.get(team_id)
    if previous is None:
        return 0.0
    return float((match_date - previous).days)


def build_team_sequence(
        matches: pd.DataFrame,
        team_id: int,
        as_of_date: date | datetime,
        window: int = 8,
        feature_cols: list[str] | None = None) -> np.ndarray | None:
    """Return an oldest-to-newest numeric window or None if history is short."""
    if window <= 0:
        raise ValueError("window must be positive")
    required = {
        "home_team", "away_team", "game_date", "result",
        "home_team_goals", "away_team_goals"}
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Missing sequence columns: {sorted(missing)}")
    dates = pd.to_datetime(matches["game_date"])
    valid = (
        ((matches["home_team"] == team_id)
         | (matches["away_team"] == team_id))
        & (dates < pd.Timestamp(as_of_date))
        & matches["result"].astype(str).isin({"1", "X", "2"})
        & matches["home_team_goals"].notna()
        & matches["away_team_goals"].notna())
    history = matches.loc[valid].copy()
    if len(history) < window:
        return None
    history["_sequence_date"] = pd.to_datetime(history["game_date"])
    sort_columns = ["_sequence_date"]
    if "id" in history.columns:
        sort_columns.append("id")
    history = history.sort_values(sort_columns).tail(window)
    perspective = pd.DataFrame([
        _perspective_row(row, team_id) for _, row in history.iterrows()])
    columns = feature_cols or DEFAULT_SEQUENCE_FEATURES
    missing_features = set(columns).difference(perspective.columns)
    if missing_features:
        raise KeyError(f"Unknown sequence features: {sorted(missing_features)}")
    return _impute_numeric(perspective[columns]).to_numpy(dtype=np.float32)


def _training_label(row: pd.Series, task_type: str) -> int | tuple[int, int]:
    if task_type == "result":
        from models.pipeline.labels.football_result import label_result

        return label_result(row)
    if task_type == "btts":
        from models.pipeline.labels.football_btts import label_btts

        return label_btts(row)
    from models.pipeline.labels.football_goals_poisson import (
        label_goals_poisson)

    return label_goals_poisson(row)


def _league_id(
        history: pd.DataFrame,
        matchup: MatchupInput) -> int:
    if matchup.league_id is not None:
        return matchup.league_id
    team_rows = history.loc[
        (history["home_team"] == matchup.home_team_id)
        | (history["away_team"] == matchup.home_team_id)]
    if team_rows.empty:
        raise ValueError("league_id is required without home-team history")
    return int(team_rows.sort_values("game_date").iloc[-1]["league"])


def _league_tier(sport_id: int, league_id: int) -> int | None:
    context = fetch_league_context(sport_id, league_id)
    if context.empty or pd.isna(context.iloc[0]["tier"]):
        return None
    return int(context.iloc[0]["tier"])


@register_feature_builder("FutureEventsFeatureBuilder")
class FutureEventsFeatureBuilder:
    """Build dual sequences, static features, labels, and sample dates."""

    def build_training_batch(
            self,
            matches: pd.DataFrame,
            config: FutureEventsRunConfig) -> dict[str, object]:
        """Build chronological model inputs, skipping short histories."""
        timeline = compute_ratings_timeline(
            matches, params=config.ratings)
        league_context = fetch_league_context(config.sport_id)
        league_tiers = {
            int(row["league_id"]): (
                int(row["tier"]) if pd.notna(row["tier"]) else None)
            for _, row in league_context.iterrows()
        }
        home_sequences: list[np.ndarray] = []
        away_sequences: list[np.ndarray] = []
        static_rows: list[np.ndarray] = []
        labels: list[int | tuple[int, int]] = []
        dates: list[pd.Timestamp] = []
        history = _TrainingHistory(config.window_size)
        sequence_columns = (
            config.sequence_feature_columns or DEFAULT_SEQUENCE_FEATURES)
        static_columns = (
            config.static_feature_columns or STATIC_FEATURE_COLUMNS)
        for _, date_rows in timeline.groupby("game_date", sort=False):
            for _, row in date_rows.iterrows():
                home = history.sequence(
                    int(row["home_team"]), sequence_columns)
                away = history.sequence(
                    int(row["away_team"]), sequence_columns)
                if home is None or away is None:
                    continue
                static = _training_static(
                    row,
                    history,
                    league_tiers.get(int(row["league"])),
                    static_columns)
                home_sequences.append(home)
                away_sequences.append(away)
                static_rows.append(static)
                labels.append(_training_label(row, config.task_type))
                dates.append(pd.Timestamp(row["game_date"]))
            for _, row in date_rows.iterrows():
                history.commit(row)
        if not labels:
            raise ValueError("No matches have enough history for sequences")
        return {
            "batch": SequenceBatch(
                X_home=np.stack(home_sequences),
                X_away=np.stack(away_sequences),
                X_static=np.stack(static_rows)),
            "labels": np.asarray(labels),
            "dates": np.asarray(dates, dtype="datetime64[ns]")
        }

    def build_matchup_batch(
            self,
            matchup: MatchupInput,
            config: FutureEventsRunConfig) -> SequenceBatch:
        """Build one inference batch from database history."""
        history = fetch_finished_matches(
            config.sport_id, matchup.as_of_date)
        timeline = compute_ratings_timeline(
            history, params=config.ratings)
        home = build_team_sequence(
            timeline, matchup.home_team_id, matchup.as_of_date,
            config.window_size, config.sequence_feature_columns)
        away = build_team_sequence(
            timeline, matchup.away_team_id, matchup.as_of_date,
            config.window_size, config.sequence_feature_columns)
        if home is None or away is None:
            raise ValueError("At least one team has insufficient match history")
        league_id = _league_id(timeline, matchup)
        static = build_matchup_static(
            matchup.home_team_id,
            matchup.away_team_id,
            matchup.as_of_date,
            league_id,
            timeline,
            timeline,
            _league_tier(config.sport_id, league_id),
            config.static_feature_columns)
        return SequenceBatch(
            X_home=home[np.newaxis, ...],
            X_away=away[np.newaxis, ...],
            X_static=static[np.newaxis, ...])

    def build_prediction_batch(
            self,
            matchup: MatchupInput,
            config: FutureEventsRunConfig) -> SequenceBatch:
        """Compatibility alias for pair inference."""
        return self.build_matchup_batch(matchup, config)
