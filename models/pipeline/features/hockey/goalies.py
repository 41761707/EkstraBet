"""As-of shrunk save percentage and GSAA/60 for starting goalies."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

import pandas as pd


GOALIE_APPEARANCE_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "game_date",
    "shots_against",
    "shots_saved",
    "toi_seconds"
]
GOALIE_RATING_COLUMNS = [
    "goalie_save_pct",
    "goalie_gsaa_per_60",
    "goalie_shots"
]
# Klasyczny poziom NHL, zanim w oknie 365 dni pojawią się strzały.
DEFAULT_LEAGUE_SAVE_PRIOR = 0.9
DEFAULT_PRIOR_SHOTS = 1000.0
DEFAULT_WINDOW_DAYS = 365


@dataclass(frozen=True)
class GoalieRatingsConfig:
    """Bayesian prior and the rolling window used for goalie form."""

    prior_shots: float = DEFAULT_PRIOR_SHOTS
    window_days: int = DEFAULT_WINDOW_DAYS
    league_save_prior: float = DEFAULT_LEAGUE_SAVE_PRIOR


@dataclass(frozen=True)
class GoalieRating:
    """Goalie strength measured before the current appearance."""

    save_pct: float
    gsaa_per_60: float
    shots: float


class GoalieRatingState:
    """Rolling goalie form. Snapshot a slate, then commit it.

    Save percentage is a Bayesian average: the goalie's own shots
    and saves in the last ``window_days``, shrunk toward the league
    save rate in that same window with ``prior_shots`` of weight.
    GSAA/60 is goals saved above that league rate, per 60 minutes,
    on the same window. Dates must not move backwards. One timestamp
    is one slate: snapshot every goalie, then commit them.
    """

    def __init__(
            self,
            config: GoalieRatingsConfig | None = None) -> None:
        self._config = config or GoalieRatingsConfig()
        if self._config.prior_shots <= 0:
            raise ValueError("goalie prior_shots must be positive")
        if self._config.window_days <= 0:
            raise ValueError("goalie window_days must be positive")
        self._players: dict[int, deque] = {}
        self._league: deque = deque()
        self._league_shots = 0.0
        self._league_saves = 0.0
        self._last_date: datetime | None = None

    def snapshot(self, player_id: int, as_of: datetime) -> GoalieRating:
        """Return form using only appearances strictly before ``as_of``."""
        moment = self._require_forward_date(as_of)
        cutoff = moment - timedelta(days=self._config.window_days)
        self._evict(player_id, cutoff)
        league_shots, league_saves = self._league_before(moment)
        league_save = _rate(
            league_saves,
            league_shots,
            self._config.league_save_prior)
        shots, saves, toi_seconds = self._player_before(
            player_id, cutoff, moment)
        return _shrink_rating(
            shots, saves, toi_seconds, league_save, self._config)

    def commit(
            self,
            player_id: int,
            as_of: datetime,
            shots_against: float,
            shots_saved: float,
            toi_seconds: float) -> None:
        """Append one appearance after its pre-match snapshot."""
        moment = self._require_forward_date(as_of)
        if shots_against <= 0:
            return
        ice_time = max(toi_seconds, 0.0)
        saved = max(shots_saved, 0.0)
        faced = shots_against
        self._players.setdefault(player_id, deque()).append(
            (moment, faced, saved, ice_time))
        self._league.append((moment, faced, saved))
        self._league_shots += faced
        self._league_saves += saved

    def _require_forward_date(self, as_of: datetime) -> datetime:
        # Ogon kolejki jest najnowszy; cofnięta data psuje prior ligowy.
        moment = _as_datetime(as_of)
        if self._last_date is not None and moment < self._last_date:
            raise ValueError(
                "Hockey ratings require chronological game dates. "
                f"Got {moment} after {self._last_date}.")
        self._last_date = moment
        return moment

    def _evict(self, player_id: int, cutoff: datetime) -> None:
        while self._league and self._league[0][0] <= cutoff:
            _when, shots, saves = self._league.popleft()
            self._league_shots -= shots
            self._league_saves -= saves
        appearances = self._players.get(player_id)
        if appearances is None:
            return
        while appearances and appearances[0][0] <= cutoff:
            appearances.popleft()

    def _league_before(self, moment: datetime) -> tuple[float, float]:
        # Suma bieżąca obejmuje już commity; zdejmujemy tylko suffix
        # z tym samym albo późniejszym stemplem (ta sama kolejka).
        shots = self._league_shots
        saves = self._league_saves
        for when, faced, saved in reversed(self._league):
            if when < moment:
                break
            shots -= faced
            saves -= saved
        return shots, saves

    def _player_before(
            self,
            player_id: int,
            cutoff: datetime,
            moment: datetime) -> tuple[float, float, float]:
        shots = 0.0
        saves = 0.0
        toi_seconds = 0.0
        for when, faced, saved, ice_time in self._players.get(
                player_id, ()):
            if when <= cutoff or when >= moment:
                continue
            shots += faced
            saves += saved
            toi_seconds += ice_time
        return shots, saves, toi_seconds


def build_goalie_ratings(
        appearances: pd.DataFrame,
        config: GoalieRatingsConfig | None = None) -> pd.DataFrame:
    """Return pre-match save% and GSAA/60 for each appearance.

    Rows that share ``game_date`` are snapshotted before any of them
    is committed, so a slate cannot leak into itself. ``toi_seconds``
    is ice time already parsed from ``MM:SS``.
    """
    settings = config or GoalieRatingsConfig()
    prepared = _prepare_appearances(appearances)
    if prepared.empty:
        return _empty_goalie_frame(prepared)
    state = GoalieRatingState(settings)
    rows: list[dict[str, object]] = []
    for game_date, group in prepared.groupby("game_date", sort=False):
        del game_date
        rows.extend(_snapshot_goalies(state, group))
        for _, row in group.iterrows():
            _commit_appearance(state, row)
    return pd.DataFrame(rows)


def _prepare_appearances(appearances: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column for column in GOALIE_APPEARANCE_COLUMNS
        if column not in appearances.columns]
    if missing:
        raise KeyError(
            f"Missing goalie appearance columns: {missing}")
    ready = appearances.loc[
        appearances["game_date"].notna()
        & appearances["player_id"].notna()].copy()
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    return ready.sort_values(
        ["game_date", "match_id", "player_id"]).reset_index(drop=True)


def _empty_goalie_frame(prepared: pd.DataFrame) -> pd.DataFrame:
    frame = prepared.copy()
    for column in GOALIE_RATING_COLUMNS:
        frame[column] = pd.Series(dtype="float64")
    return frame


def _snapshot_goalies(
        state: GoalieRatingState,
        group: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for _, row in group.iterrows():
        rating = state.snapshot(int(row["player_id"]), row["game_date"])
        rows.append({
            "match_id": int(row["match_id"]),
            "player_id": int(row["player_id"]),
            "team_id": int(row["team_id"]),
            "game_date": row["game_date"],
            "shots_against": row["shots_against"],
            "shots_saved": row["shots_saved"],
            "toi_seconds": row["toi_seconds"],
            "goalie_save_pct": rating.save_pct,
            "goalie_gsaa_per_60": rating.gsaa_per_60,
            "goalie_shots": rating.shots
        })
    return rows


def _commit_appearance(state: GoalieRatingState, row: pd.Series) -> None:
    shots = _optional_float(row["shots_against"])
    saves = _optional_float(row["shots_saved"])
    if shots is None or saves is None or shots <= 0:
        return
    toi_seconds = _optional_float(row["toi_seconds"])
    state.commit(
        int(row["player_id"]),
        row["game_date"],
        shots,
        saves,
        0.0 if toi_seconds is None else toi_seconds)


def _shrink_rating(
        shots: float,
        saves: float,
        toi_seconds: float,
        league_save: float,
        config: GoalieRatingsConfig) -> GoalieRating:
    prior = config.prior_shots
    shrunk = (saves + prior * league_save) / (shots + prior)
    gsaa = saves - shots * league_save
    return GoalieRating(
        save_pct=_clamp_rate(shrunk),
        gsaa_per_60=_per_sixty(gsaa, toi_seconds),
        shots=shots)


def _per_sixty(gsaa: float, toi_seconds: float) -> float:
    """Scale a window of goals saved above average to 60 minutes."""
    # Bez czasu na lodzie stawka na 60 minut nie jest określona.
    minutes = toi_seconds / 60.0
    if minutes <= 0:
        return 0.0
    return gsaa * 60.0 / minutes


def _rate(saves: float, shots: float, fallback: float) -> float:
    if shots <= 0:
        return _clamp_rate(fallback)
    return _clamp_rate(saves / shots)


def _clamp_rate(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _as_datetime(value: object) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
