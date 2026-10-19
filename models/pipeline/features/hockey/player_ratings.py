"""As-of skater ratings: points, shots and team-relative plus-minus.

Ratings are an EWMA of a per-60 rate, shrunk toward the slot mean.
A player with no history takes that mean. Plus-minus is measured
against the team's own average in the same game, so a blowout does
not look like defence. The early-season multiplier raises EWMA alpha
from the player's games already played in the season. Snapshot a
whole slate before ``update``, or the current game leaks in.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

import pandas as pd

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.early_season import early_season_alpha
from models.pipeline.features.hockey.line_slots import SKATER_SLOTS
from models.pipeline.features.hockey.line_slots import LineSlotResolver


PLAYER_RATING_ALPHA = 0.1
OFF_PRIOR_GAMES = 20.0
SHOT_PRIOR_GAMES = 20.0
DEF_PRIOR_GAMES = 40.0
# Zimny start, zanim slot ma własne obserwacje (punkty i strzały / 60).
DEFAULT_SLOT_OFF = {
    "F1": 2.6,
    "F2": 2.3,
    "F3": 1.6,
    "F4": 1.2,
    "D1": 1.3,
    "D2": 1.0,
    "D3": 0.8
}
DEFAULT_SLOT_SHOT = {
    "F1": 7.4,
    "F2": 7.0,
    "F3": 6.1,
    "F4": 5.2,
    "D1": 4.2,
    "D2": 3.9,
    "D3": 3.4
}
STAT_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "slot",
    "season",
    "game_date",
    "points",
    "sog",
    "plus_minus",
    "toi_seconds"
]
PLAYER_RATING_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "game_date",
    "season",
    "slot",
    "off_rating",
    "shot_rating",
    "def_rating",
    "season_games_played"
]


def _default_off() -> dict[str, float]:
    return dict(DEFAULT_SLOT_OFF)


def _default_shot() -> dict[str, float]:
    return dict(DEFAULT_SLOT_SHOT)


@dataclass(frozen=True)
class PlayerRatingsConfig:
    """EWMA speed, shrinkage priors and the empty-slot means."""

    alpha: float = PLAYER_RATING_ALPHA
    off_prior_games: float = OFF_PRIOR_GAMES
    shot_prior_games: float = SHOT_PRIOR_GAMES
    def_prior_games: float = DEF_PRIOR_GAMES
    early_season: EarlySeasonConfig = field(
        default_factory=EarlySeasonConfig)
    initial_off: dict[str, float] = field(default_factory=_default_off)
    initial_shot: dict[str, float] = field(default_factory=_default_shot)
    initial_def: float = 0.0


@dataclass(frozen=True)
class PlayerRating:
    """Skater strength measured before the current appearance."""

    off_rating: float
    shot_rating: float
    def_rating: float
    season_games_played: int


@dataclass
class _PlayerForm:
    off_ewma: float | None = None
    shot_ewma: float | None = None
    def_ewma: float | None = None
    games: int = 0
    season_games: int = 0
    season: int | None = None


@dataclass(frozen=True)
class _Appearance:
    match_id: int
    player_id: int
    team_id: int
    slot: str
    season: int
    game_date: datetime
    points: float | None
    sog: float | None
    plus_minus: float | None
    toi_seconds: float | None


class HockeyPlayerRatingState:
    """Per-player form. Snapshot a slate, then ``update`` the match.

    ``snapshot`` needs the slot about to be played: a new player is
    the mean of that slot, and a line change shrinks toward the new
    one. ``season`` resets only the early-season counter. Dates must
    not move backwards.
    """

    def __init__(
            self,
            config: PlayerRatingsConfig | None = None) -> None:
        self._config = config or PlayerRatingsConfig()
        self._check_config()
        self._off_initial = _merged_slots(
            DEFAULT_SLOT_OFF, self._config.initial_off)
        self._shot_initial = _merged_slots(
            DEFAULT_SLOT_SHOT, self._config.initial_shot)
        self._players: dict[int, _PlayerForm] = {}
        self._off_sum: dict[str, float] = {}
        self._off_count: dict[str, int] = {}
        self._shot_sum: dict[str, float] = {}
        self._shot_count: dict[str, int] = {}
        self._def_sum: dict[str, float] = {}
        self._def_count: dict[str, int] = {}
        self._last_date: datetime | None = None

    def snapshot(
            self,
            player_id: int,
            slot: str,
            season: int,
            game_date: datetime,
            *,
            record_date: bool = True) -> PlayerRating:
        """Return ratings using only games strictly before this one.

        ``record_date`` stays false when scoring a future match, so
        the read does not move the cursor learned from box scores.
        A new season reports zero games played. The stored counter
        changes only in ``update``.
        """
        self._require_skater_slot(slot)
        self._require_forward_date(game_date, record=record_date)
        form = self._players.get(player_id)
        games = 0 if form is None else form.games
        season_games = _games_before_season(form, season)
        return PlayerRating(
            off_rating=_shrink(
                None if form is None else form.off_ewma,
                games,
                self._slot_off(slot),
                self._config.off_prior_games),
            shot_rating=_shrink(
                None if form is None else form.shot_ewma,
                games,
                self._slot_shot(slot),
                self._config.shot_prior_games),
            def_rating=_shrink(
                None if form is None else form.def_ewma,
                games,
                self._slot_def(slot),
                self._config.def_prior_games),
            season_games_played=season_games)

    def update(self, match_rows: pd.DataFrame) -> None:
        """Learn one match after its pre-match snapshots."""
        if match_rows.empty:
            return
        rows = _appearances(match_rows)
        _require_one_match(rows)
        self._require_forward_date(rows[0].game_date)
        learned = [row for row in rows if _can_learn(row)]
        relatives = _relative_plus_minus(learned)
        for row in learned:
            self._learn(row, relatives[row.player_id])

    def _check_config(self) -> None:
        if self._config.alpha <= 0 or self._config.alpha > 1:
            raise ValueError("player-rating alpha must be in (0, 1]")
        priors = (
            self._config.off_prior_games,
            self._config.shot_prior_games,
            self._config.def_prior_games)
        if any(prior <= 0 for prior in priors):
            raise ValueError("shrinkage priors must be positive")

    def _learn(self, row: _Appearance, relative_pm: float) -> None:
        form = self._players.get(row.player_id)
        if form is None:
            form = _PlayerForm(season=row.season)
            self._players[row.player_id] = form
        elif form.season != row.season:
            form.season = row.season
            form.season_games = 0
        alpha = early_season_alpha(
            self._config.alpha,
            form.season_games,
            self._config.early_season)
        points_per_60 = _per_60(row.points or 0.0, row.toi_seconds or 0.0)
        shots_per_60 = _per_60(row.sog or 0.0, row.toi_seconds or 0.0)
        form.off_ewma = _ewma(form.off_ewma, points_per_60, alpha)
        form.shot_ewma = _ewma(form.shot_ewma, shots_per_60, alpha)
        form.def_ewma = _ewma(form.def_ewma, relative_pm, alpha)
        form.games += 1
        form.season_games += 1
        self._add_slot(row.slot, points_per_60, shots_per_60, relative_pm)

    def _add_slot(
            self,
            slot: str,
            points_per_60: float,
            shots_per_60: float,
            relative_pm: float) -> None:
        self._off_sum[slot] = self._off_sum.get(slot, 0.0) + points_per_60
        self._off_count[slot] = self._off_count.get(slot, 0) + 1
        self._shot_sum[slot] = (
            self._shot_sum.get(slot, 0.0) + shots_per_60)
        self._shot_count[slot] = self._shot_count.get(slot, 0) + 1
        self._def_sum[slot] = self._def_sum.get(slot, 0.0) + relative_pm
        self._def_count[slot] = self._def_count.get(slot, 0) + 1

    def _slot_off(self, slot: str) -> float:
        return _mean(
            self._off_sum.get(slot, 0.0),
            self._off_count.get(slot, 0),
            self._off_initial[slot])

    def _slot_shot(self, slot: str) -> float:
        return _mean(
            self._shot_sum.get(slot, 0.0),
            self._shot_count.get(slot, 0),
            self._shot_initial[slot])

    def _slot_def(self, slot: str) -> float:
        return _mean(
            self._def_sum.get(slot, 0.0),
            self._def_count.get(slot, 0),
            self._config.initial_def)

    def _require_skater_slot(self, slot: str) -> None:
        if slot not in SKATER_SLOTS:
            raise ValueError(f"Unsupported skater slot: {slot}")

    def _require_forward_date(
            self,
            game_date: object,
            *,
            record: bool = True) -> datetime:
        moment = _as_datetime(game_date)
        if self._last_date is not None and moment < self._last_date:
            raise ValueError(
                "Player ratings require chronological game dates. "
                f"Got {moment} after {self._last_date}.")
        # Sam odczyt przyszłego meczu nie przesuwa kursora.
        if record:
            self._last_date = moment
        return moment


def build_player_ratings(
        appearances: pd.DataFrame,
        config: PlayerRatingsConfig | None = None) -> pd.DataFrame:
    """Return a pre-match slot and rating for every skater appearance.

    Goalies are omitted; their form lives in ``goalies.py``. Rows that
    share ``game_date`` are snapshotted before any of them is learned.
    """
    settings = config or PlayerRatingsConfig()
    assigned = LineSlotResolver().assign(appearances)
    prepared = _prepare_skaters(assigned)
    if prepared.empty:
        return _empty_ratings(prepared)
    state = HockeyPlayerRatingState(settings)
    rows: list[dict[str, object]] = []
    for game_date, slate in prepared.groupby("game_date", sort=False):
        del game_date
        rows.extend(_snapshot_slate(state, slate))
        for _, match_rows in slate.groupby("match_id", sort=False):
            state.update(match_rows)
    return pd.DataFrame(rows)


def _prepare_skaters(assigned: pd.DataFrame) -> pd.DataFrame:
    required = [
        column for column in STAT_COLUMNS
        if column != "slot"]
    missing = [
        column for column in required
        if column not in assigned.columns]
    if missing:
        raise KeyError(f"Missing skater columns: {missing}")
    if "slot" not in assigned.columns:
        raise KeyError("Missing skater columns: ['slot']")
    ready = assigned.loc[
        assigned["slot"].isin(SKATER_SLOTS)
        & assigned["game_date"].notna()
        & assigned["player_id"].notna()].copy()
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    return ready.sort_values(
        ["game_date", "match_id", "player_id"]).reset_index(drop=True)


def _empty_ratings(prepared: pd.DataFrame) -> pd.DataFrame:
    frame = prepared.copy()
    for column in ("off_rating", "shot_rating", "def_rating"):
        frame[column] = pd.Series(dtype="float64")
    frame["season_games_played"] = pd.Series(dtype="int64")
    columns = [
        column for column in PLAYER_RATING_COLUMNS if column in frame.columns]
    return frame.loc[:, columns]


def _snapshot_slate(
        state: HockeyPlayerRatingState,
        slate: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in slate.itertuples(index=False):
        rating = state.snapshot(
            int(row.player_id),
            str(row.slot),
            int(row.season),
            row.game_date)
        rows.append({
            "match_id": int(row.match_id),
            "player_id": int(row.player_id),
            "team_id": int(row.team_id),
            "game_date": row.game_date,
            "season": int(row.season),
            "slot": str(row.slot),
            "off_rating": rating.off_rating,
            "shot_rating": rating.shot_rating,
            "def_rating": rating.def_rating,
            "season_games_played": rating.season_games_played
        })
    return rows


def _appearances(frame: pd.DataFrame) -> list[_Appearance]:
    missing = [
        column for column in STAT_COLUMNS
        if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing skater columns: {missing}")
    rows: list[_Appearance] = []
    for row in frame.itertuples(index=False):
        rows.append(_Appearance(
            match_id=int(row.match_id),
            player_id=int(row.player_id),
            team_id=int(row.team_id),
            slot=str(row.slot),
            season=int(row.season),
            game_date=_as_datetime(row.game_date),
            points=_optional_float(row.points),
            sog=_optional_float(row.sog),
            plus_minus=_optional_float(row.plus_minus),
            toi_seconds=_optional_float(row.toi_seconds)))
    return rows


def _require_one_match(rows: list[_Appearance]) -> None:
    match_ids = {row.match_id for row in rows}
    if len(match_ids) != 1:
        raise ValueError("update() learns one match at a time")
    dates = {row.game_date for row in rows}
    if len(dates) != 1:
        raise ValueError("update() learned rows must share a game date")


def _games_before_season(form: _PlayerForm | None, season: int) -> int:
    """Games already played in ``season``. A new season reads as zero."""
    if form is None or form.season not in (None, season):
        return 0
    return form.season_games


def _can_learn(row: _Appearance) -> bool:
    # Bez czasu na lodzie stawka na 60 minut nie istnieje.
    if row.toi_seconds is None or row.toi_seconds <= 0:
        return False
    if row.slot not in SKATER_SLOTS:
        return False
    return (
        row.points is not None
        and row.sog is not None
        and row.plus_minus is not None)


def _relative_plus_minus(rows: list[_Appearance]) -> dict[int, float]:
    # Średnia drużyny w tym meczu zdejmuje wynik całego zespołu.
    by_team: dict[int, list[float]] = {}
    player_rate: dict[int, float] = {}
    player_team: dict[int, int] = {}
    for row in rows:
        rate = _per_60(row.plus_minus or 0.0, row.toi_seconds or 0.0)
        player_rate[row.player_id] = rate
        player_team[row.player_id] = row.team_id
        by_team.setdefault(row.team_id, []).append(rate)
    team_mean = {
        team_id: sum(rates) / len(rates)
        for team_id, rates in by_team.items()
    }
    return {
        player_id: rate - team_mean[player_team[player_id]]
        for player_id, rate in player_rate.items()
    }


def _shrink(
        ewma: float | None,
        games: int,
        slot_mean: float,
        prior_games: float) -> float:
    if games <= 0 or ewma is None:
        return slot_mean
    weight = float(games)
    return (weight * ewma + prior_games * slot_mean) / (weight + prior_games)


def _ewma(previous: float | None, value: float, alpha: float) -> float:
    # Pierwsza obserwacja nie ma stanu, z którym dałoby się ją zmieszać.
    if previous is None:
        return value
    return alpha * value + (1.0 - alpha) * previous


def _per_60(value: float, toi_seconds: float) -> float:
    return value * 3600.0 / toi_seconds


def _mean(total: float, count: int, fallback: float) -> float:
    if count <= 0:
        return fallback
    return total / count


def _merged_slots(
        fallback: dict[str, float],
        override: dict[str, float]) -> dict[str, float]:
    merged = dict(fallback)
    merged.update(override)
    missing = [slot for slot in SKATER_SLOTS if slot not in merged]
    if missing:
        raise ValueError(f"Missing slot priors: {missing}")
    return merged


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _as_datetime(value: object) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
