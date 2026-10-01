"""Logistic model of which goalie starts an NHL game.

Historical ``hockey_match_rosters`` rows store only the starter
(``G``, ``line=1``), so each team-game is expanded to a candidate
pool: goalies who started for that club in the previous ``pool_games``
games, plus the goalie who actually started this one. The label is 1
only for that starter. Features use starts strictly before the slate,
then the slate is observed.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.config import REPO_ROOT
from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import TrainingReport
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_matches)
from models.pipeline.features.hockey.ratings import HOCKEY_ELO_INITIAL
from models.pipeline.features.hockey.ratings import (
    build_hockey_team_ratings)


logger = logging.getLogger(__name__)

GOALIE_START_TASK = "goalie_start"
GOALIE_POSITION = "G"
STARTING_LINE = 1
STARTED_LABEL = 1
DEFAULT_POOL_GAMES = 20
DEFAULT_START_SHARE_GAMES = 10
DEFAULT_RECENT_START_DAYS = 4
DEFAULT_DAYS_SINCE_CAP = 60
# Sezon 4 w matches to 2020/21: krótki sezon grany tylko w dywizjach.
_DEFAULT_LOW_WEIGHT_SEASONS = {4: 0.5}
_FINISHED_RESULTS = frozenset({"1", "X", "2"})
_MAX_LOGISTIC_ITERATIONS = 1000

GOALIE_START_FEATURES = [
    "start_share_last_10",
    "started_yesterday",
    "days_since_last_start",
    "starts_last_4_days",
    "is_b2b_second_game",
    "opponent_elo"]
_IDENTITY_COLUMNS = [
    "match_id",
    "team_id",
    "player_id",
    "game_date",
    "season",
    "started"]
_MATCH_COLUMNS = [
    "match_id",
    "game_date",
    "season",
    "home_team",
    "away_team"]
_ROSTER_COLUMNS = [
    "match_id",
    "team_id",
    "player_id",
    "position",
    "line"]


@dataclass(frozen=True)
class GoalieStartConfig:
    """Windows and the season held out of the reported fit."""

    pool_games: int = DEFAULT_POOL_GAMES
    start_share_games: int = DEFAULT_START_SHARE_GAMES
    recent_start_days: int = DEFAULT_RECENT_START_DAYS
    days_since_start_cap: int = DEFAULT_DAYS_SINCE_CAP
    league_id: int = 45
    test_season: int = 12
    random_state: int = 42
    opponent_elo_prior: float = HOCKEY_ELO_INITIAL
    low_weight_seasons: dict[int, float] = field(
        default_factory=lambda: dict(_DEFAULT_LOW_WEIGHT_SEASONS))

    def __post_init__(self) -> None:
        if self.pool_games < 1:
            raise ValueError("pool_games must be positive")
        if self.start_share_games < 1:
            raise ValueError("start_share_games must be positive")
        if self.recent_start_days < 1:
            raise ValueError("recent_start_days must be positive")
        if self.days_since_start_cap < 1:
            raise ValueError("days_since_start_cap must be positive")
        if not np.isfinite(self.opponent_elo_prior):
            raise ValueError("opponent_elo_prior must be finite")
        _require_season_weights(self.low_weight_seasons)


@dataclass(frozen=True)
class GoalieStartRun:
    """Config file plus the artifact location for one training run."""

    model_name: str
    model_version: str
    sport_id: int
    artifact_dir: Path
    config: GoalieStartConfig
    config_path: Path


class GoalieStartHistory:
    """As-of start memory for one league.

    Call ``feature_row`` for every candidate on a slate, then
    ``observe`` those starts. A later read of an earlier date, or a
    read after that slate was observed, raises.
    """

    def __init__(
            self,
            config: GoalieStartConfig | None = None) -> None:
        self.config = config or GoalieStartConfig()
        depth = max(
            self.config.pool_games,
            self.config.start_share_games)
        self._memory_games = depth
        self._team_starts: dict[int, deque[tuple[date, int]]] = {}
        self._player_starts: dict[int, deque[date]] = {}
        self._last_date: datetime | None = None
        self._closed_date: datetime | None = None

    @classmethod
    def from_starts(
            cls,
            starts: pd.DataFrame,
            config: GoalieStartConfig | None = None
    ) -> GoalieStartHistory:
        """Replay starters in chronological order, one slate at a time."""
        history = cls(config)
        _require_columns(starts, ["team_id", "player_id", "game_date"])
        if starts.empty:
            return history
        sort_columns = ["game_date", "team_id"]
        if "match_id" in starts.columns:
            sort_columns = ["game_date", "match_id", "team_id"]
        ordered = starts.sort_values(sort_columns, kind="mergesort")
        for game_date, group in ordered.groupby("game_date", sort=False):
            for row in group.itertuples(index=False):
                history.observe(
                    int(row.team_id),
                    int(row.player_id),
                    game_date)
        return history

    def candidate_ids(self, team_id: int, starter_id: int) -> list[int]:
        """Recent starters for the club, always including ``starter_id``."""
        memory = self._team_starts.get(int(team_id))
        window: list[tuple[date, int]] = []
        if memory is not None:
            window = list(memory)[-self.config.pool_games:]
        pool: list[int] = []
        for _day, player_id in window:
            if player_id not in pool:
                pool.append(player_id)
        starter = int(starter_id)
        if starter not in pool:
            pool.append(starter)
        return pool

    def feature_row(
            self,
            team_id: int,
            player_id: int,
            game_date: datetime,
            opponent_elo: float) -> dict[str, float]:
        """Return pre-slate features for one candidate goalie."""
        moment = self._accept(game_date, reading=True)
        return self._features(
            int(team_id),
            int(player_id),
            moment.date(),
            float(opponent_elo))

    def observe(
            self,
            team_id: int,
            starter_id: int,
            game_date: datetime) -> None:
        """Record one start after its pre-match features were read."""
        moment = self._accept(game_date, reading=False)
        day = moment.date()
        team_memory = self._team_memory(int(team_id))
        team_memory.append((day, int(starter_id)))
        starts = self._player_starts.setdefault(int(starter_id), deque())
        starts.append(day)
        self._closed_date = moment

    def _features(
            self,
            team_id: int,
            player_id: int,
            day: date,
            opponent_elo: float) -> dict[str, float]:
        team_starts = self._recent_team_starts(team_id)
        share_window = team_starts[-self.config.start_share_games:]
        share = _start_share(share_window, player_id)
        player_starts = self._player_starts.get(player_id, deque())
        days_since, started_yesterday = _rest_features(
            player_starts,
            day,
            self.config.days_since_start_cap)
        return {
            "start_share_last_10": share,
            "started_yesterday": float(started_yesterday),
            "days_since_last_start": float(days_since),
            "starts_last_4_days": float(_starts_in_window(
                player_starts,
                day,
                self.config.recent_start_days)),
            "is_b2b_second_game": float(_team_played_yesterday(
                team_starts,
                day)),
            "opponent_elo": float(opponent_elo)}

    def _recent_team_starts(self, team_id: int) -> list[tuple[date, int]]:
        memory = self._team_starts.get(team_id)
        if memory is None:
            return []
        return list(memory)

    def _team_memory(self, team_id: int) -> deque[tuple[date, int]]:
        memory = self._team_starts.get(team_id)
        if memory is None:
            memory = deque(maxlen=self._memory_games)
            self._team_starts[team_id] = memory
        return memory

    def _accept(self, game_date: datetime, *, reading: bool) -> datetime:
        moment = _as_datetime(game_date)
        if self._last_date is not None and moment < self._last_date:
            raise ValueError(
                "Goalie start history cannot move backwards. "
                f"Got {moment} after {self._last_date}.")
        if (
                reading
                and self._closed_date is not None
                and moment <= self._closed_date):
            raise ValueError(
                "Goalie start features cannot be read after that "
                "slate was observed.")
        self._last_date = moment
        return moment


class GoalieStartModel:
    """Scaled logistic regression of P(this goalie starts)."""

    def __init__(
            self,
            config: GoalieStartConfig | None = None) -> None:
        self.config = config or GoalieStartConfig()
        self.feature_columns = list(GOALIE_START_FEATURES)
        self._pipeline: Pipeline | None = None

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series | np.ndarray,
            sample_weight: np.ndarray | pd.Series | None = None
    ) -> GoalieStartModel:
        """Fit on candidate rows. Labels are 1 for the starter."""
        matrix = _feature_matrix(features, self.feature_columns)
        target = _binary_labels(labels, len(features))
        model = LogisticRegression(
            max_iter=_MAX_LOGISTIC_ITERATIONS,
            random_state=self.config.random_state)
        self._pipeline = Pipeline(steps=[
            ("scaler", StandardScaler()),
            ("model", model)])
        weights = _fit_weights(sample_weight, len(features))
        if weights is None:
            self._pipeline.fit(matrix, target)
        else:
            self._pipeline.fit(
                matrix, target, model__sample_weight=weights)
        return self

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return P(start) aligned with ``features``."""
        if self._pipeline is None:
            raise RuntimeError("GoalieStartModel is not fitted")
        matrix = _feature_matrix(features, self.feature_columns)
        probabilities = self._pipeline.predict_proba(matrix)
        model = self._pipeline.named_steps["model"]
        classes = [int(label) for label in model.classes_]
        if STARTED_LABEL not in classes:
            return np.zeros(len(features), dtype=float)
        column = classes.index(STARTED_LABEL)
        return probabilities[:, column]


def normalize_start_probabilities(
        frame: pd.DataFrame,
        probabilities: np.ndarray) -> np.ndarray:
    """Scale raw start probabilities into weights that sum to 1.

    Each ``(match_id, team_id)`` group is divided by its own sum. A
    group of all zeros is split evenly. Starter selection and AUC
    stay on the unscaled ``predict_proba`` values.
    """
    if len(probabilities) != len(frame):
        raise ValueError(
            "probabilities must match the candidate frame")
    _require_columns(frame, ["match_id", "team_id"])
    raw = np.asarray(probabilities, dtype=float)
    if not np.isfinite(raw).all():
        raise ValueError("start probabilities must be finite")
    weights = raw.copy()
    if len(weights) == 0:
        return weights
    keys = pd.DataFrame({
        "match_id": frame["match_id"].astype(int).to_numpy(),
        "team_id": frame["team_id"].astype(int).to_numpy()})
    grouped = keys.groupby(["match_id", "team_id"], sort=False)
    for positions in grouped.indices.values():
        _normalize_group(weights, np.asarray(positions, dtype=int))
    return weights


def build_goalie_start_frame(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        config: GoalieStartConfig | None = None,
        ratings: pd.DataFrame | None = None) -> pd.DataFrame:
    """Expand each known starter into the club's candidate pool.

    ``ratings`` supplies pre-match ``home_elo`` and ``away_elo``.
    Without it every opponent uses ``opponent_elo_prior``.
    """
    settings = config or GoalieStartConfig()
    games = _team_games_with_starters(matches, rosters, ratings, settings)
    if games.empty:
        return _empty_frame()
    return _walk_slates(games, settings)


def score_goalie_starts(
        frame: pd.DataFrame,
        probabilities: np.ndarray) -> dict[str, object]:
    """AUC plus how often the highest P(start) is the real starter.

    Ties keep the smaller ``player_id``. Contested accuracy ignores
    team-games that had only one candidate.
    """
    if len(probabilities) != len(frame):
        raise ValueError(
            "probabilities must match the candidate frame")
    _require_columns(frame, ["match_id", "team_id", "player_id", "started"])
    labels = frame["started"].to_numpy(dtype=int)
    if len(np.unique(labels)) < 2:
        raise ValueError("AUC needs both starting and backup rows")
    selection = _selection_accuracy(frame, np.asarray(
        probabilities, dtype=float))
    return {
        "auc": float(roc_auc_score(labels, probabilities)),
        "starter_selection_accuracy": selection[
            "starter_selection_accuracy"],
        "starter_selection_accuracy_contested": selection[
            "starter_selection_accuracy_contested"],
        "n_team_games": selection["n_team_games"],
        "n_contested_team_games": selection["n_contested_team_games"],
        "n_rows": int(len(frame))}


def is_goalie_start_config(path: Path) -> bool:
    """True when the JSON file is a goalie-start training config."""
    config_path = Path(path)
    if not config_path.is_file():
        return False
    try:
        with config_path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(raw, dict):
        return False
    return raw.get("task_type") == GOALIE_START_TASK


def load_goalie_start_run(path: Path) -> GoalieStartRun:
    """Load and validate a ``hockey_goalie_start_v1`` config."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Goalie start config must be a JSON object")
    if raw.get("task_type") != GOALIE_START_TASK:
        raise ValueError(
            "Goalie start config requires task_type goalie_start")
    if int(raw.get("sport_id", 0)) != 2:
        raise ValueError("Goalie start config requires sport_id=2")
    model_name = str(raw.get("model_name", "")).strip()
    if not model_name:
        raise ValueError("model_name is required")
    artifact_dir = raw.get("artifact_dir")
    if not artifact_dir:
        raise ValueError("artifact_dir is required")
    nested = raw.get("goalie_start", {})
    if not isinstance(nested, dict):
        raise ValueError("goalie_start must be an object")
    return GoalieStartRun(
        model_name=model_name,
        model_version=str(raw.get("model_version", "1.0.0")),
        sport_id=2,
        artifact_dir=_resolve_artifact_dir(artifact_dir),
        config=_config_from_mapping(nested),
        config_path=config_path)


def train_goalie_start(config_path: Path) -> TrainingReport:
    """Fit the holdout, save a full-sample artifact, report 2025/26."""
    run = load_goalie_start_run(config_path)
    matches, rosters, ratings = _load_league(run.config.league_id)
    frame, skipped_matches, skipped_team_games = _candidate_frame(
        matches, rosters, ratings, run.config)
    holdout_rows, probabilities, n_train = _holdout_probabilities(
        frame, run.config)
    metrics = score_goalie_starts(holdout_rows, probabilities)
    _annotate_holdout(metrics, run.config, n_train, len(holdout_rows))
    metrics["n_skipped_team_games"] = skipped_team_games
    production = GoalieStartModel(run.config)
    production.fit(
        frame,
        frame["started"],
        sample_weight=_season_weights(frame, run.config))
    _save_run(run, production, metrics)
    logger.info(
        "Goalie start holdout season %s AUC %.4f, "
        "starter accuracy %.4f, contested %.4f",
        run.config.test_season,
        metrics["auc"],
        metrics["starter_selection_accuracy"],
        metrics["starter_selection_accuracy_contested"])
    return TrainingReport(
        model_name=run.model_name,
        model_version=run.model_version,
        artifact_dir=str(run.artifact_dir),
        metrics=metrics,
        feature_columns=list(GOALIE_START_FEATURES),
        n_train=n_train,
        n_test=int(len(holdout_rows)),
        skipped_matches=skipped_matches)


def evaluate_goalie_start(config_path: Path) -> EvaluationReport:
    """Recompute the season holdout without writing artifacts."""
    run = load_goalie_start_run(config_path)
    matches, rosters, ratings = _load_league(run.config.league_id)
    frame, skipped_matches, skipped_team_games = _candidate_frame(
        matches, rosters, ratings, run.config)
    holdout_rows, probabilities, n_train = _holdout_probabilities(
        frame, run.config)
    metrics = score_goalie_starts(holdout_rows, probabilities)
    _annotate_holdout(metrics, run.config, n_train, len(holdout_rows))
    metrics["n_skipped_team_games"] = skipped_team_games
    return EvaluationReport(
        model_name=run.model_name,
        model_version=run.model_version,
        metrics=metrics,
        n_samples=int(len(holdout_rows)),
        skipped_matches=skipped_matches)


def _config_from_mapping(raw: dict[str, object]) -> GoalieStartConfig:
    return GoalieStartConfig(
        pool_games=int(raw.get("pool_games", DEFAULT_POOL_GAMES)),
        start_share_games=int(raw.get(
            "start_share_games", DEFAULT_START_SHARE_GAMES)),
        recent_start_days=int(raw.get(
            "recent_start_days", DEFAULT_RECENT_START_DAYS)),
        days_since_start_cap=int(raw.get(
            "days_since_start_cap", DEFAULT_DAYS_SINCE_CAP)),
        league_id=int(raw.get("league_id", 45)),
        test_season=int(raw.get("test_season", 12)),
        random_state=int(raw.get("random_state", 42)),
        opponent_elo_prior=float(raw.get(
            "opponent_elo_prior", HOCKEY_ELO_INITIAL)),
        low_weight_seasons=_low_weight_seasons(raw))


def _load_league(
        league_id: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matches = fetch_hockey_matches(league_id)
    rosters = fetch_hockey_match_rosters(league_id)
    ratings = build_hockey_team_ratings(matches)
    return matches, rosters, ratings


def _candidate_frame(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        ratings: pd.DataFrame,
        config: GoalieStartConfig
) -> tuple[pd.DataFrame, int, int]:
    games = _team_games_with_starters(matches, rosters, ratings, config)
    skipped_matches, skipped_team_games = _skip_counts(matches, games)
    frame = _walk_slates(games, config) if not games.empty else _empty_frame()
    if frame.empty or frame["started"].nunique() < 2:
        raise ValueError("Goalie start training needs starters and backups")
    return frame, skipped_matches, skipped_team_games


def _holdout_probabilities(
        frame: pd.DataFrame,
        config: GoalieStartConfig
) -> tuple[pd.DataFrame, np.ndarray, int]:
    # Numery sezonów nie są chronologią. Trening kończy się przed
    # pierwszym meczem sezonu testowego, więc późniejszy sezon nie
    # wchodzi do oceny.
    test_rows = frame.loc[
        frame["season"].astype(int) == config.test_season]
    if test_rows.empty:
        raise ValueError(
            f"Season {config.test_season} must be a proper holdout")
    cutoff = pd.to_datetime(test_rows["game_date"]).min()
    dates = pd.to_datetime(frame["game_date"])
    train_rows = frame.loc[dates < cutoff]
    if train_rows.empty:
        raise ValueError(
            f"Season {config.test_season} has no earlier games")
    model = GoalieStartModel(config)
    model.fit(
        train_rows,
        train_rows["started"],
        sample_weight=_season_weights(train_rows, config))
    return test_rows, model.predict_proba(test_rows), int(len(train_rows))


def _annotate_holdout(
        metrics: dict[str, object],
        config: GoalieStartConfig,
        n_train: int,
        n_test: int) -> None:
    metrics["test_season"] = config.test_season
    metrics["n_train_rows"] = n_train
    metrics["n_test_rows"] = n_test
    metrics["scored_fit"] = "before_first_test_season_game"
    metrics["artifact_fit"] = "all_candidate_rows"


def _save_run(
        run: GoalieStartRun,
        model: GoalieStartModel,
        metrics: dict[str, object]) -> None:
    artifacts.save_model_artifact(run.artifact_dir, model)
    artifacts.save_metrics(run.artifact_dir, metrics)
    artifacts.save_meta(run.artifact_dir, {
        "model_name": run.model_name,
        "model_version": run.model_version,
        "task_type": GOALIE_START_TASK,
        "features": list(GOALIE_START_FEATURES),
        "pool_games": model.config.pool_games,
        "start_share_games": model.config.start_share_games,
        "recent_start_days": model.config.recent_start_days,
        "days_since_start_cap": model.config.days_since_start_cap,
        "test_season": model.config.test_season,
        "low_weight_seasons": _string_key_weights(
            model.config.low_weight_seasons),
        "holdout": "games before the first test-season match",
        "production_fit": "all candidate rows"})


def _team_games_with_starters(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        ratings: pd.DataFrame | None,
        config: GoalieStartConfig) -> pd.DataFrame:
    _require_columns(matches, _MATCH_COLUMNS)
    _require_columns(rosters, _ROSTER_COLUMNS)
    sides = _team_sides(matches)
    starters = _starters(rosters)
    games = sides.merge(starters, on=["match_id", "team_id"], how="inner")
    return _attach_opponent_elo(games, ratings, config.opponent_elo_prior)


def _team_sides(matches: pd.DataFrame) -> pd.DataFrame:
    home = matches.loc[:, [
        "match_id", "game_date", "season", "home_team", "away_team"]]
    home = home.rename(columns={
        "home_team": "team_id",
        "away_team": "opponent_id"})
    away = matches.loc[:, [
        "match_id", "game_date", "season", "away_team", "home_team"]]
    away = away.rename(columns={
        "away_team": "team_id",
        "home_team": "opponent_id"})
    return pd.concat([home, away], ignore_index=True)


def _starters(rosters: pd.DataFrame) -> pd.DataFrame:
    position = rosters["position"].astype(str).str.strip().str.upper()
    line = pd.to_numeric(rosters["line"], errors="coerce")
    starters = rosters.loc[
        (position == GOALIE_POSITION) & (line == STARTING_LINE)].copy()
    if starters.empty:
        return pd.DataFrame(columns=["match_id", "team_id", "starter_id"])
    if "id" in starters.columns:
        starters = starters.sort_values("id", kind="mergesort")
    starters = starters.drop_duplicates(
        ["match_id", "team_id"], keep="first")
    renamed = starters.loc[:, ["match_id", "team_id", "player_id"]]
    return renamed.rename(columns={"player_id": "starter_id"})


def _attach_opponent_elo(
        games: pd.DataFrame,
        ratings: pd.DataFrame | None,
        prior: float) -> pd.DataFrame:
    if games.empty:
        result = games.copy()
        result["opponent_elo"] = pd.Series(dtype="float64")
        return result
    if ratings is None or ratings.empty:
        result = games.copy()
        result["opponent_elo"] = prior
        return result
    _require_columns(ratings, [
        "match_id", "home_team", "away_team", "home_elo", "away_elo"])
    elo = _opponent_elo_rows(ratings)
    merged = games.merge(elo, on=["match_id", "team_id"], how="left")
    merged["opponent_elo"] = merged["opponent_elo"].fillna(prior)
    return merged


def _opponent_elo_rows(ratings: pd.DataFrame) -> pd.DataFrame:
    home = ratings.loc[:, ["match_id", "home_team", "away_elo"]]
    home = home.rename(columns={
        "home_team": "team_id",
        "away_elo": "opponent_elo"})
    away = ratings.loc[:, ["match_id", "away_team", "home_elo"]]
    away = away.rename(columns={
        "away_team": "team_id",
        "home_elo": "opponent_elo"})
    return pd.concat([home, away], ignore_index=True)


def _walk_slates(
        games: pd.DataFrame,
        config: GoalieStartConfig) -> pd.DataFrame:
    history = GoalieStartHistory(config)
    ordered = games.sort_values(
        ["game_date", "match_id", "team_id"],
        kind="mergesort")
    rows: list[dict[str, object]] = []
    grouped = ordered.groupby("game_date", sort=False)
    for game_date, group in grouped:
        _append_slate(rows, history, group, game_date)
        _observe_slate(history, group, game_date)
    if not rows:
        return _empty_frame()
    return pd.DataFrame(rows)


def _append_slate(
        rows: list[dict[str, object]],
        history: GoalieStartHistory,
        group: pd.DataFrame,
        game_date: object) -> None:
    for game in group.itertuples(index=False):
        starter = int(game.starter_id)
        team_id = int(game.team_id)
        elo = float(game.opponent_elo)
        for player_id in history.candidate_ids(team_id, starter):
            features = history.feature_row(
                team_id, player_id, game_date, elo)
            row: dict[str, object] = {
                "match_id": int(game.match_id),
                "team_id": team_id,
                "player_id": player_id,
                "game_date": game.game_date,
                "season": _require_season(game.season),
                "started": int(player_id == starter)}
            row.update(features)
            rows.append(row)


def _observe_slate(
        history: GoalieStartHistory,
        group: pd.DataFrame,
        game_date: object) -> None:
    for game in group.itertuples(index=False):
        history.observe(int(game.team_id), int(game.starter_id), game_date)


def _selection_accuracy(
        frame: pd.DataFrame,
        probabilities: np.ndarray) -> dict[str, object]:
    scored = frame.loc[:, [
        "match_id", "team_id", "player_id", "started"]].copy()
    scored["match_id"] = scored["match_id"].astype(int)
    scored["team_id"] = scored["team_id"].astype(int)
    scored["player_id"] = scored["player_id"].astype(int)
    scored["probability"] = probabilities
    ordered = scored.sort_values(
        ["match_id", "team_id", "player_id"],
        kind="mergesort").reset_index(drop=True)
    chosen = ordered.groupby(
        ["match_id", "team_id"], sort=False)["probability"].idxmax()
    picked = ordered.loc[chosen]
    correct = picked["started"].to_numpy(dtype=int) == 1
    sizes = ordered.groupby(["match_id", "team_id"], sort=False).size()
    keys = pd.MultiIndex.from_frame(picked.loc[:, ["match_id", "team_id"]])
    contested = sizes.reindex(keys).to_numpy() >= 2
    n_games = int(len(picked))
    n_contested = int(np.sum(contested))
    accuracy = float(np.mean(correct)) if n_games else None
    if n_contested:
        contested_accuracy = float(np.mean(correct[contested]))
    else:
        contested_accuracy = None
    return {
        "starter_selection_accuracy": accuracy,
        "starter_selection_accuracy_contested": contested_accuracy,
        "n_team_games": n_games,
        "n_contested_team_games": n_contested}


def _skip_counts(
        matches: pd.DataFrame,
        games: pd.DataFrame) -> tuple[int, int]:
    if "result" not in matches.columns or matches.empty:
        return 0, 0
    finished = matches.loc[
        matches["result"].astype(str).isin(_FINISHED_RESULTS),
        ["match_id", "home_team", "away_team"]]
    if finished.empty:
        return 0, 0
    covered = set(zip(
        games["match_id"].astype(int),
        games["team_id"].astype(int)))
    missing_matches = 0
    missing_team_games = 0
    for row in finished.itertuples(index=False):
        match_id = int(row.match_id)
        home_missing = (match_id, int(row.home_team)) not in covered
        away_missing = (match_id, int(row.away_team)) not in covered
        missing_team_games += int(home_missing) + int(away_missing)
        missing_matches += int(home_missing or away_missing)
    return missing_matches, missing_team_games


def _normalize_group(weights: np.ndarray, positions: np.ndarray) -> None:
    total = float(weights[positions].sum())
    if total > 0.0:
        weights[positions] = weights[positions] / total
        return
    weights[positions] = 1.0 / len(positions)


def _low_weight_seasons(raw: dict[str, object]) -> dict[int, float]:
    if "low_weight_seasons" not in raw:
        return dict(_DEFAULT_LOW_WEIGHT_SEASONS)
    source = raw["low_weight_seasons"]
    if not isinstance(source, dict):
        raise ValueError("low_weight_seasons must be an object")
    return {
        int(season): float(weight)
        for season, weight in source.items()}


def _require_season_weights(weights: dict[int, float]) -> None:
    for season, weight in weights.items():
        if not np.isfinite(weight) or weight < 0.0:
            raise ValueError(
                f"season weight for {season} must be finite and "
                "non-negative")


def _season_weights(
        frame: pd.DataFrame,
        config: GoalieStartConfig) -> np.ndarray:
    seasons = frame["season"].to_numpy()
    values = [
        config.low_weight_seasons.get(int(season), 1.0)
        for season in seasons]
    return np.array(values, dtype=float)


def _fit_weights(
        sample_weight: np.ndarray | pd.Series | None,
        n_rows: int) -> np.ndarray | None:
    if sample_weight is None:
        return None
    weights = np.asarray(sample_weight, dtype=float)
    if len(weights) != n_rows:
        raise ValueError("sample_weight must match the feature frame")
    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise ValueError(
            "sample_weight must be finite and non-negative")
    return weights


def _string_key_weights(weights: dict[int, float]) -> dict[str, float]:
    return {
        str(season): float(weights[season])
        for season in sorted(weights)}


def _start_share(window: list[tuple[date, int]], player_id: int) -> float:
    if not window:
        return 0.0
    starts = sum(1 for _day, player in window if player == player_id)
    return starts / len(window)


def _rest_day_gap(start_day: date, day: date) -> int:
    # 00:00 i 23:00 tego samego dnia UTC to lokalny back-to-back.
    # Wcześniejszy start jest już w historii, więc liczymy go jak wczoraj.
    delta = (day - start_day).days
    if delta == 0:
        return 1
    return delta


def _rest_features(
        starts: deque[date],
        day: date,
        cap: int) -> tuple[int, int]:
    if not starts:
        return cap, 0
    delta = _rest_day_gap(starts[-1], day)
    days_since = min(cap, max(delta, 0))
    started_yesterday = int(delta == 1)
    return days_since, started_yesterday


def _starts_in_window(starts: deque[date], day: date, window_days: int) -> int:
    count = 0
    for start_day in reversed(starts):
        delta = _rest_day_gap(start_day, day)
        if delta > window_days:
            break
        if delta > 0:
            count += 1
    return count


def _team_played_yesterday(
        team_starts: list[tuple[date, int]],
        day: date) -> int:
    if not team_starts:
        return 0
    return int(_rest_day_gap(team_starts[-1][0], day) == 1)


def _binary_labels(
        labels: pd.Series | np.ndarray,
        n_rows: int) -> np.ndarray:
    target = np.asarray(labels, dtype=int)
    if len(target) != n_rows:
        raise ValueError("labels must match the feature frame")
    if set(np.unique(target).tolist()) != {0, STARTED_LABEL}:
        raise ValueError("Goalie start labels must include both 0 and 1")
    return target


def _feature_matrix(
        features: pd.DataFrame,
        columns: list[str]) -> np.ndarray:
    if features.empty:
        raise ValueError("Goalie start features are empty")
    _require_columns(features, columns)
    values = features.loc[:, columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Goalie start features must be finite")
    return values


def _empty_frame() -> pd.DataFrame:
    columns = list(_IDENTITY_COLUMNS) + list(GOALIE_START_FEATURES)
    return pd.DataFrame(columns=columns)


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing goalie start columns: {missing}")


def _require_season(value: object) -> int:
    if pd.isna(value):
        raise ValueError("goalie start rows need a season")
    return int(value)


def _as_datetime(value: datetime | object) -> datetime:
    moment = pd.Timestamp(value)
    if pd.isna(moment):
        raise ValueError("game_date is missing")
    converted = moment.to_pydatetime()
    if converted.tzinfo is not None:
        return converted.replace(tzinfo=None)
    return converted


def _resolve_artifact_dir(value: object) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()
