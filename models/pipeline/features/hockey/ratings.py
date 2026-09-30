"""As-of NHL team ratings: Elo, goal GAP, shot GAP and PDO.

Elo uses the final margin (regulation, otherwise one overtime or
shootout goal). GAP stays on regulation goals. PDO uses the same
goals and shots with empty-net goals removed. GAP defence keeps the
football sign: it rises when the team concedes more than expected.

Games that share ``game_date`` are snapshotted before any commit.
Any new ``season`` value, even a smaller id, pulls ratings 30%
toward the mean and resets the early-season counter.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

import pandas as pd

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.early_season import early_season_alpha
from models.pipeline.features.hockey.early_season import (
    early_season_multiplier)
from models.pipeline.features.hockey.goalies import GOALIE_APPEARANCE_COLUMNS
from models.pipeline.features.hockey.goalies import GoalieRatingsConfig
from models.pipeline.features.hockey.goalies import build_goalie_ratings
from models.pipeline.features.ratings.elo import EloParams
from models.pipeline.features.ratings.elo import update_elo
from models.pipeline.features.ratings.gap import GapParams
from models.pipeline.features.ratings.gap import GapRating
from models.pipeline.features.ratings.gap import new_gap_rating
from models.pipeline.features.ratings.gap import update_gap


# 82 mecze i przewaga domu ~54%: niższe K i HA niż w piłce.
HOCKEY_ELO_INITIAL = 1500.0
HOCKEY_ELO_K = 8.0
HOCKEY_ELO_HOME_ADVANTAGE = 30.0
HOCKEY_GOAL_GAP_INITIAL = 3.0
HOCKEY_GOAL_GAP_RATE = 0.08
HOCKEY_SOG_GAP_INITIAL = 28.0
HOCKEY_SOG_GAP_RATE = 0.05
HOCKEY_PDO_ALPHA = 0.1
HOCKEY_PDO_PRIOR = 100.0
HOCKEY_SEASON_REGRESSION = 0.3

HOCKEY_TEAM_RATING_COLUMNS = [
    "home_elo",
    "away_elo",
    "home_gap_att",
    "home_gap_def",
    "away_gap_att",
    "away_gap_def",
    "home_sog_gap_att",
    "home_sog_gap_def",
    "away_sog_gap_att",
    "away_sog_gap_def",
    "home_pdo",
    "away_pdo",
    "home_season_games",
    "away_season_games",
    "home_early_multiplier",
    "away_early_multiplier"
]
_REQUIRED_MATCH_COLUMNS = [
    "match_id",
    "season",
    "home_team",
    "away_team",
    "game_date",
    "home_team_goals",
    "away_team_goals",
    "result",
    "home_team_sog",
    "away_team_sog",
    "home_team_saves",
    "away_team_saves",
    "home_team_en",
    "away_team_en",
    "ot_winner",
    "so_winner"
]
_STARTER_COLUMNS = [
    "match_id",
    "team_id",
    "player_id",
    "goalie_save_pct",
    "goalie_gsaa_per_60",
    "shots_against"
]
_FINISHED_RESULTS = {"1", "X", "2"}


def _default_elo() -> EloParams:
    return EloParams(
        initial_rating=HOCKEY_ELO_INITIAL,
        k_factor=HOCKEY_ELO_K,
        home_advantage=HOCKEY_ELO_HOME_ADVANTAGE,
        second_tier_coefficient=1.0)


def _default_goal_gap() -> GapParams:
    return GapParams(
        initial_attack=HOCKEY_GOAL_GAP_INITIAL,
        initial_defence=HOCKEY_GOAL_GAP_INITIAL,
        learning_rate=HOCKEY_GOAL_GAP_RATE)


def _default_sog_gap() -> GapParams:
    return GapParams(
        initial_attack=HOCKEY_SOG_GAP_INITIAL,
        initial_defence=HOCKEY_SOG_GAP_INITIAL,
        learning_rate=HOCKEY_SOG_GAP_RATE)


@dataclass(frozen=True)
class HockeyRatingsConfig:
    """Tunable Elo, GAP, PDO and early-season parameters."""

    elo: EloParams = field(default_factory=_default_elo)
    goal_gap: GapParams = field(default_factory=_default_goal_gap)
    sog_gap: GapParams = field(default_factory=_default_sog_gap)
    pdo_alpha: float = HOCKEY_PDO_ALPHA
    season_regression: float = HOCKEY_SEASON_REGRESSION
    early_season: EarlySeasonConfig = field(
        default_factory=EarlySeasonConfig)


class HockeyTeamRatingState:
    """Mutable team ratings with snapshot-before-commit semantics."""

    def __init__(
            self,
            config: HockeyRatingsConfig | None = None) -> None:
        self._config = config or HockeyRatingsConfig()
        weight = self._config.season_regression
        if weight < 0 or weight > 1:
            raise ValueError(
                "season_regression must be between 0 and 1")
        self._elo: dict[int, float] = {}
        self._goal_gap: dict[int, GapRating] = {}
        self._sog_gap: dict[int, GapRating] = {}
        self._pdo: dict[int, float] = {}
        self._season_games: dict[int, int] = {}
        self._season: int | None = None
        self._last_date: datetime | None = None

    def snapshot(
            self,
            home_id: int,
            away_id: int,
            season: int,
            game_date: datetime) -> dict[str, float]:
        """Return both teams' ratings before this match is learned."""
        self._require_forward_date(game_date)
        self._roll_season(int(season))
        self._ensure(home_id)
        self._ensure(away_id)
        home_games = self._season_games.get(home_id, 0)
        away_games = self._season_games.get(away_id, 0)
        home_goals = self._goal_gap[home_id]
        away_goals = self._goal_gap[away_id]
        home_shots = self._sog_gap[home_id]
        away_shots = self._sog_gap[away_id]
        return {
            "home_elo": self._elo[home_id],
            "away_elo": self._elo[away_id],
            "home_gap_att": home_goals.attack,
            "home_gap_def": home_goals.defence,
            "away_gap_att": away_goals.attack,
            "away_gap_def": away_goals.defence,
            "home_sog_gap_att": home_shots.attack,
            "home_sog_gap_def": home_shots.defence,
            "away_sog_gap_att": away_shots.attack,
            "away_sog_gap_def": away_shots.defence,
            "home_pdo": self._pdo[home_id],
            "away_pdo": self._pdo[away_id],
            "home_season_games": float(home_games),
            "away_season_games": float(away_games),
            "home_early_multiplier": _multiplier(
                home_games, self._config),
            "away_early_multiplier": _multiplier(
                away_games, self._config)
        }

    def commit(
            self,
            home_id: int,
            away_id: int,
            home_goals: int,
            away_goals: int,
            home_sog: int | None = None,
            away_sog: int | None = None,
            home_saves: int | None = None,
            away_saves: int | None = None,
            home_empty_net: int = 0,
            away_empty_net: int = 0,
            ot_winner: int | None = None,
            so_winner: int | None = None) -> None:
        """Update both teams from a finished match."""
        self._ensure(home_id)
        self._ensure(away_id)
        home_games = self._season_games.get(home_id, 0)
        away_games = self._season_games.get(away_id, 0)
        self._commit_elo(
            home_id, away_id, home_goals, away_goals,
            ot_winner, so_winner, home_games, away_games)
        self._commit_goal_gap(
            home_id, away_id, home_goals, away_goals,
            home_games, away_games)
        self._commit_sog_gap(
            home_id, away_id, home_sog, away_sog,
            home_games, away_games)
        self._commit_pdo(
            home_id, away_id, home_goals, away_goals,
            home_sog, away_sog, home_saves, away_saves,
            home_empty_net, away_empty_net,
            home_games, away_games)
        self._season_games[home_id] = home_games + 1
        self._season_games[away_id] = away_games + 1

    def _ensure(self, team_id: int) -> None:
        if team_id in self._elo:
            return
        self._elo[team_id] = self._config.elo.initial_rating
        self._goal_gap[team_id] = new_gap_rating(self._config.goal_gap)
        self._sog_gap[team_id] = new_gap_rating(self._config.sog_gap)
        self._pdo[team_id] = HOCKEY_PDO_PRIOR

    def _require_forward_date(self, game_date: datetime) -> None:
        moment = _as_naive_datetime(game_date)
        if self._last_date is not None and moment < self._last_date:
            raise ValueError(
                "Hockey ratings require chronological game dates. "
                f"Got {moment} after {self._last_date}.")
        self._last_date = moment

    def _roll_season(self, season: int) -> None:
        if self._season is None:
            self._season = season
            return
        if season == self._season:
            return
        # Numer sezonu w bazie nie rośnie z datą (8, 7, …, 1, 11).
        self._regress_to_mean()
        self._season_games.clear()
        self._season = season

    def _regress_to_mean(self) -> None:
        weight = self._config.season_regression
        if weight == 0:
            return
        _regress_values(self._elo, weight)
        _regress_values(self._pdo, weight)
        _regress_gaps(self._goal_gap, weight)
        _regress_gaps(self._sog_gap, weight)

    def _commit_elo(
            self,
            home_id: int,
            away_id: int,
            home_goals: int,
            away_goals: int,
            ot_winner: int | None,
            so_winner: int | None,
            home_games: int,
            away_games: int) -> None:
        final_home, final_away = _final_elo_goals(
            home_goals, away_goals, ot_winner, so_winner)
        updated_home, updated_away = _update_elo_sides(
            self._elo[home_id],
            self._elo[away_id],
            final_home,
            final_away,
            _scaled_k(self._config, home_games),
            _scaled_k(self._config, away_games),
            self._config)
        self._elo[home_id] = updated_home
        self._elo[away_id] = updated_away

    def _commit_goal_gap(
            self,
            home_id: int,
            away_id: int,
            home_goals: int,
            away_goals: int,
            home_games: int,
            away_games: int) -> None:
        updated_home, updated_away = _update_gap_sides(
            self._goal_gap[home_id],
            self._goal_gap[away_id],
            home_goals,
            away_goals,
            _scaled_rate(
                self._config.goal_gap.learning_rate,
                home_games,
                self._config),
            _scaled_rate(
                self._config.goal_gap.learning_rate,
                away_games,
                self._config),
            self._config.goal_gap)
        self._goal_gap[home_id] = updated_home
        self._goal_gap[away_id] = updated_away

    def _commit_sog_gap(
            self,
            home_id: int,
            away_id: int,
            home_sog: int | None,
            away_sog: int | None,
            home_games: int,
            away_games: int) -> None:
        if home_sog is None or away_sog is None:
            return
        updated_home, updated_away = _update_gap_sides(
            self._sog_gap[home_id],
            self._sog_gap[away_id],
            home_sog,
            away_sog,
            _scaled_rate(
                self._config.sog_gap.learning_rate,
                home_games,
                self._config),
            _scaled_rate(
                self._config.sog_gap.learning_rate,
                away_games,
                self._config),
            self._config.sog_gap)
        self._sog_gap[home_id] = updated_home
        self._sog_gap[away_id] = updated_away

    def _commit_pdo(
            self,
            home_id: int,
            away_id: int,
            home_goals: int,
            away_goals: int,
            home_sog: int | None,
            away_sog: int | None,
            home_saves: int | None,
            away_saves: int | None,
            home_empty_net: int,
            away_empty_net: int,
            home_games: int,
            away_games: int) -> None:
        # Pusta bramka jest golem i strzałem celnym,
        # ale nie strzałem oddanym na bramkarza.
        home_points = _pdo_points(
            _net_of_empty(home_goals, home_empty_net),
            _net_of_empty(home_sog, home_empty_net),
            home_saves,
            _net_of_empty(away_sog, away_empty_net))
        away_points = _pdo_points(
            _net_of_empty(away_goals, away_empty_net),
            _net_of_empty(away_sog, away_empty_net),
            away_saves,
            _net_of_empty(home_sog, home_empty_net))
        if home_points is not None:
            self._pdo[home_id] = _blend_pdo(
                self._pdo[home_id],
                home_points,
                home_games,
                self._config)
        if away_points is not None:
            self._pdo[away_id] = _blend_pdo(
                self._pdo[away_id],
                away_points,
                away_games,
                self._config)


def build_hockey_team_ratings(
        matches: pd.DataFrame,
        config: HockeyRatingsConfig | None = None) -> pd.DataFrame:
    """Attach pre-match ratings to each finished match.

    Unplayed rows (``result`` outside 1/X/2, or missing goals) are
    dropped. The returned frame keeps the match columns and adds
    ``HOCKEY_TEAM_RATING_COLUMNS``.
    """
    settings = config or HockeyRatingsConfig()
    prepared = _finished_matches(matches)
    if prepared.empty:
        return _with_rating_columns(prepared)
    state = HockeyTeamRatingState(settings)
    snapshots: dict[int, dict[str, float]] = {}
    for game_date, group in prepared.groupby("game_date", sort=False):
        del game_date
        _snapshot_group(state, group, snapshots)
        for _, row in group.iterrows():
            _commit_row(state, row)
    rating_frame = pd.DataFrame.from_dict(snapshots, orient="index")
    rating_frame = rating_frame.reindex(
        columns=HOCKEY_TEAM_RATING_COLUMNS)
    return pd.concat([prepared, rating_frame], axis=1)


def build_hockey_pre_match_ratings(
        matches: pd.DataFrame,
        goalie_appearances: pd.DataFrame | None = None,
        match_rosters: pd.DataFrame | None = None,
        config: HockeyRatingsConfig | None = None,
        goalie_config: GoalieRatingsConfig | None = None) -> pd.DataFrame:
    """Attach team ratings and both starting goalies to each match.

    A starter is ``position == 'G'`` and ``line == 1`` in
    ``match_rosters``. Shots against break a tie when several such
    rows exist. Missing starters stay null.
    """
    teams = build_hockey_team_ratings(matches, config)
    appearances = goalie_appearances
    if appearances is None:
        appearances = pd.DataFrame(columns=GOALIE_APPEARANCE_COLUMNS)
    goalies = build_goalie_ratings(appearances, goalie_config)
    return _attach_goalies(teams, goalies, match_rosters)


def _finished_matches(matches: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column for column in _REQUIRED_MATCH_COLUMNS
        if column not in matches.columns]
    if missing:
        raise KeyError(f"Missing hockey rating columns: {missing}")
    frame = matches.copy()
    finished = frame["result"].astype(str).isin(_FINISHED_RESULTS)
    finished &= frame["home_team_goals"].notna()
    finished &= frame["away_team_goals"].notna()
    ready = frame.loc[finished].copy()
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    return ready.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)


def _with_rating_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in HOCKEY_TEAM_RATING_COLUMNS:
        result[column] = pd.Series(dtype="float64")
    return result


def _snapshot_group(
        state: HockeyTeamRatingState,
        group: pd.DataFrame,
        snapshots: dict[int, dict[str, float]]) -> None:
    for index, row in group.iterrows():
        snapshots[index] = state.snapshot(
            int(row["home_team"]),
            int(row["away_team"]),
            int(row["season"]),
            row["game_date"])


def _commit_row(state: HockeyTeamRatingState, row: pd.Series) -> None:
    state.commit(
        home_id=int(row["home_team"]),
        away_id=int(row["away_team"]),
        home_goals=int(row["home_team_goals"]),
        away_goals=int(row["away_team_goals"]),
        home_sog=_optional_int(row["home_team_sog"]),
        away_sog=_optional_int(row["away_team_sog"]),
        home_saves=_optional_int(row["home_team_saves"]),
        away_saves=_optional_int(row["away_team_saves"]),
        home_empty_net=_empty_net_count(row["home_team_en"]),
        away_empty_net=_empty_net_count(row["away_team_en"]),
        ot_winner=_optional_int(row["ot_winner"]),
        so_winner=_optional_int(row["so_winner"]))


def _attach_goalies(
        teams: pd.DataFrame,
        goalies: pd.DataFrame,
        match_rosters: pd.DataFrame | None) -> pd.DataFrame:
    starters = _starting_goalies(goalies, match_rosters)
    merged = teams.merge(
        _goalie_side(starters, "home"),
        on=["match_id", "home_team"],
        how="left")
    return merged.merge(
        _goalie_side(starters, "away"),
        on=["match_id", "away_team"],
        how="left")


def _starting_goalies(
        goalies: pd.DataFrame,
        match_rosters: pd.DataFrame | None) -> pd.DataFrame:
    """Keep the line-1 goalie, using shots only to break ties."""
    if goalies.empty or match_rosters is None or match_rosters.empty:
        return _empty_starters()
    missing = [
        column for column in (
            "match_id", "player_id", "team_id", "position", "line")
        if column not in match_rosters.columns]
    if missing:
        raise KeyError(f"Missing hockey roster columns: {missing}")
    line = pd.to_numeric(match_rosters["line"], errors="coerce")
    position = match_rosters["position"].astype(str).str.strip()
    starters = match_rosters.loc[(position == "G") & line.eq(1)]
    merged = goalies.merge(
        starters.loc[:, ["match_id", "player_id", "team_id"]],
        on=["match_id", "player_id", "team_id"],
        how="inner")
    if merged.empty:
        return _empty_starters()
    ordered = merged.sort_values(
        ["match_id", "team_id", "shots_against", "player_id"],
        ascending=[True, True, False, True],
        na_position="last")
    return ordered.drop_duplicates(
        ["match_id", "team_id"], keep="first")


def _empty_starters() -> pd.DataFrame:
    return pd.DataFrame(columns=_STARTER_COLUMNS)


def _goalie_side(goalies: pd.DataFrame, side: str) -> pd.DataFrame:
    team_column = f"{side}_team"
    columns = [
        "match_id",
        "team_id",
        "player_id",
        "goalie_save_pct",
        "goalie_gsaa_per_60"
    ]
    frame = goalies.loc[:, columns].copy()
    return frame.rename(columns={
        "team_id": team_column,
        "player_id": f"{side}_goalie_id",
        "goalie_save_pct": f"{side}_goalie_save_pct",
        "goalie_gsaa_per_60": f"{side}_goalie_gsaa_per_60"
    })


def _update_elo_sides(
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
        home_k: float,
        away_k: float,
        config: HockeyRatingsConfig) -> tuple[float, float]:
    """Reuse ``update_elo`` with a separate K on each side.

    The shared helper applies one K to both teams. Early-season
    multipliers differ, so each side is taken from its own call.
    """
    home_params = _elo_params(config, home_k)
    away_params = _elo_params(config, away_k)
    updated_home, _away_ignored = update_elo(
        home_rating, away_rating, home_goals, away_goals, home_params)
    _home_ignored, updated_away = update_elo(
        home_rating, away_rating, home_goals, away_goals, away_params)
    return updated_home, updated_away


def _update_gap_sides(
        home: GapRating,
        away: GapRating,
        home_goals: int,
        away_goals: int,
        home_rate: float,
        away_rate: float,
        base: GapParams) -> tuple[GapRating, GapRating]:
    """Reuse ``update_gap`` with a separate learning rate per team."""
    home_params = _gap_params(base, home_rate)
    away_params = _gap_params(base, away_rate)
    updated_home, _away_ignored = update_gap(
        home, away, home_goals, away_goals, home_params)
    _home_ignored, updated_away = update_gap(
        home, away, home_goals, away_goals, away_params)
    return updated_home, updated_away


def _elo_params(config: HockeyRatingsConfig, k_factor: float) -> EloParams:
    base = config.elo
    return EloParams(
        initial_rating=base.initial_rating,
        k_factor=k_factor,
        home_advantage=base.home_advantage,
        second_tier_coefficient=base.second_tier_coefficient)


def _gap_params(base: GapParams, learning_rate: float) -> GapParams:
    return GapParams(
        initial_attack=base.initial_attack,
        initial_defence=base.initial_defence,
        learning_rate=learning_rate)


def _final_elo_goals(
        home_goals: int,
        away_goals: int,
        ot_winner: int | None,
        so_winner: int | None) -> tuple[int, int]:
    """Regulation margin, plus one goal when overtime decides a tie.

    A tie without a winner stays a draw so one missing ``OTwinner``
    does not abort the whole rating pass.
    """
    if home_goals != away_goals:
        return home_goals, away_goals
    side = _extra_time_side(ot_winner, so_winner)
    if side == "home":
        return home_goals + 1, away_goals
    if side == "away":
        return home_goals, away_goals + 1
    return home_goals, away_goals


def _extra_time_side(
        ot_winner: int | None,
        so_winner: int | None) -> str | None:
    if ot_winner == 1:
        return "home"
    if ot_winner == 2:
        return "away"
    if ot_winner != 3:
        return None
    if so_winner == 1:
        return "home"
    if so_winner == 2:
        return "away"
    return None


def _pdo_points(
        goals: int,
        shots: int | None,
        saves: int | None,
        opponent_shots: int | None) -> float | None:
    if shots is None or saves is None or opponent_shots is None:
        return None
    if shots <= 0 or opponent_shots <= 0:
        return None
    shooting = goals / shots
    saving = saves / opponent_shots
    return (shooting + saving) * 100.0


def _blend_pdo(
        previous: float,
        observed: float,
        games_played: int,
        config: HockeyRatingsConfig) -> float:
    alpha = early_season_alpha(
        config.pdo_alpha, games_played, config.early_season)
    return alpha * observed + (1.0 - alpha) * previous


def _scaled_k(config: HockeyRatingsConfig, games_played: int) -> float:
    return config.elo.k_factor * _multiplier(games_played, config)


def _scaled_rate(
        learning_rate: float,
        games_played: int,
        config: HockeyRatingsConfig) -> float:
    return learning_rate * _multiplier(games_played, config)


def _multiplier(games_played: int, config: HockeyRatingsConfig) -> float:
    return early_season_multiplier(games_played, config.early_season)


def _regress_values(values: dict[int, float], weight: float) -> None:
    if not values:
        return
    keep = 1.0 - weight
    mean = sum(values.values()) / len(values)
    for team_id in list(values):
        values[team_id] = keep * values[team_id] + weight * mean


def _regress_gaps(ratings: dict[int, GapRating], weight: float) -> None:
    if not ratings:
        return
    keep = 1.0 - weight
    mean_attack = sum(item.attack for item in ratings.values()) / len(
        ratings)
    mean_defence = sum(
        item.defence for item in ratings.values()) / len(ratings)
    for team_id, rating in list(ratings.items()):
        ratings[team_id] = GapRating(
            attack=keep * rating.attack + weight * mean_attack,
            defence=keep * rating.defence + weight * mean_defence)


def _net_of_empty(total: int | None, empty_net: int) -> int | None:
    """Drop empty-net goals from a goal or shot total."""
    if total is None:
        return None
    adjusted = total - empty_net
    if adjusted < 0:
        return 0
    return adjusted


def _empty_net_count(value: object) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed < 0:
        return 0
    return parsed


def _as_naive_datetime(value: datetime) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _optional_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)
