"""Pre-match features for one NHL skater appearance.

Counting stats use an EWMA whose memory is about 10 and 30 games.
Ratings and ``slot_toi`` come from the line slot, so a higher line
raises expected ice time. Team expected goals are the as-of GAP
rate ``(attack + opponent defence) / 2``. The production Dixon-Coles
fit has already seen later games, so it is not a historical feature.
Power-play unit is kept for prediction; historical rosters do not
store it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

import numpy as np
import pandas as pd

from models.pipeline.core.config import FeatureConfig
from models.pipeline.core.registry import register_feature_builder
from models.pipeline.features.hockey.early_season import early_season_alpha
from models.pipeline.features.hockey.goalies import GOALIE_APPEARANCE_COLUMNS
from models.pipeline.features.hockey.goalies import GoalieRatingState
from models.pipeline.features.hockey.line_slots import GOALIE_POSITION
from models.pipeline.features.hockey.line_slots import SKATER_SLOTS
from models.pipeline.features.hockey.line_slots import LineSlotResolver
from models.pipeline.features.hockey.line_slots import SlotMinuteCarry
from models.pipeline.features.hockey.line_slots import carry_slot_minutes
from models.pipeline.features.hockey.line_slots import slot_for_labels
from models.pipeline.features.hockey.player_ratings import (
    HockeyPlayerRatingState)
from models.pipeline.features.hockey.player_ratings import (
    build_player_ratings)
from models.pipeline.features.hockey.ratings import HockeyTeamRatingState
from models.pipeline.features.hockey.ratings import (
    build_hockey_pre_match_ratings)
from models.pipeline.features.hockey.schedule import build_schedule_features
from models.pipeline.labels.hockey_player_props import TARGET_COLUMNS


COUNTING_STATS = ("sog", "goals", "assists", "points")
EWMA_WINDOWS = (10, 30)
_FINISHED_RESULTS = frozenset({"1", "X", "2"})
_ARENA_COLUMNS = ["team_id", "latitude", "longitude", "timezone"]
_ROSTER_FIELDS = [
    "match_id",
    "player_id",
    "team_id",
    "position",
    "line",
    "game_date",
    "season"]
_STAT_FIELDS = [
    "goals",
    "assists",
    "points",
    "sog",
    "plus_minus",
    "toi_seconds",
    "shots_against",
    "shots_saved"]
_ID_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "game_date",
    "season"]


def _ewma_columns() -> list[str]:
    columns = [f"toi_per_game_{window}" for window in EWMA_WINDOWS]
    for stat in COUNTING_STATS:
        for window in EWMA_WINDOWS:
            columns.append(f"{stat}_per_game_{window}")
            columns.append(f"{stat}_per_60_{window}")
    return columns


EWMA_COLUMNS = _ewma_columns()
PLAYER_PROP_FEATURE_COLUMNS = [
    "off_rating",
    "shot_rating",
    "def_rating",
    "slot_toi",
    "pp_unit",
    "line_number",
    "is_forward",
    "is_home",
    "is_b2b",
    *EWMA_COLUMNS,
    "team_expected_goals",
    "opp_shots_allowed",
    "opp_goalie_save_pct"]
_FEATURE_FRAME_COLUMNS = (
    _ID_COLUMNS + PLAYER_PROP_FEATURE_COLUMNS + TARGET_COLUMNS)


def ewma_alpha(window: int) -> float:
    """Return the EWMA weight whose memory is about ``window`` games."""
    if window < 1:
        raise ValueError("EWMA window must be positive")
    return 2.0 / (window + 1.0)


def build_hockey_player_features(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        arenas: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return one pre-match row per historical skater appearance.

    Goalies are omitted. Rows that share ``game_date`` are read
    before any of them updates a player's EWMA.
    """
    appearances = _skater_appearances(rosters, player_stats)
    if appearances.empty:
        return _empty_feature_frame()
    counted, _forms = _walk_counting(appearances)
    ratings = build_player_ratings(appearances)
    slot_toi = LineSlotResolver().build_slot_toi(appearances)
    context = _match_context(matches, player_stats, rosters, arenas)
    return _assemble(counted, ratings, slot_toi, context)


@register_feature_builder("HockeyPlayerFeatureBuilder")
class HockeyPlayerFeatureBuilder:
    """Registry wrapper around ``build_hockey_player_features``."""

    def __init__(self) -> None:
        self.rosters = pd.DataFrame()
        self.player_stats = pd.DataFrame()
        self.arenas = pd.DataFrame()

    def build_features(
            self,
            frame: pd.DataFrame,
            config: FeatureConfig) -> pd.DataFrame:
        """Build features for ``frame``. Auxiliaries are set on self."""
        del config
        return build_hockey_player_features(
            frame,
            self.rosters,
            self.player_stats,
            self.arenas)


@dataclass(frozen=True)
class PrematchContext:
    """As-of team rates and back-to-back flags for one match."""

    home_expected_goals: float
    away_expected_goals: float
    home_opponent_shots: float
    away_opponent_shots: float
    home_b2b: float
    away_b2b: float


@dataclass
class PlayerPropMemory:
    """Form after the last box score, ready for the next games.

    Team and goalie snapshots move the cursor forward. Score matches
    in date order. Skater ratings are read with ``record_date`` false
    so a slate of players does not have to be learned.
    """

    forms: dict[int, dict[str, float]]
    ratings: HockeyPlayerRatingState
    slot_minutes: SlotMinuteCarry
    goalies: GoalieRatingState
    teams: HockeyTeamRatingState
    b2b: dict[int, tuple[float, float]]
    _cache: dict[int, PrematchContext] = field(default_factory=dict)

    def prematch(
            self,
            match_id: int,
            home_team: int,
            away_team: int,
            season: int,
            game_date: datetime) -> PrematchContext:
        """Return GAP expected goals and schedule flags for one match."""
        key = int(match_id)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        snapshot = self.teams.snapshot(
            int(home_team),
            int(away_team),
            int(season),
            game_date)
        home_b2b, away_b2b = self.b2b.get(key, (math.nan, math.nan))
        context = PrematchContext(
            home_expected_goals=_pair(
                snapshot["home_gap_att"], snapshot["away_gap_def"]),
            away_expected_goals=_pair(
                snapshot["away_gap_att"], snapshot["home_gap_def"]),
            home_opponent_shots=float(snapshot["away_sog_gap_def"]),
            away_opponent_shots=float(snapshot["home_sog_gap_def"]),
            home_b2b=home_b2b,
            away_b2b=away_b2b)
        self._cache[key] = context
        return context

    def goalie_save(
            self,
            players: list[object],
            game_date: datetime) -> float:
        """Return start-weighted save% of the goalies in one lineup."""
        goalies = [player for player in players if _player_is_goalie(player)]
        if not goalies:
            return math.nan
        rated: list[tuple[float, float]] = []
        for player in goalies:
            rating = self.goalies.snapshot(
                int(_player_attr(player, "player_id")), game_date)
            rated.append((
                float(rating.save_pct),
                _start_weight(player)))
        return _weighted_mean(rated)

    def skater_features(
            self,
            context: PrematchContext,
            player: object,
            team_id: int,
            is_home: bool,
            opponent_save: float,
            season: int,
            game_date: datetime) -> dict[str, float] | None:
        """Return one model row, or None when the player has no skater slot."""
        slot = slot_for_labels(
            _player_attr(player, "position"),
            _player_attr(player, "line"))
        if slot not in SKATER_SLOTS:
            return None
        rating = self.ratings.snapshot(
            int(_player_attr(player, "player_id")),
            slot,
            int(season),
            game_date,
            record_date=False)
        minutes = self.slot_minutes.for_team(int(team_id), int(season))
        features = {column: math.nan for column in PLAYER_PROP_FEATURE_COLUMNS}
        stored = self.forms.get(int(_player_attr(player, "player_id")))
        if stored is not None:
            features.update(stored)
        features["off_rating"] = rating.off_rating
        features["shot_rating"] = rating.shot_rating
        features["def_rating"] = rating.def_rating
        features["slot_toi"] = float(minutes.get(slot, math.nan))
        features["pp_unit"] = _optional_float(
            _player_attr(player, "pp_unit"))
        features["line_number"] = float(slot[1])
        features["is_forward"] = 1.0 if slot.startswith("F") else 0.0
        features["is_home"] = 1.0 if is_home else 0.0
        features["is_b2b"] = (
            context.home_b2b if is_home else context.away_b2b)
        features["team_expected_goals"] = (
            context.home_expected_goals
            if is_home else context.away_expected_goals)
        features["opp_shots_allowed"] = (
            context.home_opponent_shots
            if is_home else context.away_opponent_shots)
        features["opp_goalie_save_pct"] = float(opponent_save)
        return features


def prepare_player_prop_memory(
        matches: pd.DataFrame,
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        arenas: pd.DataFrame | None = None) -> PlayerPropMemory:
    """Replay box scores once and keep the state for the next games."""
    appearances = _skater_appearances(rosters, player_stats)
    _counted, forms = _walk_counting(appearances)
    return PlayerPropMemory(
        forms=forms,
        ratings=_replay_player_ratings(appearances),
        slot_minutes=_carried_minutes(appearances),
        goalies=_replay_goalies(rosters, player_stats),
        teams=_replay_teams(matches),
        b2b=_b2b_index(matches, arenas))


def _skater_appearances(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame) -> pd.DataFrame:
    merged = _merge_box_scores(rosters, player_stats)
    if merged.empty:
        return merged
    assigned = LineSlotResolver().assign(merged)
    skaters = assigned.loc[
        assigned["slot"].isin(SKATER_SLOTS)].copy()
    skaters = _finite_targets(skaters)
    if skaters.empty:
        return skaters
    skaters["game_date"] = pd.to_datetime(skaters["game_date"])
    return skaters.sort_values(
        ["game_date", "match_id", "player_id"]).reset_index(drop=True)


def _merge_box_scores(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column for column in _ROSTER_FIELDS
        if column not in rosters.columns]
    if missing:
        raise KeyError(f"Missing roster columns: {missing}")
    roster = rosters.loc[:, _roster_columns(rosters)].copy()
    position = roster["position"].astype(str).str.strip().str.upper()
    roster = roster.loc[position != GOALIE_POSITION]
    stats = _stat_slice(player_stats)
    merged = roster.merge(
        stats, on=["match_id", "player_id", "team_id"], how="inner")
    for column in ("toi_seconds", "plus_minus", *TARGET_COLUMNS):
        if column not in merged.columns:
            merged[column] = pd.NA
    return merged.drop_duplicates(
        ["match_id", "player_id", "team_id"]).reset_index(drop=True)


def _roster_columns(rosters: pd.DataFrame) -> list[str]:
    columns = list(_ROSTER_FIELDS)
    if "pp" in rosters.columns:
        columns.append("pp")
    return columns


def _stat_slice(player_stats: pd.DataFrame) -> pd.DataFrame:
    columns = ["match_id", "player_id", "team_id"]
    columns.extend(
        column for column in _STAT_FIELDS
        if column in player_stats.columns)
    if player_stats.empty:
        return pd.DataFrame(columns=columns)
    return player_stats.loc[:, columns]


def _finite_targets(frame: pd.DataFrame) -> pd.DataFrame:
    ready = frame.copy()
    mask = np.ones(len(ready), dtype=bool)
    for column in TARGET_COLUMNS:
        if column not in ready.columns:
            raise KeyError(f"Missing skater target: {column}")
        values = pd.to_numeric(ready[column], errors="coerce")
        ready[column] = values
        mask &= values.notna().to_numpy() & (values.to_numpy() >= 0)
    return ready.loc[mask].reset_index(drop=True)


@dataclass
class _CountingForm:
    """EWMA values plus the season counter that speeds the blend."""

    values: dict[str, float]
    season: int | None = None
    season_games: int = 0


def _walk_counting(
        appearances: pd.DataFrame
) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    forms: dict[int, _CountingForm] = {}
    if appearances.empty:
        return _empty_counted(), {}
    records: list[dict[str, object]] = []
    for _game_date, slate in appearances.groupby("game_date", sort=False):
        rows = list(slate.itertuples(index=False))
        for row in rows:
            records.append(_counting_record(row, forms))
        for row in rows:
            _learn_counting(forms, row)
    carried = {
        player_id: form.values for player_id, form in forms.items()}
    return pd.DataFrame(records), carried


def _counting_record(
        row: object,
        forms: dict[int, _CountingForm]) -> dict[str, object]:
    player_id = int(getattr(row, "player_id"))
    state = forms.get(player_id)
    stored = _blank_form() if state is None else state.values
    record: dict[str, object] = {
        "match_id": int(getattr(row, "match_id")),
        "player_id": player_id,
        "team_id": int(getattr(row, "team_id")),
        "game_date": getattr(row, "game_date"),
        "season": int(getattr(row, "season")),
        "pp_unit": _optional_float(getattr(row, "pp", None))}
    for column in TARGET_COLUMNS:
        record[column] = float(getattr(row, column))
    record.update(stored)
    return record


def _learn_counting(
        forms: dict[int, _CountingForm],
        row: object) -> None:
    player_id = int(getattr(row, "player_id"))
    season = int(getattr(row, "season"))
    state = forms.get(player_id)
    if state is None:
        state = _CountingForm(values=_blank_form(), season=season)
        forms[player_id] = state
    elif state.season != season:
        # Nowy sezon startuje licznik od zera, jak ratingi zawodnika.
        state.season = season
        state.season_games = 0
    form = state.values
    minutes = _toi_minutes(getattr(row, "toi_seconds", None))
    counts = {
        stat: _optional_float(getattr(row, stat))
        for stat in COUNTING_STATS}
    for window in EWMA_WINDOWS:
        # m(g) podnosi alpha przez pierwsze 8 meczów, z sufitem 0.5.
        alpha = early_season_alpha(
            ewma_alpha(window), state.season_games)
        toi_key = f"toi_per_game_{window}"
        form[toi_key] = _blend(form[toi_key], minutes, alpha)
        for stat, value in counts.items():
            per_game = f"{stat}_per_game_{window}"
            per_60 = f"{stat}_per_60_{window}"
            form[per_game] = _blend(form[per_game], value, alpha)
            rate = _per_60(value, minutes)
            form[per_60] = _blend(form[per_60], rate, alpha)
    state.season_games += 1


def _blank_form() -> dict[str, float]:
    return {column: math.nan for column in EWMA_COLUMNS}


def _blend(previous: float, value: float | None, alpha: float) -> float:
    if value is None or not math.isfinite(value):
        return previous
    if not math.isfinite(previous):
        return value
    return alpha * value + (1.0 - alpha) * previous


def _per_60(value: float | None, minutes: float | None) -> float | None:
    if value is None or minutes is None or minutes <= 0.0:
        return None
    return value * 60.0 / minutes


def _toi_minutes(raw: object) -> float | None:
    seconds = _optional_float(raw)
    if seconds is None:
        return None
    return seconds / 60.0


def _assemble(
        counted: pd.DataFrame,
        ratings: pd.DataFrame,
        slot_toi: pd.DataFrame,
        context: pd.DataFrame) -> pd.DataFrame:
    if counted.empty or ratings.empty or context.empty:
        return _empty_feature_frame()
    rated = counted.merge(
        ratings.loc[:, [
            "match_id",
            "player_id",
            "slot",
            "off_rating",
            "shot_rating",
            "def_rating"]],
        on=["match_id", "player_id"],
        how="inner")
    minutes = _slot_minutes(slot_toi)
    merged = rated.merge(
        minutes, on=["match_id", "team_id", "slot"], how="left")
    merged = merged.merge(context, on="match_id", how="inner")
    if merged.empty:
        return _empty_feature_frame()
    return _project(merged)


def _slot_minutes(slot_toi: pd.DataFrame) -> pd.DataFrame:
    if slot_toi.empty:
        return pd.DataFrame(columns=[
            "match_id", "team_id", "slot", "slot_toi_minutes"])
    return slot_toi.loc[:, [
        "match_id", "team_id", "slot", "slot_toi_minutes"]]


def _project(frame: pd.DataFrame) -> pd.DataFrame:
    home = frame["team_id"].to_numpy() == frame["home_team"].to_numpy()
    projected = pd.DataFrame({
        "match_id": frame["match_id"].to_numpy(),
        "player_id": frame["player_id"].to_numpy(),
        "team_id": frame["team_id"].to_numpy(),
        "game_date": frame["game_date"].to_numpy(),
        "season": frame["season"].to_numpy(),
        "off_rating": frame["off_rating"].to_numpy(dtype=float),
        "shot_rating": frame["shot_rating"].to_numpy(dtype=float),
        "def_rating": frame["def_rating"].to_numpy(dtype=float),
        "slot_toi": frame["slot_toi_minutes"].to_numpy(dtype=float),
        "pp_unit": frame["pp_unit"].to_numpy(dtype=float),
        "line_number": _line_numbers(frame["slot"]),
        "is_forward": _forward_flags(frame["slot"]),
        "is_home": home.astype(float),
        "is_b2b": np.where(
            home, frame["home_is_b2b"], frame["away_is_b2b"]).astype(float),
        "team_expected_goals": np.where(
            home,
            _pair_arrays(frame["home_gap_att"], frame["away_gap_def"]),
            _pair_arrays(frame["away_gap_att"], frame["home_gap_def"])),
        "opp_shots_allowed": np.where(
            home,
            frame["away_sog_gap_def"],
            frame["home_sog_gap_def"]).astype(float),
        "opp_goalie_save_pct": np.where(
            home,
            frame["away_goalie_save_pct"],
            frame["home_goalie_save_pct"]).astype(float)})
    for column in EWMA_COLUMNS:
        projected[column] = frame[column].to_numpy(dtype=float)
    for column in TARGET_COLUMNS:
        projected[column] = frame[column].to_numpy(dtype=float)
    return projected.loc[:, _FEATURE_FRAME_COLUMNS].reset_index(drop=True)


def _line_numbers(slots: pd.Series) -> np.ndarray:
    return slots.astype(str).str[1].astype(float).to_numpy()


def _forward_flags(slots: pd.Series) -> np.ndarray:
    flags = slots.astype(str).str.startswith("F")
    return flags.astype(float).to_numpy()


def _pair_arrays(left: pd.Series, right: pd.Series) -> np.ndarray:
    return (
        left.to_numpy(dtype=float) + right.to_numpy(dtype=float)) / 2.0


def _match_context(
        matches: pd.DataFrame,
        player_stats: pd.DataFrame,
        rosters: pd.DataFrame,
        arenas: pd.DataFrame | None) -> pd.DataFrame:
    ratings = build_hockey_pre_match_ratings(
        matches,
        _goalie_appearances(rosters, player_stats),
        rosters)
    if ratings.empty:
        return pd.DataFrame()
    schedule = build_schedule_features(matches, _arenas(arenas))
    context = ratings.loc[:, [
        "match_id",
        "home_team",
        "away_team",
        "home_gap_att",
        "home_gap_def",
        "away_gap_att",
        "away_gap_def",
        "home_sog_gap_def",
        "away_sog_gap_def",
        "home_goalie_save_pct",
        "away_goalie_save_pct"]]
    b2b = schedule.loc[:, ["match_id", "home_is_b2b", "away_is_b2b"]]
    return context.merge(b2b, on="match_id", how="left")


def _goalie_appearances(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=GOALIE_APPEARANCE_COLUMNS)
    if rosters.empty or "position" not in rosters.columns:
        return empty
    position = rosters["position"].astype(str).str.strip().str.upper()
    goalies = rosters.loc[position == GOALIE_POSITION]
    if goalies.empty:
        return empty
    stats = _stat_slice(player_stats)
    merged = goalies.merge(
        stats, on=["match_id", "player_id", "team_id"], how="left")
    frame = pd.DataFrame({
        "match_id": merged["match_id"],
        "player_id": merged["player_id"],
        "team_id": merged["team_id"],
        "game_date": merged["game_date"],
        "shots_against": _column_or_nan(merged, "shots_against"),
        "shots_saved": _column_or_nan(merged, "shots_saved"),
        "toi_seconds": _column_or_nan(merged, "toi_seconds")})
    return frame.loc[:, GOALIE_APPEARANCE_COLUMNS]


def _column_or_nan(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    return frame[column]


def _arenas(arenas: pd.DataFrame | None) -> pd.DataFrame:
    if arenas is None or arenas.empty:
        return pd.DataFrame(columns=_ARENA_COLUMNS)
    return arenas


def _replay_player_ratings(
        appearances: pd.DataFrame) -> HockeyPlayerRatingState:
    state = HockeyPlayerRatingState()
    if appearances.empty:
        return state
    for _game_date, slate in appearances.groupby("game_date", sort=False):
        for _match_id, match_rows in slate.groupby("match_id", sort=False):
            state.update(match_rows)
    return state


def _carried_minutes(appearances: pd.DataFrame) -> SlotMinuteCarry:
    if appearances.empty:
        return SlotMinuteCarry.blank()
    return carry_slot_minutes(appearances)


def _replay_goalies(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame) -> GoalieRatingState:
    state = GoalieRatingState()
    appearances = _goalie_appearances(rosters, player_stats)
    if appearances.empty:
        return state
    ready = appearances.loc[appearances["game_date"].notna()].copy()
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    ready = ready.sort_values(["game_date", "match_id", "player_id"])
    for _game_date, slate in ready.groupby("game_date", sort=False):
        rows = list(slate.itertuples(index=False))
        for row in rows:
            state.snapshot(int(row.player_id), row.game_date)
        for row in rows:
            _commit_goalie(state, row)
    return state


def _commit_goalie(state: GoalieRatingState, row: object) -> None:
    shots = _optional_float(getattr(row, "shots_against", None))
    saves = _optional_float(getattr(row, "shots_saved", None))
    if shots is None or saves is None or shots <= 0.0:
        return
    toi = _optional_float(getattr(row, "toi_seconds", None))
    state.commit(
        int(getattr(row, "player_id")),
        getattr(row, "game_date"),
        shots,
        saves,
        0.0 if toi is None else toi)


def _replay_teams(matches: pd.DataFrame) -> HockeyTeamRatingState:
    state = HockeyTeamRatingState()
    finished = _finished_matches(matches)
    if finished.empty:
        return state
    for _game_date, slate in finished.groupby("game_date", sort=False):
        rows = list(slate.itertuples(index=False))
        for row in rows:
            state.snapshot(
                int(row.home_team),
                int(row.away_team),
                int(row.season),
                row.game_date)
        for row in rows:
            state.commit(
                int(row.home_team),
                int(row.away_team),
                int(row.home_team_goals),
                int(row.away_team_goals),
                _optional_int(row.home_team_sog),
                _optional_int(row.away_team_sog),
                _optional_int(row.home_team_saves),
                _optional_int(row.away_team_saves),
                _empty_net(row.home_team_en),
                _empty_net(row.away_team_en),
                _optional_int(row.ot_winner),
                _optional_int(row.so_winner))
    return state


def _finished_matches(matches: pd.DataFrame) -> pd.DataFrame:
    if matches.empty:
        return matches
    frame = matches.copy()
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    result = frame["result"].astype(str)
    mask = result.isin(_FINISHED_RESULTS)
    mask &= frame["home_team_goals"].notna()
    mask &= frame["away_team_goals"].notna()
    ready = frame.loc[mask].sort_values(["game_date", "match_id"])
    return ready.reset_index(drop=True)


def _b2b_index(
        matches: pd.DataFrame,
        arenas: pd.DataFrame | None) -> dict[int, tuple[float, float]]:
    if matches.empty:
        return {}
    schedule = build_schedule_features(matches, _arenas(arenas))
    index: dict[int, tuple[float, float]] = {}
    for row in schedule.itertuples(index=False):
        index[int(row.match_id)] = (
            _required_float(row.home_is_b2b),
            _required_float(row.away_is_b2b))
    return index


def _empty_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=_FEATURE_FRAME_COLUMNS)


def _empty_counted() -> pd.DataFrame:
    columns = _ID_COLUMNS + ["pp_unit"] + TARGET_COLUMNS + EWMA_COLUMNS
    return pd.DataFrame(columns=columns)


def _pair(left: float, right: float) -> float:
    return (float(left) + float(right)) / 2.0


def _weighted_mean(rated: list[tuple[float, float]]) -> float:
    total = sum(weight for _save, weight in rated)
    if total <= 0.0:
        return float(sum(save for save, _weight in rated) / len(rated))
    weighted = sum(save * weight for save, weight in rated)
    return float(weighted / total)


def _player_is_goalie(player: object) -> bool:
    position = _player_attr(player, "position")
    if position is None:
        return False
    return str(position).strip().upper() == GOALIE_POSITION


def _start_weight(player: object) -> float:
    probability = _optional_float(
        _player_attr(player, "start_probability"))
    if probability is not None:
        return max(0.0, probability)
    starter = _player_attr(player, "is_starting_goalie")
    if starter == 1:
        return 1.0
    return 0.0


def _player_attr(player: object, name: str) -> object:
    if isinstance(player, dict):
        return player.get(name)
    return getattr(player, name, None)


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _optional_int(value: object) -> int | None:
    number = _optional_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _empty_net(value: object) -> int:
    number = _optional_int(value)
    if number is None or number < 0:
        return 0
    return number


def _required_float(value: object) -> float:
    number = _optional_float(value)
    if number is None:
        return math.nan
    return number
