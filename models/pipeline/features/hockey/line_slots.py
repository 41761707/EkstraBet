"""Line slots and as-of expected ice time for NHL skaters.

A slot is the forward line (F1-F4), defence pair (D1-D3) or the
goalie (G). The roster line and position name the slot. Time on ice
only places a skater whose line does not. Position labels are trusted:
the 4th-line correction is a manual data fix and is not reapplied here.

``slot_toi`` is the previous season's league average minutes in that
slot, then an EWMA of how this team actually shares the minutes.
The value on a row is the expectation before that game.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

import pandas as pd

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.early_season import early_season_alpha


FORWARD_POSITIONS = frozenset({"C", "LW", "RW"})
DEFENSE_POSITIONS = frozenset({"D"})
GOALIE_POSITION = "G"
FORWARD_SLOTS = ("F1", "F2", "F3", "F4")
DEFENSE_SLOTS = ("D1", "D2", "D3")
GOALIE_SLOT = "G"
SKATER_SLOTS = FORWARD_SLOTS + DEFENSE_SLOTS
ALL_SLOTS = SKATER_SLOTS + (GOALIE_SLOT,)
# Trzech napastników na linię, para obrońców, jeden bramkarz.
SLOT_CAPACITY = {
    "F1": 3,
    "F2": 3,
    "F3": 3,
    "F4": 3,
    "D1": 2,
    "D2": 2,
    "D3": 2
}
# Minuty z opisu linii w sezonie 2025/26, zanim zbierzemy własną średnią.
DEFAULT_SLOT_MINUTES = {
    "F1": 19.7,
    "F2": 17.5,
    "F3": 15.0,
    "F4": 10.7,
    "D1": 22.5,
    "D2": 20.1,
    "D3": 15.6,
    "G": 60.0
}
SLOT_TOI_ALPHA = 0.1
ROSTER_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "position",
    "line",
    "toi_seconds"
]
SLOT_TOI_COLUMNS = [
    "match_id",
    "team_id",
    "season",
    "game_date",
    "slot",
    "slot_toi_minutes"
]
_FORWARD_LINES = frozenset({1, 2, 3, 4})
_DEFENSE_LINES = frozenset({1, 2, 3})
_GROUP_COLUMNS = [
    "game_date",
    "match_id",
    "team_id",
    "season",
    "slot"
]


def _default_minutes() -> dict[str, float]:
    return dict(DEFAULT_SLOT_MINUTES)


@dataclass(frozen=True)
class SlotToiConfig:
    """EWMA of team ice time, anchored on last season's league mean."""

    alpha: float = SLOT_TOI_ALPHA
    early_season: EarlySeasonConfig = field(
        default_factory=EarlySeasonConfig)
    initial_minutes: dict[str, float] = field(
        default_factory=_default_minutes)


class LineSlotResolver:
    """Assign F1-F4, D1-D3 and G, then expected minutes per team."""

    def __init__(self, config: SlotToiConfig | None = None) -> None:
        self._config = config or SlotToiConfig()
        if self._config.alpha <= 0 or self._config.alpha > 1:
            raise ValueError("slot_toi alpha must be in (0, 1]")

    def assign(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Return ``rows`` with a ``slot`` column.

        Forwards on line ``n`` become ``Fn``. Defencemen on line ``n``
        become ``Dn``. Every goalie is ``G``. A skater with no usable
        line is placed by time on ice into the first open slot of his
        position group. Unknown positions stay unassigned.
        """
        return _assign_slots(rows)

    def build_slot_toi(self, assigned: pd.DataFrame) -> pd.DataFrame:
        """Return pre-match expected minutes for each team slot.

        Rows that share ``game_date`` are read before any of them
        updates the team EWMA. A new season restarts from the league
        average of the season just finished.
        """
        return _build_slot_toi(assigned, self._config)


def _assign_slots(rows: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column for column in ROSTER_COLUMNS
        if column not in rows.columns]
    if missing:
        raise KeyError(f"Missing roster columns: {missing}")
    prepared = rows.reset_index(drop=True)
    slots: list[str | None] = [None] * len(prepared)
    if prepared.empty:
        prepared["slot"] = pd.Series(dtype="object")
        return prepared
    grouped = prepared.groupby(["match_id", "team_id"], sort=False)
    for _, group in grouped:
        for index, slot in _assign_group(group):
            slots[index] = slot
    prepared["slot"] = slots
    return prepared


def _assign_group(group: pd.DataFrame) -> list[tuple[int, str | None]]:
    counts = {slot: 0 for slot in SKATER_SLOTS}
    labeled: list[tuple[int, str | None]] = []
    open_forwards: list[tuple[int, int, float | None]] = []
    open_defense: list[tuple[int, int, float | None]] = []
    for row in group.itertuples(index=True):
        position = _position_code(row.position)
        slot = _slot_from_labels(position, row.line)
        if slot == GOALIE_SLOT or slot in counts:
            labeled.append((row.Index, slot))
            if slot in counts:
                counts[slot] += 1
            continue
        pending = (
            row.Index,
            int(row.player_id),
            _optional_float(row.toi_seconds))
        if position in FORWARD_POSITIONS:
            open_forwards.append(pending)
        elif position in DEFENSE_POSITIONS:
            open_defense.append(pending)
        else:
            labeled.append((row.Index, None))
    labeled.extend(_fill_by_toi(
        open_forwards, counts, FORWARD_SLOTS, "F4"))
    labeled.extend(_fill_by_toi(
        open_defense, counts, DEFENSE_SLOTS, "D3"))
    return labeled


def _slot_from_labels(position: str | None, line: object) -> str | None:
    if position == GOALIE_POSITION:
        return GOALIE_SLOT
    number = _line_number(line)
    if position in FORWARD_POSITIONS and number in _FORWARD_LINES:
        return f"F{number}"
    if position in DEFENSE_POSITIONS and number in _DEFENSE_LINES:
        return f"D{number}"
    return None


def _fill_by_toi(
        pending: list[tuple[int, int, float | None]],
        counts: dict[str, int],
        slots: tuple[str, ...],
        overflow: str) -> list[tuple[int, str]]:
    # Więcej lodu wyżej: brak linii nie może wyprzedzić opisanej linii.
    pending.sort(key=lambda item: _toi_sort_key(item[2], item[1]))
    assigned: list[tuple[int, str]] = []
    for index, _player_id, _toi in pending:
        slot = _first_open_slot(counts, slots, overflow)
        counts[slot] += 1
        assigned.append((index, slot))
    return assigned


def _first_open_slot(
        counts: dict[str, int],
        slots: tuple[str, ...],
        overflow: str) -> str:
    for slot in slots:
        if counts[slot] < SLOT_CAPACITY[slot]:
            return slot
    return overflow


def _toi_sort_key(
        toi_seconds: float | None,
        player_id: int) -> tuple[bool, float, int]:
    if toi_seconds is None:
        return (True, 0.0, player_id)
    return (False, -toi_seconds, player_id)


def _build_slot_toi(
        assigned: pd.DataFrame,
        config: SlotToiConfig) -> pd.DataFrame:
    observed = _observed_slot_minutes(assigned)
    if observed.empty:
        return _empty_slot_toi(observed)
    state = _SlotToiState(config)
    emitted: list[dict[str, object]] = []
    for game_date, slate in observed.groupby("game_date", sort=False):
        del game_date
        state.roll_season(_slate_season(slate))
        emitted.extend(state.snapshot_slate(slate))
        state.update_slate(slate)
    return pd.DataFrame(emitted)


def _observed_slot_minutes(assigned: pd.DataFrame) -> pd.DataFrame:
    required = ROSTER_COLUMNS + ["game_date", "season", "slot"]
    missing = [
        column for column in required
        if column not in assigned.columns]
    if missing:
        raise KeyError(f"Missing slot-toi columns: {missing}")
    working = assigned.loc[assigned["slot"].notna(), required].copy()
    if working.empty:
        return working.iloc[0:0]
    working["game_date"] = pd.to_datetime(working["game_date"])
    working["toi_minutes"] = [
        _minutes(value) for value in working["toi_seconds"].tolist()]
    grouped = working.groupby(
        _GROUP_COLUMNS, sort=False, as_index=False)["toi_minutes"].mean()
    return grouped.sort_values(
        ["game_date", "match_id", "team_id", "slot"]
    ).reset_index(drop=True)


def _empty_slot_toi(observed: pd.DataFrame) -> pd.DataFrame:
    frame = observed.copy()
    frame["slot_toi_minutes"] = pd.Series(dtype="float64")
    columns = [
        column for column in SLOT_TOI_COLUMNS
        if column in frame.columns or column == "slot_toi_minutes"]
    return frame.loc[:, columns]


class _SlotToiState:
    """League anchor plus one EWMA per team and slot."""

    def __init__(self, config: SlotToiConfig) -> None:
        self._config = config
        self._prior = dict(config.initial_minutes)
        for slot, minutes in DEFAULT_SLOT_MINUTES.items():
            self._prior.setdefault(slot, minutes)
        self._team_minutes: dict[tuple[int, str], float] = {}
        self._team_games: dict[int, int] = {}
        self._season_sum: dict[str, float] = {}
        self._season_count: dict[str, int] = {}
        self._season: int | None = None
        self._last_date: datetime | None = None

    def roll_season(self, season: int) -> None:
        if self._season is None:
            self._season = season
            return
        if self._season == season:
            return
        # Nowy sezon startuje od średniej ligi, nie od EWMA drużyny.
        self._freeze_league_prior()
        self._season = season
        self._team_games.clear()
        self._team_minutes.clear()

    def snapshot_slate(self, slate: pd.DataFrame) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in slate.itertuples(index=False):
            moment = self._require_forward_date(row.game_date)
            slot = str(row.slot)
            team_id = int(row.team_id)
            rows.append({
                "match_id": int(row.match_id),
                "team_id": team_id,
                "season": int(row.season),
                "game_date": moment,
                "slot": slot,
                "slot_toi_minutes": self._expectation(team_id, slot)
            })
        return rows

    def update_slate(self, slate: pd.DataFrame) -> None:
        teams_seen: set[int] = set()
        for row in slate.itertuples(index=False):
            team_id = int(row.team_id)
            teams_seen.add(team_id)
            observed = _optional_float(row.toi_minutes)
            if observed is None:
                continue
            slot = str(row.slot)
            alpha = early_season_alpha(
                self._config.alpha,
                self._team_games.get(team_id, 0),
                self._config.early_season)
            current = self._expectation(team_id, slot)
            self._team_minutes[(team_id, slot)] = (
                alpha * observed + (1.0 - alpha) * current)
            self._season_sum[slot] = (
                self._season_sum.get(slot, 0.0) + observed)
            self._season_count[slot] = self._season_count.get(slot, 0) + 1
        for team_id in teams_seen:
            self._team_games[team_id] = (
                self._team_games.get(team_id, 0) + 1)

    def _expectation(self, team_id: int, slot: str) -> float:
        stored = self._team_minutes.get((team_id, slot))
        if stored is None:
            return self._prior.get(slot, DEFAULT_SLOT_MINUTES[GOALIE_SLOT])
        return stored

    def _freeze_league_prior(self) -> None:
        for slot, count in self._season_count.items():
            if count > 0:
                self._prior[slot] = self._season_sum[slot] / count
        self._season_sum.clear()
        self._season_count.clear()

    def _require_forward_date(self, game_date: object) -> datetime:
        moment = _as_datetime(game_date)
        if self._last_date is not None and moment < self._last_date:
            raise ValueError(
                "Slot toi requires chronological game dates. "
                f"Got {moment} after {self._last_date}.")
        self._last_date = moment
        return moment


def _slate_season(slate: pd.DataFrame) -> int:
    seasons = {int(value) for value in slate["season"].tolist()}
    if len(seasons) != 1:
        raise ValueError(
            "One game date cannot mix hockey seasons.")
    return seasons.pop()


def _position_code(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text == "":
        return None
    return text


def _line_number(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _minutes(value: object) -> float:
    seconds = _optional_float(value)
    if seconds is None or seconds < 0:
        return float("nan")
    return seconds / 60.0


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _as_datetime(value: object) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
