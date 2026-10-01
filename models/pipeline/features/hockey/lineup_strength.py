"""Match lineup strength and the baseline model's lambda correction.

Strength is expected points, shots and defence of the dressed
skaters, weighted by each slot's expected minutes. Ratios compare
that sum with the club's usual occupants of those slots. A
projected skater is dressed in full, and ``confidence`` shrinks only
the gap from the typical lineup: ``1 + confidence * (raw_ratio - 1)``.
A projection with no confidence is left out, so the ratio stays 1.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime

import pandas as pd

from models.pipeline.features.hockey.line_slots import DEFAULT_SLOT_MINUTES
from models.pipeline.features.hockey.line_slots import SKATER_SLOTS
from models.pipeline.features.hockey.line_slots import SLOT_CAPACITY
from models.pipeline.features.hockey.line_slots import LineSlotResolver
from models.pipeline.features.hockey.line_slots import SlotMinuteCarry
from models.pipeline.features.hockey.line_slots import carry_slot_minutes
from models.pipeline.features.hockey.line_slots import slot_for_labels
from models.pipeline.features.hockey.player_ratings import (
    DEFAULT_SLOT_OFF)
from models.pipeline.features.hockey.player_ratings import (
    DEFAULT_SLOT_SHOT)
from models.pipeline.features.hockey.player_ratings import (
    HockeyPlayerRatingState)


BASELINE_GAMES = 10
CONFIRMED_LINEUP_SOURCE = "CONFIRMED"
# def_rating jest ściągany do 0 i bywa ujemny. Przesunięcie o 1
# trzyma sumę dodatnią, a różnica około 0,5 nadal rusza stosunek.
# Duże przesunięcie spłaszczało ratio koło 1.
DEFENCE_RATING_OFFSET = 1.0
_DEFENCE_LEVEL_FLOOR = 0.05
TOP6_SLOTS = frozenset({"F1", "F2"})
BOTTOM6_SLOTS = frozenset({"F3", "F4"})
TOP4_DEFENCE_SLOTS = frozenset({"D1", "D2"})
# Ujemny def_rating potrafi dać ujemny stosunek, a potęga wtedy nie jest
# rzeczywista. Skrajne dodatnie wartości i tak nie powinny mnożyć λ.
_MIN_LINEUP_RATIO = 0.25
_MAX_LINEUP_RATIO = 4.0
_RATIO_BASELINE_FLOOR = 1e-9
LINEUP_RATIO_COLUMNS = [
    "match_id",
    "team_id",
    "lineup_off",
    "lineup_shots",
    "lineup_def",
    "lineup_off_ratio",
    "lineup_def_ratio",
    "top6_f_off",
    "bottom6_f_off",
    "top4_d_def",
    "missing_top6_f",
    "missing_top4_d"]
_ROSTER_FIELDS = [
    "match_id",
    "player_id",
    "team_id",
    "position",
    "line",
    "game_date",
    "season"]
_STAT_FIELDS = ["points", "sog", "plus_minus", "toi_seconds"]


@dataclass(frozen=True)
class ProbableLineupPlayer:
    """One skater or goalie in a probable or confirmed lineup.

    ``confidence`` is the share of the last five lineups. A goalie's
    ``start_probability`` is P(start) from GoalieStartModel and is
    separate from that share.
    """

    player_id: int
    position: str
    line: int | None
    pp_unit: int | None
    is_starting_goalie: int | None
    confidence: float | None
    source: str
    start_probability: float | None = None


@dataclass(frozen=True)
class ProbableLineup:
    """Club lineup for one match. History lives in the box score."""

    match_id: int
    team_id: int
    players: list[ProbableLineupPlayer]


@dataclass(frozen=True)
class _Skater:
    player_id: int
    slot: str
    off_rating: float
    shot_rating: float
    def_rating: float
    weight: float


def compute_lineup_strength(
        lineup: ProbableLineup,
        ratings: HockeyPlayerRatingState,
        slot_toi: dict[str, float],
        baseline_lineup: ProbableLineup,
        as_of: datetime,
        season: int) -> dict[str, float]:
    """Return lineup totals and ratios against the typical lineup.

    ``as_of`` and ``season`` are the match being scored.
    ``HockeyPlayerRatingState.snapshot`` needs both, and the date
    must not move backwards. Ratings are read before any ``update``
    for this match.
    """
    current = _skaters_from_lineup(lineup, ratings, as_of, season)
    baseline = _skaters_from_lineup(
        baseline_lineup, ratings, as_of, season)
    return _strength(current, baseline, slot_toi)


def apply_lineup_adjustment(
        base_lambda: float,
        off_ratio: float,
        opp_def_ratio: float,
        goalie_factor: float,
        beta_off: float,
        beta_def: float) -> float:
    """Scale one goal rate by lineup ratios and the opposing goalie.

    ``beta_off`` and ``beta_def`` of 0 drop the lineup terms, so the
    rate stays ``base_lambda * goalie_factor``. A stronger opponent
    defence (ratio above 1) lowers the rate.
    """
    if not math.isfinite(base_lambda) or base_lambda < 0.0:
        raise ValueError("base_lambda must be a finite non-negative rate")
    if not math.isfinite(goalie_factor) or goalie_factor < 0.0:
        raise ValueError(
            "goalie_factor must be a finite non-negative rate")
    if not math.isfinite(beta_off) or not math.isfinite(beta_def):
        raise ValueError("lineup betas must be finite")
    offence = _bounded_ratio(off_ratio)
    defence = _bounded_ratio(opp_def_ratio)
    return (
        base_lambda
        * (offence ** beta_off)
        * (defence ** (-beta_def))
        * goalie_factor)


@dataclass
class _LineupMemory:
    ratings: HockeyPlayerRatingState
    history: dict[int, deque[list[tuple[int, str]]]]
    carried: dict[tuple[int, str], float]
    last_moment: datetime | None
    slot_minutes: SlotMinuteCarry


_LineupReplay = tuple[list[dict[str, float | int]], _LineupMemory]


def prepare_lineup_memory(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int = BASELINE_GAMES) -> _LineupMemory:
    """Replay box scores once. Later matches reuse this state."""
    if baseline_games < 1:
        raise ValueError("baseline_games must be positive")
    return _memory_after_history(rosters, player_stats, baseline_games)


def ratios_for_lineups(
        home: ProbableLineup | None,
        away: ProbableLineup | None,
        rosters: pd.DataFrame | None,
        player_stats: pd.DataFrame | None,
        as_of: datetime,
        season: int,
        baseline_games: int = BASELINE_GAMES,
        *,
        memory: _LineupMemory | None = None) -> dict[str, float] | None:
    """Return the four strength ratios for one match, or None.

    A missing side stays at 1. Both missing means there is nothing
    to score. ``memory`` skips a second replay of the same history.
    ``as_of`` has to fall on or after the last box score.
    """
    if home is None and away is None:
        return None
    if memory is None:
        if rosters is None or player_stats is None:
            raise ValueError(
                "rosters and player_stats are required without memory")
        memory = prepare_lineup_memory(
            rosters, player_stats, baseline_games)
    moment = _plain_datetime(as_of)
    if memory.last_moment is not None and moment < memory.last_moment:
        raise ValueError(
            "Lineup ratios require a date on or after the last "
            f"box score. Got {moment} after {memory.last_moment}.")
    home_off, home_defence = _side_ratios(memory, home, moment, season)
    away_off, away_defence = _side_ratios(memory, away, moment, season)
    return {
        "home_off_ratio": home_off,
        "away_off_ratio": away_off,
        "home_def_ratio": home_defence,
        "away_def_ratio": away_defence}


def _side_ratios(
        memory: _LineupMemory,
        lineup: ProbableLineup | None,
        moment: datetime,
        season: int) -> tuple[float, float]:
    if lineup is None:
        return 1.0, 1.0
    strength = _strength_of_lineup(memory, lineup, moment, season)
    return (
        float(strength["lineup_off_ratio"]),
        float(strength["lineup_def_ratio"]))


def build_lineup_ratios(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int = BASELINE_GAMES) -> pd.DataFrame:
    """Return pre-match lineup features for every club appearance.

    The baseline fills each slot with the players who appeared there
    most often over the previous ``baseline_games`` matches. Each
    player is used once. The first match has no baseline, so its
    ratios are 1.
    """
    if baseline_games < 1:
        raise ValueError("baseline_games must be positive")
    if rosters.empty:
        return pd.DataFrame(columns=LINEUP_RATIO_COLUMNS)
    assigned = _assigned_appearances(rosters, player_stats)
    if assigned.empty:
        return pd.DataFrame(columns=LINEUP_RATIO_COLUMNS)
    slot_toi = LineSlotResolver().build_slot_toi(assigned)
    return _walk_lineup_ratios(assigned, slot_toi, baseline_games)


def _skaters_from_lineup(
        lineup: ProbableLineup,
        ratings: HockeyPlayerRatingState,
        as_of: datetime,
        season: int) -> list[_Skater]:
    skaters: list[_Skater] = []
    for player in lineup.players:
        slot = slot_for_labels(player.position, player.line)
        if slot not in SKATER_SLOTS:
            continue
        rating = ratings.snapshot(
            int(player.player_id),
            slot,
            season,
            as_of,
            record_date=False)
        skaters.append(_Skater(
            player_id=int(player.player_id),
            slot=slot,
            off_rating=rating.off_rating,
            shot_rating=rating.shot_rating,
            def_rating=rating.def_rating,
            weight=_player_weight(player)))
    return skaters


def _player_weight(player: ProbableLineupPlayer) -> float:
    # Protokół jest pewny. Projekcja bez confidence nie wchodzi w całości.
    if player.source == CONFIRMED_LINEUP_SOURCE:
        return 1.0
    if player.confidence is None:
        return 0.0
    try:
        confidence = float(player.confidence)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(confidence) or confidence <= 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _strength(
        current: list[_Skater],
        baseline: list[_Skater],
        slot_toi: dict[str, float]) -> dict[str, float]:
    dressed = _dressed(current)
    return {
        "lineup_off": _sum_rating(dressed, "off_rating", slot_toi, None),
        "lineup_shots": _sum_rating(
            dressed, "shot_rating", slot_toi, None),
        "lineup_def": _sum_rating(dressed, "def_rating", slot_toi, None),
        "lineup_off_ratio": _shrink_toward_typical(
            _divide(
                _sum_rating(dressed, "off_rating", slot_toi, None),
                _sum_rating(baseline, "off_rating", slot_toi, None)),
            current),
        "lineup_def_ratio": _shrink_toward_typical(
            _divide(
                _sum_defence_level(dressed, slot_toi),
                _sum_defence_level(baseline, slot_toi)),
            current),
        "top6_f_off": _sum_rating(
            dressed, "off_rating", slot_toi, TOP6_SLOTS),
        "bottom6_f_off": _sum_rating(
            dressed, "off_rating", slot_toi, BOTTOM6_SLOTS),
        "top4_d_def": _sum_rating(
            dressed, "def_rating", slot_toi, TOP4_DEFENCE_SLOTS),
        "missing_top6_f": _missing(current, baseline, TOP6_SLOTS),
        "missing_top4_d": _missing(
            current, baseline, TOP4_DEFENCE_SLOTS)}


def _dressed(skaters: list[_Skater]) -> list[_Skater]:
    # Pewność nie obcina poziomu. Obcina tylko odchyłkę w ratio.
    return [
        replace(skater, weight=1.0)
        for skater in skaters
        if skater.weight > 0.0]


def _shrink_toward_typical(raw_ratio: float, skaters: list[_Skater]) -> float:
    weights = [skater.weight for skater in skaters if skater.weight > 0.0]
    if not weights:
        return 1.0
    confidence = sum(weights) / len(weights)
    if confidence > 1.0:
        confidence = 1.0
    return 1.0 + confidence * (raw_ratio - 1.0)


def _sum_rating(
        skaters: list[_Skater],
        field_name: str,
        slot_toi: dict[str, float],
        slots: frozenset[str] | None) -> float:
    total = 0.0
    for skater in skaters:
        if slots is not None and skater.slot not in slots:
            continue
        minutes = _minutes(slot_toi, skater.slot)
        if minutes is None:
            continue
        total += skater.weight * getattr(skater, field_name) * minutes / 60.0
    return total


def _sum_defence_level(
        skaters: list[_Skater],
        slot_toi: dict[str, float]) -> float:
    total = 0.0
    for skater in skaters:
        minutes = _minutes(slot_toi, skater.slot)
        if minutes is None:
            continue
        level = skater.def_rating + DEFENCE_RATING_OFFSET
        if level < _DEFENCE_LEVEL_FLOOR:
            level = _DEFENCE_LEVEL_FLOOR
        total += skater.weight * level * minutes / 60.0
    return total


def _minutes(slot_toi: dict[str, float], slot: str) -> float | None:
    if slot not in slot_toi:
        return None
    try:
        minutes = float(slot_toi[slot])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(minutes) or minutes < 0.0:
        return None
    return minutes


def _divide(current: float, baseline: float) -> float:
    if not math.isfinite(current) or not math.isfinite(baseline):
        return 1.0
    if abs(baseline) < _RATIO_BASELINE_FLOOR:
        return 1.0
    return current / baseline


def _missing(
        current: list[_Skater],
        baseline: list[_Skater],
        slots: frozenset[str]) -> float:
    present = {
        skater.player_id
        for skater in current
        if skater.weight > 0.0}
    seen: set[int] = set()
    count = 0
    for skater in baseline:
        if skater.slot not in slots or skater.player_id in seen:
            continue
        seen.add(skater.player_id)
        if skater.player_id not in present:
            count += 1
    return float(count)


def _bounded_ratio(ratio: float) -> float:
    # Brak albo ujemny sygnał obrony nie może wywrócić potęgi.
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(value) or value <= 0.0:
        return 1.0
    if value < _MIN_LINEUP_RATIO:
        return _MIN_LINEUP_RATIO
    if value > _MAX_LINEUP_RATIO:
        return _MAX_LINEUP_RATIO
    return value


def _assigned_appearances(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column for column in _ROSTER_FIELDS
        if column not in rosters.columns]
    if missing:
        raise KeyError(f"Missing roster columns: {missing}")
    merged = rosters.loc[:, _ROSTER_FIELDS].merge(
        _stat_slice(player_stats),
        on=["match_id", "player_id", "team_id"],
        how="left")
    for column in _STAT_FIELDS:
        if column not in merged.columns:
            merged[column] = pd.NA
    return LineSlotResolver().assign(merged)


def _stat_slice(player_stats: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty:
        return pd.DataFrame(
            columns=["match_id", "player_id", "team_id", *_STAT_FIELDS])
    columns = [
        column for column in (
            ["match_id", "player_id", "team_id", *_STAT_FIELDS])
        if column in player_stats.columns]
    return player_stats.loc[:, columns]


def _walk_lineup_ratios(
        assigned: pd.DataFrame,
        slot_toi: pd.DataFrame,
        baseline_games: int) -> pd.DataFrame:
    rows, _memory = _replay_lineups(assigned, slot_toi, baseline_games)
    if not rows:
        return pd.DataFrame(columns=LINEUP_RATIO_COLUMNS)
    return pd.DataFrame(rows, columns=LINEUP_RATIO_COLUMNS)


def _memory_after_history(
        rosters: pd.DataFrame,
        player_stats: pd.DataFrame,
        baseline_games: int) -> _LineupMemory:
    if rosters.empty:
        return _empty_memory()
    assigned = _assigned_appearances(rosters, player_stats)
    if assigned.empty:
        return _empty_memory()
    slot_toi = LineSlotResolver().build_slot_toi(assigned)
    _rows, memory = _replay_lineups(assigned, slot_toi, baseline_games)
    return memory


def _empty_memory() -> _LineupMemory:
    return _LineupMemory(
        ratings=HockeyPlayerRatingState(),
        history={},
        carried={},
        last_moment=None,
        slot_minutes=SlotMinuteCarry.blank())


def _replay_lineups(
        assigned: pd.DataFrame,
        slot_toi: pd.DataFrame,
        baseline_games: int) -> _LineupReplay:
    prepared = assigned.loc[assigned["game_date"].notna()].copy()
    state = HockeyPlayerRatingState()
    history: dict[int, deque[list[tuple[int, str]]]] = {}
    carried: dict[tuple[int, str], float] = {}
    if prepared.empty:
        return [], _finished_memory(state, history, carried, None, prepared)
    prepared["game_date"] = pd.to_datetime(prepared["game_date"])
    prepared = prepared.sort_values(
        ["game_date", "match_id", "team_id", "player_id"])
    prematch = _prematch_toi(slot_toi)
    rows: list[dict[str, float | int]] = []
    last_moment: datetime | None = None
    for game_date, slate in prepared.groupby("game_date", sort=False):
        last_moment = _plain_datetime(game_date)
        rows.extend(_snapshot_slate(
            slate, state, history, prematch, carried, last_moment))
        for _match_id, match_rows in slate.groupby("match_id", sort=False):
            state.update(match_rows)
        _remember(history, slate, baseline_games)
        _carry_toi(carried, prematch, slate)
    return rows, _finished_memory(
        state, history, carried, last_moment, prepared)


def _finished_memory(
        state: HockeyPlayerRatingState,
        history: dict[int, deque[list[tuple[int, str]]]],
        carried: dict[tuple[int, str], float],
        last_moment: datetime | None,
        assigned: pd.DataFrame) -> _LineupMemory:
    # Predykcja bierze EWMA po ostatnim meczu, nie minuty sprzed niego.
    return _LineupMemory(
        state,
        history,
        carried,
        last_moment,
        carry_slot_minutes(assigned))


def projected_lineup_strength(
        memory: _LineupMemory,
        lineup: ProbableLineup,
        as_of: datetime,
        season: int) -> dict[str, float]:
    """Return full strength for a lineup scored on a replayed history."""
    return _strength_of_lineup(
        memory, lineup, _plain_datetime(as_of), int(season))


def typical_lineup_strength(
        memory: _LineupMemory,
        team_id: int,
        as_of: datetime,
        season: int) -> dict[str, float]:
    """Return the usual slot lineup. Ratios stay at 1.

    A club with no baseline occupants takes the prior of each slot.
    A date behind the learned cursor cannot be rewound, so that
    case also uses the slot prior.
    """
    moment = _plain_datetime(as_of)
    try:
        baseline = _baseline_skaters(
            memory.ratings,
            memory.history.get(int(team_id)),
            int(season),
            moment,
            record_date=False)
    except ValueError:
        baseline = []
    minutes = memory.slot_minutes.for_team(int(team_id), int(season))
    if not baseline:
        baseline = _prior_slot_skaters()
    return _strength(baseline, baseline, minutes)


def _prior_slot_skaters() -> list[_Skater]:
    skaters: list[_Skater] = []
    player_id = -1
    for slot in SKATER_SLOTS:
        for _seat in range(SLOT_CAPACITY[slot]):
            skaters.append(_Skater(
                player_id=player_id,
                slot=slot,
                off_rating=DEFAULT_SLOT_OFF[slot],
                shot_rating=DEFAULT_SLOT_SHOT[slot],
                def_rating=0.0,
                weight=1.0))
            player_id -= 1
    return skaters


def _strength_of_lineup(
        memory: _LineupMemory,
        lineup: ProbableLineup,
        moment: datetime,
        season: int) -> dict[str, float]:
    current = _skaters_from_lineup(
        lineup, memory.ratings, moment, season)
    baseline = _baseline_skaters(
        memory.ratings,
        memory.history.get(int(lineup.team_id)),
        season,
        moment,
        record_date=False)
    if not baseline:
        baseline = current
    minutes = memory.slot_minutes.for_team(int(lineup.team_id), season)
    return _strength(current, baseline, minutes)


def _snapshot_slate(
        slate: pd.DataFrame,
        state: HockeyPlayerRatingState,
        history: dict[int, deque[list[tuple[int, str]]]],
        prematch: dict[tuple[int, int, str], float],
        carried: dict[tuple[int, str], float],
        moment: datetime) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    grouped = slate.groupby(["match_id", "team_id"], sort=False)
    for (match_id, team_id), group in grouped:
        season = int(group["season"].iloc[0])
        club = int(team_id)
        current = _skaters_in_group(state, group, season, moment)
        baseline = _baseline_skaters(
            state, history.get(club), season, moment)
        if not baseline:
            baseline = current
        minutes = _toi_for_club(prematch, carried, int(match_id), club)
        strength = _strength(current, baseline, minutes)
        strength["match_id"] = int(match_id)
        strength["team_id"] = club
        rows.append(strength)
    return rows


def _skaters_in_group(
        state: HockeyPlayerRatingState,
        group: pd.DataFrame,
        season: int,
        moment: datetime) -> list[_Skater]:
    skaters: list[_Skater] = []
    for row in group.itertuples(index=False):
        slot = _played_slot(row.slot)
        if slot is None:
            continue
        rating = state.snapshot(int(row.player_id), slot, season, moment)
        skaters.append(_Skater(
            player_id=int(row.player_id),
            slot=slot,
            off_rating=rating.off_rating,
            shot_rating=rating.shot_rating,
            def_rating=rating.def_rating,
            weight=1.0))
    return skaters


def _baseline_skaters(
        state: HockeyPlayerRatingState,
        games: deque[list[tuple[int, str]]] | None,
        season: int,
        moment: datetime,
        *,
        record_date: bool = True) -> list[_Skater]:
    skaters: list[_Skater] = []
    for player_id, slot in _frequent_occupants(games):
        rating = state.snapshot(
            player_id,
            slot,
            season,
            moment,
            record_date=record_date)
        skaters.append(_Skater(
            player_id=player_id,
            slot=slot,
            off_rating=rating.off_rating,
            shot_rating=rating.shot_rating,
            def_rating=rating.def_rating,
            weight=1.0))
    return skaters


def _frequent_occupants(
        games: deque[list[tuple[int, str]]] | None
        ) -> list[tuple[int, str]]:
    """Fill each slot up to capacity from its own appearances.

    A player sits once, in the slot where he appeared most. Ties
    prefer the earlier slot name. The seat he does not take is
    filled by the next appearance in that slot.
    """
    if not games:
        return []
    counts: dict[tuple[int, str], int] = {}
    for played in games:
        for player_id, slot in played:
            if slot not in SLOT_CAPACITY:
                continue
            key = (player_id, slot)
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(
        counts,
        key=lambda item: (-counts[item], item[1], item[0]))
    used: set[int] = set()
    seated: dict[str, list[int]] = {slot: [] for slot in SKATER_SLOTS}
    for player_id, slot in ranked:
        if player_id in used:
            continue
        bucket = seated[slot]
        if len(bucket) >= SLOT_CAPACITY[slot]:
            continue
        used.add(player_id)
        bucket.append(player_id)
    chosen: list[tuple[int, str]] = []
    for slot in SKATER_SLOTS:
        for player_id in seated[slot]:
            chosen.append((player_id, slot))
    return chosen


def _remember(
        history: dict[int, deque[list[tuple[int, str]]]],
        slate: pd.DataFrame,
        baseline_games: int) -> None:
    grouped = slate.groupby(["match_id", "team_id"], sort=False)
    for (_match_id, team_id), group in grouped:
        played: list[tuple[int, str]] = []
        for row in group.itertuples(index=False):
            slot = _played_slot(row.slot)
            if slot is None:
                continue
            played.append((int(row.player_id), slot))
        club = int(team_id)
        bucket = history.get(club)
        if bucket is None:
            bucket = deque(maxlen=baseline_games)
            history[club] = bucket
        bucket.append(played)


def _prematch_toi(
        slot_toi: pd.DataFrame) -> dict[tuple[int, int, str], float]:
    """Index expected minutes that were known before each match."""
    indexed: dict[tuple[int, int, str], float] = {}
    if slot_toi.empty:
        return indexed
    for row in slot_toi.itertuples(index=False):
        slot = str(row.slot)
        if slot not in SKATER_SLOTS:
            continue
        minutes = _optional_minutes(row.slot_toi_minutes)
        if minutes is None:
            continue
        indexed[(int(row.match_id), int(row.team_id), slot)] = minutes
    return indexed


def _toi_for_club(
        prematch: dict[tuple[int, int, str], float],
        carried: dict[tuple[int, str], float],
        match_id: int,
        team_id: int) -> dict[str, float]:
    # Pusty slot nie ma wiersza, więc bierzemy poprzednie oczekiwanie.
    minutes: dict[str, float] = {}
    for slot in SKATER_SLOTS:
        key = (match_id, team_id, slot)
        if key in prematch:
            minutes[slot] = prematch[key]
        elif (team_id, slot) in carried:
            minutes[slot] = carried[(team_id, slot)]
        else:
            minutes[slot] = DEFAULT_SLOT_MINUTES[slot]
    return minutes


def _carry_toi(
        carried: dict[tuple[int, str], float],
        prematch: dict[tuple[int, int, str], float],
        slate: pd.DataFrame) -> None:
    grouped = slate.groupby(["match_id", "team_id"], sort=False)
    for (match_id, team_id), _group in grouped:
        club = int(team_id)
        for slot in SKATER_SLOTS:
            key = (int(match_id), club, slot)
            if key in prematch:
                carried[(club, slot)] = prematch[key]


def _played_slot(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    slot = str(value)
    if slot not in SKATER_SLOTS:
        return None
    return slot


def _optional_minutes(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(minutes) or minutes < 0.0:
        return None
    return minutes


def _plain_datetime(value: object) -> datetime:
    parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
