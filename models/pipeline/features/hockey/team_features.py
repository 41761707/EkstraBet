"""Pre-match NHL features for the gradient-boosted goals model.

Every column is known before the match. A slate that shares
``game_date`` is snapshotted before any of those games is learned.
Training treats the historical box score as the lineup. Prediction
can replace that lineup with ``projected``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from models.pipeline.core.config import FeatureConfig
from models.pipeline.core.registry import register_feature_builder
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_matches)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.data.hockey_history_repository import fetch_team_arenas
from models.pipeline.features.hockey.goalies import GOALIE_APPEARANCE_COLUMNS
from models.pipeline.features.hockey.goalies import GoalieRatingState
from models.pipeline.features.hockey.goalies import build_goalie_ratings
from models.pipeline.features.hockey.lineup_strength import (
    CONFIRMED_LINEUP_SOURCE)
from models.pipeline.features.hockey.lineup_strength import LINEUP_RATIO_COLUMNS
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.lineup_strength import (
    build_lineup_ratios)
from models.pipeline.features.hockey.lineup_strength import (
    prepare_lineup_memory)
from models.pipeline.features.hockey.lineup_strength import (
    projected_lineup_strength)
from models.pipeline.features.hockey.lineup_strength import (
    typical_lineup_strength)
from models.pipeline.features.hockey.ratings import HOCKEY_TEAM_RATING_COLUMNS
from models.pipeline.features.hockey.ratings import HockeyRatingsConfig
from models.pipeline.features.hockey.ratings import HockeyTeamRatingState
from models.pipeline.features.hockey.schedule import SCHEDULE_FEATURE_COLUMNS
from models.pipeline.features.hockey.schedule import build_schedule_features
from models.pipeline.labels.hockey_goals import HockeyGoalsLabeler


logger = logging.getLogger(__name__)

PLAYOFF_ROUND = 900
H2H_WINDOW_DAYS = 365
H2H_PRIOR_GAMES = 5
LEAGUE_GOALS_ALPHA = 0.02
LEAGUE_GOALS_PRIOR = 5.5
SEASON_INDEX_CAP = 8
GOALIE_HALF_LIFE_DAYS = 180.0
_FINISHED_RESULTS = frozenset({"1", "X", "2"})
_LINEUP_VALUES = [
    column for column in LINEUP_RATIO_COLUMNS
    if column not in ("match_id", "team_id")]
_NEUTRAL_LINEUP = {
    "lineup_off": np.nan,
    "lineup_shots": np.nan,
    "lineup_def": np.nan,
    "lineup_off_ratio": 1.0,
    "lineup_def_ratio": 1.0,
    "top6_f_off": np.nan,
    "bottom6_f_off": np.nan,
    "top4_d_def": np.nan,
    "missing_top6_f": 0.0,
    "missing_top4_d": 0.0}
_RATING_PAIRS = [
    ("elo", "home_elo", "away_elo"),
    ("gap_att", "home_gap_att", "away_gap_att"),
    ("gap_def", "home_gap_def", "away_gap_def"),
    ("sog_gap_att", "home_sog_gap_att", "away_sog_gap_att"),
    ("sog_gap_def", "home_sog_gap_def", "away_sog_gap_def"),
    ("pdo", "home_pdo", "away_pdo"),
    ("season_games", "home_season_games", "away_season_games"),
    (
        "early_multiplier",
        "home_early_multiplier",
        "away_early_multiplier")]
_SIDE_STEMS = [
    "goalie_save_pct",
    "goalie_gsaa_per_60",
    "team_save_pct",
    "season_game_index",
    "early_form_goals_per_60",
    "early_form_shot_share",
    "early_form_off",
    *_LINEUP_VALUES]
_SHARED_COLUMNS = [
    "is_playoff",
    "league_goals_avg",
    "h2h_goal_diff"]
_IDENTITY = [
    "match_id",
    "season",
    "game_date",
    "home_team",
    "away_team"]
_TARGET_COLUMNS = ["goals_home", "goals_away", "ot_home_win"]
ProjectedLineups = dict[
    int, tuple[ProbableLineup | None, ProbableLineup | None]]


def hockey_gbm_feature_columns() -> list[str]:
    """Return the ordered numeric columns the GBM consumes."""
    columns: list[str] = []
    for stem, home, away in _RATING_PAIRS:
        columns.extend([home, away, f"{stem}_diff"])
    for stem in _SIDE_STEMS:
        columns.extend([f"home_{stem}", f"away_{stem}", f"{stem}_diff"])
    columns.extend(SCHEDULE_FEATURE_COLUMNS)
    columns.extend(_SHARED_COLUMNS)
    return columns


HOCKEY_GBM_FEATURE_COLUMNS = hockey_gbm_feature_columns()


@dataclass
class _ClubForm:
    """Goals, shots and lineup offence carried inside one season."""

    season: int | None = None
    games: int = 0
    goals: float = 0.0
    sog_for: float = 0.0
    sog_against: float = 0.0
    prev_goals_per_60: float = 0.0
    prev_shot_share: float = 0.5
    prev_off: float | None = None
    off_sum: float = 0.0
    off_games: int = 0
    pending_off: float | None = None


def build_hockey_team_features(
        matches: pd.DataFrame,
        arenas: pd.DataFrame,
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int = 10,
        projected: ProjectedLineups | None = None,
        ratings_config: HockeyRatingsConfig | None = None,
        goalie_half_life_days: float = GOALIE_HALF_LIFE_DAYS
) -> pd.DataFrame:
    """Return one pre-match feature row for every input match.

    ``projected`` replaces the historical lineup for those match ids.
    A missing side stays at a typical lineup (ratios of 1).
    """
    prepared = _prepare_matches(matches)
    if prepared.empty:
        return _empty_feature_frame()
    ratings = _prematch_ratings(prepared, ratings_config)
    schedule = build_schedule_features(prepared, arenas)
    lineups = _lineup_frame(
        prepared, rosters, player_stats, baseline_games, projected)
    goalies = _goalie_frame(
        prepared,
        player_stats,
        rosters,
        projected,
        goalie_half_life_days)
    shared = _shared_context(prepared)
    early = _early_form(prepared, lineups)
    labeled = _targets(prepared)
    return _join_features(
        prepared, ratings, schedule, lineups, goalies, shared, early,
        labeled)


def load_hockey_team_feature_frame(
        league_id: int,
        baseline_games: int = 10,
        projected: ProjectedLineups | None = None,
        ratings_config: HockeyRatingsConfig | None = None,
        goalie_half_life_days: float = GOALIE_HALF_LIFE_DAYS
) -> pd.DataFrame:
    """Load league history and build the GBM feature table."""
    logger.info("Loading hockey team features for league %s", league_id)
    return build_hockey_team_features(
        fetch_hockey_matches(league_id),
        fetch_team_arenas(),
        fetch_hockey_match_rosters(league_id),
        fetch_hockey_player_stats(league_id),
        baseline_games=baseline_games,
        projected=projected,
        ratings_config=ratings_config,
        goalie_half_life_days=goalie_half_life_days)


@register_feature_builder("HockeyTeamFeatureBuilder")
class HockeyTeamFeatureBuilder:
    """Registry wrapper around ``build_hockey_team_features``."""

    def __init__(self) -> None:
        self.arenas = pd.DataFrame()
        self.rosters = pd.DataFrame()
        self.player_stats = pd.DataFrame()
        self.projected: ProjectedLineups | None = None
        self.baseline_games = 10
        self.ratings_config: HockeyRatingsConfig | None = None
        self.goalie_half_life_days = GOALIE_HALF_LIFE_DAYS

    def build_features(
            self,
            frame: pd.DataFrame,
            config: FeatureConfig) -> pd.DataFrame:
        """Build features for ``frame``. Auxiliaries are set on self."""
        del config
        return build_hockey_team_features(
            frame,
            self.arenas,
            self.rosters,
            self.player_stats,
            baseline_games=self.baseline_games,
            projected=self.projected,
            ratings_config=self.ratings_config,
            goalie_half_life_days=self.goalie_half_life_days)


def _prepare_matches(matches: pd.DataFrame) -> pd.DataFrame:
    required = ["match_id", "season", "home_team", "away_team", "game_date"]
    missing = [column for column in required if column not in matches.columns]
    if missing:
        raise KeyError(f"Missing hockey match columns: {missing}")
    frame = matches.copy()
    for column in (
            "result",
            "round",
            "home_team_goals",
            "away_team_goals",
            "home_team_sog",
            "away_team_sog",
            "home_team_saves",
            "away_team_saves",
            "home_team_en",
            "away_team_en",
            "ot_winner",
            "so_winner"):
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    if frame["game_date"].dt.tz is not None:
        frame["game_date"] = frame["game_date"].dt.tz_localize(None)
    frame = frame.loc[frame["game_date"].notna()].copy()
    frame["match_id"] = frame["match_id"].astype(int)
    frame["season"] = frame["season"].astype(int)
    frame["home_team"] = frame["home_team"].astype(int)
    frame["away_team"] = frame["away_team"].astype(int)
    frame = frame.loc[frame["home_team"] != frame["away_team"]]
    frame = frame.drop_duplicates("match_id", keep="first")
    return frame.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)


def _empty_feature_frame() -> pd.DataFrame:
    columns = (
        _IDENTITY + _TARGET_COLUMNS + HOCKEY_GBM_FEATURE_COLUMNS)
    return pd.DataFrame(columns=columns)


def _prematch_ratings(
        matches: pd.DataFrame,
        config: HockeyRatingsConfig | None) -> pd.DataFrame:
    state = HockeyTeamRatingState(config)
    rows: list[dict[str, float | int]] = []
    for _game_date, group in matches.groupby("game_date", sort=False):
        snapped: list[tuple[object, dict[str, float]]] = []
        for row in group.itertuples(index=False):
            snapped.append((row, state.snapshot(
                int(row.home_team),
                int(row.away_team),
                int(row.season),
                row.game_date.to_pydatetime())))
        for row, rating in snapped:
            rating["match_id"] = int(row.match_id)
            rows.append(rating)
            if _played(row):
                _commit_rating(state, row)
    frame = pd.DataFrame(rows)
    return frame.reindex(
        columns=["match_id", *HOCKEY_TEAM_RATING_COLUMNS])


def _commit_rating(state: HockeyTeamRatingState, row: object) -> None:
    state.commit(
        home_id=int(row.home_team),
        away_id=int(row.away_team),
        home_goals=int(row.home_team_goals),
        away_goals=int(row.away_team_goals),
        home_sog=_optional_int(row.home_team_sog),
        away_sog=_optional_int(row.away_team_sog),
        home_saves=_optional_int(row.home_team_saves),
        away_saves=_optional_int(row.away_team_saves),
        home_empty_net=_empty_net(row.home_team_en),
        away_empty_net=_empty_net(row.away_team_en),
        ot_winner=_optional_int(row.ot_winner),
        so_winner=_optional_int(row.so_winner))


def _lineup_frame(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int,
        projected: ProjectedLineups | None) -> pd.DataFrame:
    if rosters.empty:
        historical = pd.DataFrame(columns=LINEUP_RATIO_COLUMNS)
    else:
        historical = build_lineup_ratios(
            rosters, player_stats, baseline_games)
    sides = _pivot_lineups(matches, historical)
    memory = prepare_lineup_memory(
        rosters, player_stats, baseline_games)
    filled = _fill_typical_absences(sides, matches, memory)
    if not projected:
        return filled
    return _apply_projected_lineups(filled, matches, projected, memory)


def _pivot_lineups(
        matches: pd.DataFrame,
        ratios: pd.DataFrame) -> pd.DataFrame:
    home = _rename_lineup_side(ratios, "home")
    away = _rename_lineup_side(ratios, "away")
    merged = matches.loc[:, ["match_id", "home_team", "away_team"]].merge(
        home, on=["match_id", "home_team"], how="left")
    merged = merged.merge(away, on=["match_id", "away_team"], how="left")
    return _fill_neutral_lineup(merged)


def _rename_lineup_side(ratios: pd.DataFrame, side: str) -> pd.DataFrame:
    team_column = "home_team" if side == "home" else "away_team"
    columns = ["match_id", team_column, *[
        f"{side}_{name}" for name in _LINEUP_VALUES]]
    if ratios.empty:
        return pd.DataFrame(columns=columns)
    renamed = ratios.loc[:, ["match_id", "team_id", *_LINEUP_VALUES]].rename(
        columns={
            "team_id": team_column,
            **{
                name: f"{side}_{name}" for name in _LINEUP_VALUES}})
    return renamed.drop_duplicates(["match_id", team_column])


def _fill_neutral_lineup(frame: pd.DataFrame) -> pd.DataFrame:
    filled = frame.copy()
    for side in ("home", "away"):
        for name, value in _NEUTRAL_LINEUP.items():
            column = f"{side}_{name}"
            if column not in filled.columns:
                filled[column] = value
            elif name in (
                    "lineup_off_ratio",
                    "lineup_def_ratio",
                    "missing_top6_f",
                    "missing_top4_d"):
                numeric = pd.to_numeric(filled[column], errors="coerce")
                filled[column] = numeric.fillna(value)
    return filled


def _apply_projected_lineups(
        sides: pd.DataFrame,
        matches: pd.DataFrame,
        projected: ProjectedLineups,
        memory: object) -> pd.DataFrame:
    updated = sides.set_index("match_id", drop=False)
    moments = matches.set_index("match_id")
    for match_id, (home, away) in projected.items():
        if match_id not in moments.index:
            continue
        row = moments.loc[match_id]
        moment = _as_datetime(row["game_date"])
        season = int(row["season"])
        for side, lineup in (("home", home), ("away", away)):
            team_id = int(row["home_team" if side == "home" else "away_team"])
            strength = _projected_or_neutral(
                memory, lineup, moment, season, match_id, team_id)
            for name, value in strength.items():
                if name in _LINEUP_VALUES:
                    updated.loc[match_id, f"{side}_{name}"] = value
    return updated.reset_index(drop=True)


def _projected_or_neutral(
        memory: object,
        lineup: ProbableLineup | None,
        moment: datetime,
        season: int,
        match_id: int,
        team_id: int) -> dict[str, float]:
    if lineup is None:
        return _typical_strength(memory, team_id, moment, season)
    try:
        return projected_lineup_strength(memory, lineup, moment, season)
    except ValueError as exc:
        logger.warning(
            "Projected lineup for match %s could not be scored: %s",
            match_id,
            exc)
        return _typical_strength(memory, team_id, moment, season)


def _fill_typical_absences(
        sides: pd.DataFrame,
        matches: pd.DataFrame,
        memory: object) -> pd.DataFrame:
    """Replace a missing box score with the club's usual slots."""
    updated = sides.set_index("match_id", drop=False)
    moments = matches.set_index("match_id")
    for match_id, row in moments.iterrows():
        if match_id not in updated.index:
            continue
        moment = _as_datetime(row["game_date"])
        season = int(row["season"])
        sides_teams = (("home", "home_team"), ("away", "away_team"))
        for side, team_column in sides_teams:
            column = f"{side}_lineup_off"
            if pd.notna(updated.at[match_id, column]):
                continue
            strength = _typical_strength(
                memory, int(row[team_column]), moment, season)
            for name, value in strength.items():
                if name in _LINEUP_VALUES:
                    updated.at[match_id, f"{side}_{name}"] = value
    return updated.reset_index(drop=True)


def _typical_strength(
        memory: object,
        team_id: int,
        moment: datetime,
        season: int) -> dict[str, float]:
    return typical_lineup_strength(memory, team_id, moment, season)


def _goalie_frame(
        matches: pd.DataFrame,
        player_stats: pd.DataFrame,
        rosters: pd.DataFrame,
        projected: ProjectedLineups | None,
        half_life_days: float) -> pd.DataFrame:
    appearances = _goalie_appearances(player_stats)
    ratings = build_goalie_ratings(appearances)
    starters = _starter_table(ratings, rosters)
    sides = _pivot_starters(matches, starters)
    averaged = _with_team_save_average(sides, half_life_days)
    if not projected:
        return averaged
    return _apply_projected_goalies(
        averaged, appearances, projected, matches)


def _goalie_appearances(player_stats: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty or "shots_against" not in player_stats.columns:
        return pd.DataFrame(columns=GOALIE_APPEARANCE_COLUMNS)
    shots = pd.to_numeric(player_stats["shots_against"], errors="coerce")
    mask = shots.notna() & (shots > 0)
    columns = [
        column for column in GOALIE_APPEARANCE_COLUMNS
        if column in player_stats.columns]
    return player_stats.loc[mask, columns].copy()


def _starter_table(
        ratings: pd.DataFrame,
        rosters: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "match_id",
        "team_id",
        "goalie_save_pct",
        "goalie_gsaa_per_60"]
    if ratings.empty or rosters.empty:
        return pd.DataFrame(columns=columns)
    line = pd.to_numeric(rosters["line"], errors="coerce")
    position = rosters["position"].astype(str).str.strip()
    starters = rosters.loc[
        (position == "G") & line.eq(1),
        ["match_id", "player_id", "team_id"]]
    merged = ratings.merge(
        starters, on=["match_id", "player_id", "team_id"], how="inner")
    if merged.empty:
        return pd.DataFrame(columns=columns)
    ordered = merged.sort_values(
        ["match_id", "team_id", "shots_against", "player_id"],
        ascending=[True, True, False, True])
    kept = ordered.drop_duplicates(["match_id", "team_id"], keep="first")
    return kept.loc[:, columns]


def _pivot_starters(
        matches: pd.DataFrame,
        starters: pd.DataFrame) -> pd.DataFrame:
    base = matches.loc[:, [
        "match_id", "game_date", "home_team", "away_team"]].copy()
    for side, team_column in (
            ("home", "home_team"), ("away", "away_team")):
        renamed = _rename_starter_side(starters, side, team_column)
        base = base.merge(renamed, on=["match_id", team_column], how="left")
    return base


def _rename_starter_side(
        starters: pd.DataFrame,
        side: str,
        team_column: str) -> pd.DataFrame:
    columns = [
        "match_id",
        team_column,
        f"{side}_goalie_save_pct",
        f"{side}_goalie_gsaa_per_60"]
    if starters.empty:
        return pd.DataFrame(columns=columns)
    renamed = starters.rename(columns={
        "team_id": team_column,
        "goalie_save_pct": f"{side}_goalie_save_pct",
        "goalie_gsaa_per_60": f"{side}_goalie_gsaa_per_60"})
    return renamed.loc[:, columns].drop_duplicates(
        ["match_id", team_column])


def _with_team_save_average(
        frame: pd.DataFrame,
        half_life_days: float) -> pd.DataFrame:
    if half_life_days <= 0.0:
        raise ValueError("goalie_half_life_days must be positive")
    ordered = frame.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)
    state: dict[int, tuple[pd.Timestamp, float, float]] = {}
    home_average: list[float] = []
    away_average: list[float] = []
    # Cała data jest zrzutem, zanim którykolwiek mecz wejdzie do stanu.
    for _game_date, group in ordered.groupby("game_date", sort=False):
        rows = list(group.itertuples(index=False))
        for row in rows:
            home_average.append(_save_snapshot(state, int(row.home_team)))
            away_average.append(_save_snapshot(state, int(row.away_team)))
        for row in rows:
            moment = pd.Timestamp(row.game_date)
            _update_save(
                state, int(row.home_team), moment,
                _finite(row.home_goalie_save_pct), half_life_days)
            _update_save(
                state, int(row.away_team), moment,
                _finite(row.away_goalie_save_pct), half_life_days)
    ordered["home_team_save_pct"] = home_average
    ordered["away_team_save_pct"] = away_average
    return _fill_missing_goalies(ordered)


def _fill_missing_goalies(frame: pd.DataFrame) -> pd.DataFrame:
    # Brak startera: średni save% drużyny, a GSAA jak średnia ligowa.
    filled = frame.copy()
    for side in ("home", "away"):
        save = filled[f"{side}_goalie_save_pct"]
        average = filled[f"{side}_team_save_pct"]
        missing = save.isna() & average.notna()
        filled.loc[missing, f"{side}_goalie_save_pct"] = average[missing]
        gsaa = filled[f"{side}_goalie_gsaa_per_60"]
        filled.loc[missing & gsaa.isna(), f"{side}_goalie_gsaa_per_60"] = 0.0
    return filled


def _save_snapshot(
        state: dict[int, tuple[pd.Timestamp, float, float]],
        team_id: int) -> float:
    previous = state.get(team_id)
    if previous is None:
        return np.nan
    return previous[1]


def _update_save(
        state: dict[int, tuple[pd.Timestamp, float, float]],
        team_id: int,
        moment: pd.Timestamp,
        save: float | None,
        half_life_days: float) -> None:
    if save is None:
        return
    previous = state.get(team_id)
    if previous is None:
        state[team_id] = (moment, save, 1.0)
        return
    last, average, weight = previous
    age_days = max((moment - last).total_seconds() / 86400.0, 0.0)
    decay = math.exp(-math.log(2.0) * age_days / half_life_days)
    decayed = weight * decay
    new_weight = decayed + 1.0
    state[team_id] = (
        moment,
        (average * decayed + save) / new_weight,
        new_weight)


def _apply_projected_goalies(
        frame: pd.DataFrame,
        appearances: pd.DataFrame,
        projected: ProjectedLineups,
        matches: pd.DataFrame) -> pd.DataFrame:
    state = _committed_goalie_state(appearances)
    updated = frame.set_index("match_id", drop=False)
    moments = matches.set_index("match_id")
    ordered = sorted(
        projected,
        key=lambda match_id: _projection_sort_key(moments, match_id))
    for match_id in ordered:
        if match_id not in moments.index:
            continue
        moment = _as_datetime(moments.loc[match_id, "game_date"])
        home, away = projected[match_id]
        for side, lineup in (("home", home), ("away", away)):
            expected = _expected_goalie(state, lineup, moment, match_id)
            if expected is None:
                continue
            save, gsaa = expected
            updated.loc[match_id, f"{side}_goalie_save_pct"] = save
            updated.loc[match_id, f"{side}_goalie_gsaa_per_60"] = gsaa
    return updated.reset_index(drop=True)


def _projection_sort_key(
        moments: pd.DataFrame,
        match_id: int) -> tuple[pd.Timestamp, int]:
    if match_id not in moments.index:
        return pd.Timestamp.max, match_id
    return pd.Timestamp(moments.loc[match_id, "game_date"]), match_id


def _committed_goalie_state(
        appearances: pd.DataFrame) -> GoalieRatingState:
    state = GoalieRatingState()
    if appearances.empty:
        return state
    ordered = appearances.sort_values(
        ["game_date", "match_id", "player_id"])
    for row in ordered.itertuples(index=False):
        shots = _finite(row.shots_against)
        if shots is None or shots <= 0.0:
            continue
        saved = _finite(getattr(row, "shots_saved", None))
        toi = _finite(getattr(row, "toi_seconds", None))
        state.commit(
            int(row.player_id),
            _as_datetime(row.game_date),
            shots,
            0.0 if saved is None else saved,
            0.0 if toi is None else toi)
    return state


def projected_starter_save(
        lineup: ProbableLineup | None,
        state: GoalieRatingState,
        as_of: datetime,
        match_id: int) -> float | None:
    """Return the dressed net's shrunk save%, or None.

    A confirmed starter has weight 1. An unconfirmed net is the
    expectation over ``start_probability``.
    """
    expected = _expected_goalie(state, lineup, as_of, match_id)
    if expected is None:
        return None
    return expected[0]


def committed_goalie_state(player_stats: pd.DataFrame) -> GoalieRatingState:
    """Replay goalie appearances so a later snapshot stays as-of."""
    return _committed_goalie_state(_goalie_appearances(player_stats))


def _expected_goalie(
        state: GoalieRatingState,
        lineup: ProbableLineup | None,
        moment: datetime,
        match_id: int) -> tuple[float, float] | None:
    if lineup is None:
        return None
    weighted = _goalie_start_weights(lineup)
    if not weighted:
        return None
    weighted_save = 0.0
    weighted_gsaa = 0.0
    weight_sum = 0.0
    try:
        for player, weight in weighted:
            rating = state.snapshot(int(player.player_id), moment)
            weighted_save += weight * rating.save_pct
            weighted_gsaa += weight * rating.gsaa_per_60
            weight_sum += weight
    except ValueError as exc:
        logger.warning(
            "Goalie expectation for match %s failed: %s", match_id, exc)
        return None
    if weight_sum <= 0.0:
        return None
    return weighted_save / weight_sum, weighted_gsaa / weight_sum


def _goalie_start_weights(
        lineup: ProbableLineup
) -> list[tuple[ProbableLineupPlayer, float]]:
    # Potwierdzony starter ma wagę 1. P(start) jest w
    # start_probability. confidence to udział w pięciu składach.
    goalies = [
        player for player in lineup.players if _is_goalie(player)]
    confirmed = [
        player for player in goalies if _is_confirmed_starter(player)]
    if confirmed:
        return [(player, 1.0) for player in confirmed]
    probable = _probable_start_weights(goalies)
    if probable:
        return probable
    marked = [
        player for player in goalies if _is_marked_starter(player)]
    if not marked:
        return []
    return [(marked[0], 1.0)]


def _probable_start_weights(
        goalies: list[ProbableLineupPlayer]
) -> list[tuple[ProbableLineupPlayer, float]]:
    weighted: list[tuple[ProbableLineupPlayer, float]] = []
    for player in goalies:
        if _lineup_source(player) == CONFIRMED_LINEUP_SOURCE:
            continue
        probability = _start_probability(player)
        if probability is None:
            continue
        weighted.append((player, probability))
    return weighted


def _is_goalie(player: ProbableLineupPlayer) -> bool:
    position = player.position
    if position is None or _missing(position):
        return False
    return str(position).strip().upper() == "G"


def _is_confirmed_starter(player: ProbableLineupPlayer) -> bool:
    return (
        _lineup_source(player) == CONFIRMED_LINEUP_SOURCE
        and _is_marked_starter(player))


def _is_marked_starter(player: ProbableLineupPlayer) -> bool:
    starter = player.is_starting_goalie
    if starter is None or _missing(starter):
        return False
    try:
        return int(starter) == 1
    except (TypeError, ValueError):
        return False


def _lineup_source(player: ProbableLineupPlayer) -> str:
    source = player.source
    if source is None or _missing(source):
        return ""
    return str(source).strip().upper()


def _start_probability(player: ProbableLineupPlayer) -> float | None:
    probability = player.start_probability
    if probability is None or _missing(probability):
        return None
    try:
        weight = float(probability)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(weight) or weight <= 0.0:
        return None
    return min(weight, 1.0)


def _shared_context(matches: pd.DataFrame) -> pd.DataFrame:
    league = LEAGUE_GOALS_PRIOR
    meetings: dict[tuple[int, int], list[tuple[pd.Timestamp, float]]] = {}
    rows: list[dict[str, float | int]] = []
    for game_date, group in matches.groupby("game_date", sort=False):
        moment = pd.Timestamp(game_date)
        snapped: list[tuple[object, dict[str, float | int]]] = []
        for row in group.itertuples(index=False):
            snapped.append((row, {
                "match_id": int(row.match_id),
                "is_playoff": _is_playoff(row.round),
                "league_goals_avg": league,
                "h2h_goal_diff": _h2h_delta(
                    meetings, int(row.home_team), int(row.away_team),
                    moment)}))
        rows.extend(item for _row, item in snapped)
        for row, _item in snapped:
            if not _played(row):
                continue
            total = float(row.home_team_goals) + float(row.away_team_goals)
            league = (
                LEAGUE_GOALS_ALPHA * total
                + (1.0 - LEAGUE_GOALS_ALPHA) * league)
            _remember_meeting(meetings, row, moment)
    return pd.DataFrame(rows)


def _h2h_delta(
        meetings: dict[tuple[int, int], list[tuple[pd.Timestamp, float]]],
        home_id: int,
        away_id: int,
        moment: pd.Timestamp) -> float:
    key = (min(home_id, away_id), max(home_id, away_id))
    cutoff = moment - pd.Timedelta(days=H2H_WINDOW_DAYS)
    total = 0.0
    count = 0
    for when, low_diff in meetings.get(key, []):
        if when <= cutoff or when >= moment:
            continue
        signed = low_diff if home_id == key[0] else -low_diff
        total += signed
        count += 1
    return total / (count + H2H_PRIOR_GAMES)


def _remember_meeting(
        meetings: dict[tuple[int, int], list[tuple[pd.Timestamp, float]]],
        row: object,
        moment: pd.Timestamp) -> None:
    home_id = int(row.home_team)
    away_id = int(row.away_team)
    key = (min(home_id, away_id), max(home_id, away_id))
    home_diff = float(row.home_team_goals) - float(row.away_team_goals)
    low_diff = home_diff if home_id == key[0] else -home_diff
    bucket = meetings.setdefault(key, [])
    cutoff = moment - pd.Timedelta(days=H2H_WINDOW_DAYS)
    meetings[key] = [
        item for item in bucket if item[0] > cutoff]
    meetings[key].append((moment, low_diff))


def _early_form(
        matches: pd.DataFrame,
        lineups: pd.DataFrame) -> pd.DataFrame:
    offence = lineups.loc[:, [
        "match_id", "home_lineup_off", "away_lineup_off"]]
    joined = matches.merge(offence, on="match_id", how="left")
    clubs: dict[int, _ClubForm] = {}
    rows: list[dict[str, float | int]] = []
    for _game_date, group in joined.groupby("game_date", sort=False):
        snapped: list[tuple[object, dict[str, float]]] = []
        for row in group.itertuples(index=False):
            home = _snapshot_form(
                clubs, int(row.home_team), int(row.season),
                _finite(row.home_lineup_off))
            away = _snapshot_form(
                clubs, int(row.away_team), int(row.season),
                _finite(row.away_lineup_off))
            snapped.append((row, _prefix_form(home, away)))
        for row, form in snapped:
            form["match_id"] = int(row.match_id)
            rows.append(form)
            if _played(row):
                _commit_form(
                    clubs, int(row.home_team), float(row.home_team_goals),
                    _finite(row.home_team_sog), _finite(row.away_team_sog))
                _commit_form(
                    clubs, int(row.away_team), float(row.away_team_goals),
                    _finite(row.away_team_sog), _finite(row.home_team_sog))
    return pd.DataFrame(rows)


def _snapshot_form(
        clubs: dict[int, _ClubForm],
        team_id: int,
        season: int,
        lineup_off: float | None) -> dict[str, float]:
    form = clubs.setdefault(team_id, _ClubForm())
    if form.season != season:
        _roll_form(form)
        form.season = season
    goals_delta, shot_delta = _form_rates(form)
    off_delta = _off_delta(form)
    form.pending_off = lineup_off
    return {
        "season_game_index": float(min(form.games, SEASON_INDEX_CAP)),
        "early_form_goals_per_60": goals_delta,
        "early_form_shot_share": shot_delta,
        "early_form_off": off_delta}


def _form_rates(form: _ClubForm) -> tuple[float, float]:
    if form.games <= 0:
        return 0.0, 0.0
    goals_rate = form.goals / form.games
    shot_total = form.sog_for + form.sog_against
    if shot_total <= 0.0:
        shot_share = form.prev_shot_share
    else:
        shot_share = form.sog_for / shot_total
    return (
        goals_rate - form.prev_goals_per_60,
        shot_share - form.prev_shot_share)


def _off_delta(form: _ClubForm) -> float:
    """Season-to-date lineup offence minus the previous season mean."""
    if form.off_games <= 0 or form.prev_off is None:
        return 0.0
    return form.off_sum / form.off_games - form.prev_off


def _roll_form(form: _ClubForm) -> None:
    if form.games > 0:
        form.prev_goals_per_60 = form.goals / form.games
        shot_total = form.sog_for + form.sog_against
        if shot_total > 0.0:
            form.prev_shot_share = form.sog_for / shot_total
    # Średnia sezonu, nie skład jednego ostatniego meczu.
    if form.off_games > 0:
        form.prev_off = form.off_sum / form.off_games
    form.games = 0
    form.goals = 0.0
    form.sog_for = 0.0
    form.sog_against = 0.0
    form.off_sum = 0.0
    form.off_games = 0
    form.pending_off = None


def _commit_form(
        clubs: dict[int, _ClubForm],
        team_id: int,
        goals: float,
        sog_for: float | None,
        sog_against: float | None) -> None:
    form = clubs.setdefault(team_id, _ClubForm())
    form.games += 1
    form.goals += goals
    if form.pending_off is not None:
        form.off_sum += form.pending_off
        form.off_games += 1
        form.pending_off = None
    if sog_for is None or sog_against is None:
        return
    form.sog_for += sog_for
    form.sog_against += sog_against


def _prefix_form(
        home: dict[str, float],
        away: dict[str, float]) -> dict[str, float]:
    prefixed: dict[str, float] = {}
    for key, value in home.items():
        prefixed[f"home_{key}"] = value
    for key, value in away.items():
        prefixed[f"away_{key}"] = value
    return prefixed


def _targets(matches: pd.DataFrame) -> pd.DataFrame:
    result = matches["result"].astype(str).str.strip()
    played_mask = result.isin(_FINISHED_RESULTS)
    played_mask &= matches["home_team_goals"].notna()
    played_mask &= matches["away_team_goals"].notna()
    played = matches.loc[played_mask].copy()
    if played.empty:
        return pd.DataFrame(columns=["match_id", *_TARGET_COLUMNS])
    labels = HockeyGoalsLabeler().build_labels(played)
    labels.insert(0, "match_id", played["match_id"].to_numpy())
    return labels


def _join_features(
        matches: pd.DataFrame,
        ratings: pd.DataFrame,
        schedule: pd.DataFrame,
        lineups: pd.DataFrame,
        goalies: pd.DataFrame,
        shared: pd.DataFrame,
        early: pd.DataFrame,
        labeled: pd.DataFrame) -> pd.DataFrame:
    frame = matches.loc[:, _IDENTITY].merge(ratings, on="match_id", how="left")
    frame = frame.merge(schedule, on="match_id", how="left")
    lineup_columns = [
        "match_id",
        *[
            f"{side}_{name}"
            for side in ("home", "away")
            for name in _LINEUP_VALUES]]
    frame = frame.merge(
        lineups.loc[:, lineup_columns], on="match_id", how="left")
    goalie_columns = [
        "match_id",
        "home_goalie_save_pct",
        "away_goalie_save_pct",
        "home_goalie_gsaa_per_60",
        "away_goalie_gsaa_per_60",
        "home_team_save_pct",
        "away_team_save_pct"]
    frame = frame.merge(
        goalies.loc[:, goalie_columns], on="match_id", how="left")
    frame = frame.merge(shared, on="match_id", how="left")
    frame = frame.merge(early, on="match_id", how="left")
    frame = frame.merge(labeled, on="match_id", how="left")
    _add_rating_diffs(frame)
    _add_side_diffs(frame)
    return _select_feature_columns(frame)


def _add_rating_diffs(frame: pd.DataFrame) -> None:
    for stem, home, away in _RATING_PAIRS:
        frame[f"{stem}_diff"] = frame[home] - frame[away]


def _add_side_diffs(frame: pd.DataFrame) -> None:
    for stem in _SIDE_STEMS:
        frame[f"{stem}_diff"] = (
            frame[f"home_{stem}"] - frame[f"away_{stem}"])


def _select_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    selected = frame.copy()
    for column in HOCKEY_GBM_FEATURE_COLUMNS:
        if column not in selected.columns:
            selected[column] = np.nan
    ordered = _IDENTITY + _TARGET_COLUMNS + HOCKEY_GBM_FEATURE_COLUMNS
    return selected.loc[:, ordered]


def _played(row: object) -> bool:
    result = str(getattr(row, "result", "")).strip()
    if result not in _FINISHED_RESULTS:
        return False
    return (
        not _missing(getattr(row, "home_team_goals", None))
        and not _missing(getattr(row, "away_team_goals", None)))


def _is_playoff(value: object) -> float:
    parsed = _optional_int(value)
    if parsed is None:
        return 0.0
    return 1.0 if parsed >= PLAYOFF_ROUND else 0.0


def _optional_int(value: object) -> int | None:
    number = _finite(value)
    if number is None or not float(number).is_integer():
        return None
    return int(number)


def _empty_net(value: object) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed < 0:
        return 0
    return parsed


def _finite(value: object) -> float | None:
    if _missing(value) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _as_datetime(value: object) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
