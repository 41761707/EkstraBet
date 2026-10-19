"""Pre-match NHL schedule, fatigue and travel features."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

import pandas as pd

logger = logging.getLogger(__name__)

# Naiwny game_date w matches jest czasem lokalnym Polski.
STORED_GAME_DATE_TIMEZONE = "Europe/Warsaw"
EARTH_RADIUS_KM = 6371.0
GAMES_WINDOW_4_DAYS = 4
GAMES_WINDOW_7_DAYS = 7
COMPLETED_RESULTS = frozenset({"1", "X", "2"})

_BASE_FEATURES = [
    "rest_days",
    "is_b2b",
    "is_b2b_road",
    "games_last_4_days",
    "games_last_7_days",
    "series_index",
    "travel_km",
    "tz_shift_hours"]

_MATCH_COLUMNS = [
    "match_id",
    "home_team",
    "away_team",
    "game_date"]

_ARENA_COLUMNS = [
    "team_id",
    "latitude",
    "longitude",
    "timezone"]


def _schedule_columns() -> list[str]:
    columns: list[str] = []
    for name in _BASE_FEATURES:
        columns.append(f"home_{name}")
        columns.append(f"away_{name}")
        columns.append(f"{name}_diff")
    return columns


SCHEDULE_FEATURE_COLUMNS = _schedule_columns()
_OUTPUT_COLUMNS = ["match_id", *SCHEDULE_FEATURE_COLUMNS]


@dataclass(frozen=True)
class _Venue:
    latitude: float | None
    longitude: float | None
    timezone_name: str | None


@dataclass(frozen=True)
class _PriorGame:
    local_date: date
    latitude: float | None
    longitude: float | None
    offset_hours: float
    is_home: bool
    season: int | None
    series_index: int


@dataclass
class _TeamHistory:
    prior: _PriorGame | None = None
    local_dates: list[date] = field(default_factory=list)


@dataclass
class _MatchRow:
    position: int
    match_id: int
    home_team: int
    away_team: int
    instant: datetime
    local_date: date
    offset_hours: float
    latitude: float | None
    longitude: float | None
    season: int | None
    played: bool
    features: dict[str, float] = field(default_factory=dict)


def build_schedule_features(
        matches: pd.DataFrame,
        arenas: pd.DataFrame) -> pd.DataFrame:
    """Return one pre-match schedule row for every input match.

    Naive ``game_date`` values are read as Europe/Warsaw, which is how
    kickoffs are stored. Rest, back-to-backs and game counts then use
    the home arena's local calendar date. Only strictly earlier
    completed matches are history, so a later row cannot leak backward.

    ``rest_days`` is the local-date gap and is 0 when the team has no
    completed prior game. ``is_b2b`` is 1 when that gap is exactly one
    day. ``is_b2b_road`` is that flag for the away side of this match.
    ``games_last_4_days`` and ``games_last_7_days`` include the match
    itself. ``series_index`` is the 1-based game inside the current
    home stand or road trip and resets when the venue side or the
    season changes. ``travel_km`` is the haversine between the previous
    game's arena and this one. ``tz_shift_hours`` is the current UTC
    offset minus the previous one, so eastward travel is positive.
    Diff columns are home minus away.
    """
    _require_columns(matches, _MATCH_COLUMNS, "match")
    _require_columns(arenas, _ARENA_COLUMNS, "arena")
    if matches.empty:
        return _empty_schedule_frame()
    rows = _match_rows(matches, arenas)
    _apply_history(rows)
    return _assemble(rows)


def _require_columns(
        frame: pd.DataFrame,
        columns: list[str],
        kind: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise KeyError(f"Missing {kind} columns: {missing}")


def _empty_schedule_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=_OUTPUT_COLUMNS)


def _match_rows(
        matches: pd.DataFrame,
        arenas: pd.DataFrame) -> list[_MatchRow]:
    venues = _venue_by_team(arenas)
    has_result = "result" in matches.columns
    has_season = "season" in matches.columns
    missing_timezones: set[int] = set()
    unknown_timezones: set[str] = set()
    rows = [
        _match_row(
            position,
            record,
            venues,
            has_result,
            has_season,
            missing_timezones,
            unknown_timezones)
        for position, record in enumerate(matches.itertuples(index=False))]
    _warn_missing_timezones(missing_timezones, unknown_timezones)
    rows.sort(key=lambda item: (item.instant, item.match_id))
    return rows


def _venue_by_team(arenas: pd.DataFrame) -> dict[int, _Venue]:
    venues: dict[int, _Venue] = {}
    for record in arenas.itertuples(index=False):
        if pd.isna(record.team_id):
            continue
        venues[int(record.team_id)] = _Venue(
            _optional_float(record.latitude),
            _optional_float(record.longitude),
            _optional_text(record.timezone))
    return venues


def _match_row(
        position: int,
        record: object,
        venues: dict[int, _Venue],
        has_result: bool,
        has_season: bool,
        missing_timezones: set[int],
        unknown_timezones: set[str]) -> _MatchRow:
    match_id = _required_int(getattr(record, "match_id"), "match_id")
    home_team = _required_int(getattr(record, "home_team"), "home_team")
    venue = venues.get(home_team)
    zone = _arena_zone(
        venue, home_team, missing_timezones, unknown_timezones)
    instant = _as_instant(getattr(record, "game_date"), match_id)
    local_date, offset_hours = _local_clock(instant, zone)
    season = None
    if has_season:
        season = _optional_season(getattr(record, "season"))
    return _MatchRow(
        position=position,
        match_id=match_id,
        home_team=home_team,
        away_team=_required_int(getattr(record, "away_team"), "away_team"),
        instant=instant,
        local_date=local_date,
        offset_hours=offset_hours,
        latitude=None if venue is None else venue.latitude,
        longitude=None if venue is None else venue.longitude,
        season=season,
        played=_is_completed(record, has_result))


def _arena_zone(
        venue: _Venue | None,
        home_team: int,
        missing_timezones: set[int],
        unknown_timezones: set[str]) -> ZoneInfo:
    if venue is None or venue.timezone_name is None:
        missing_timezones.add(home_team)
        return ZoneInfo(STORED_GAME_DATE_TIMEZONE)
    try:
        return ZoneInfo(venue.timezone_name)
    except ZoneInfoNotFoundError:
        unknown_timezones.add(venue.timezone_name)
        missing_timezones.add(home_team)
        return ZoneInfo(STORED_GAME_DATE_TIMEZONE)


def _warn_missing_timezones(
        missing_timezones: set[int],
        unknown_timezones: set[str]) -> None:
    for team_id in sorted(missing_timezones):
        logger.warning(
            "Arena timezone missing for team_id=%s; "
            "schedule dates stay on the stored clock",
            team_id)
    for timezone_name in sorted(unknown_timezones):
        logger.warning("Unknown arena timezone %s", timezone_name)


def _as_instant(value: object, match_id: int) -> datetime:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError(f"Match {match_id} is missing game_date")
    if stamp.tzinfo is None:
        # Luka DST: przesuwamy. Nakładanie: zostawiamy czas letni.
        stamp = stamp.tz_localize(
            STORED_GAME_DATE_TIMEZONE,
            ambiguous=True,
            nonexistent="shift_forward")
    return stamp.to_pydatetime()


def _local_clock(instant: datetime, zone: ZoneInfo) -> tuple[date, float]:
    local = instant.astimezone(zone)
    offset = local.utcoffset()
    if offset is None:
        return local.date(), 0.0
    return local.date(), offset.total_seconds() / 3600.0


def _is_completed(record: object, has_result: bool) -> bool:
    if not has_result:
        return True
    result = getattr(record, "result")
    if result is None or pd.isna(result):
        return False
    return str(result) in COMPLETED_RESULTS


def _apply_history(rows: list[_MatchRow]) -> None:
    history: dict[int, _TeamHistory] = {}
    for row in rows:
        _apply_side(history, row, "home", row.home_team, True)
        _apply_side(history, row, "away", row.away_team, False)


def _apply_side(
        history: dict[int, _TeamHistory],
        row: _MatchRow,
        side: str,
        team_id: int,
        is_home: bool) -> None:
    state = history.setdefault(team_id, _TeamHistory())
    values = _side_features(state, row, is_home)
    for name, value in values.items():
        row.features[f"{side}_{name}"] = value
    if row.played:
        _commit(state, row, is_home, int(values["series_index"]))


def _side_features(
        state: _TeamHistory,
        row: _MatchRow,
        is_home: bool) -> dict[str, float]:
    rest_days = _rest_days(state.prior, row.local_date)
    is_b2b = 1.0 if rest_days == 1.0 else 0.0
    is_b2b_road = 1.0 if is_b2b == 1.0 and not is_home else 0.0
    return {
        "rest_days": rest_days,
        "is_b2b": is_b2b,
        "is_b2b_road": is_b2b_road,
        "games_last_4_days": _games_in_window(
            state.local_dates, row.local_date, GAMES_WINDOW_4_DAYS),
        "games_last_7_days": _games_in_window(
            state.local_dates, row.local_date, GAMES_WINDOW_7_DAYS),
        "series_index": _series_index(state.prior, is_home, row.season),
        "travel_km": _travel_km(state.prior, row),
        "tz_shift_hours": _timezone_shift(state.prior, row)}


def _commit(
        state: _TeamHistory,
        row: _MatchRow,
        is_home: bool,
        series_index: int) -> None:
    state.local_dates.append(row.local_date)
    state.prior = _PriorGame(
        local_date=row.local_date,
        latitude=row.latitude,
        longitude=row.longitude,
        offset_hours=row.offset_hours,
        is_home=is_home,
        season=row.season,
        series_index=series_index)


def _rest_days(prior: _PriorGame | None, local_date: date) -> float:
    if prior is None:
        return 0.0
    return float((local_date - prior.local_date).days)


def _series_index(
        prior: _PriorGame | None,
        is_home: bool,
        season: int | None) -> float:
    if prior is None:
        return 1.0
    # Seria urywa się przy zmianie strony meczu albo sezonu.
    same_stand = prior.is_home == is_home and prior.season == season
    if not same_stand:
        return 1.0
    return float(prior.series_index + 1)


def _games_in_window(
        local_dates: list[date],
        current: date,
        window_days: int) -> float:
    # Do okna wliczamy też dzisiejszy mecz, stąd „3 w 4” ma wartość 3.
    start = current - timedelta(days=window_days - 1)
    played = sum(
        1
        for played_on in local_dates
        if start <= played_on <= current)
    return float(played + 1)


def _travel_km(prior: _PriorGame | None, row: _MatchRow) -> float:
    if prior is None:
        return 0.0
    if prior.latitude is None or prior.longitude is None:
        return 0.0
    if row.latitude is None or row.longitude is None:
        return 0.0
    return _haversine_km(
        prior.latitude,
        prior.longitude,
        row.latitude,
        row.longitude)


def _timezone_shift(prior: _PriorGame | None, row: _MatchRow) -> float:
    if prior is None:
        return 0.0
    return row.offset_hours - prior.offset_hours


def _haversine_km(
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float) -> float:
    """Return the great-circle distance between two arenas."""
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    chord = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat_a) * math.cos(lat_b)
        * math.sin(delta_lon / 2.0) ** 2)
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(chord))


def _assemble(rows: list[_MatchRow]) -> pd.DataFrame:
    records: list[dict[str, float | int]] = []
    for row in sorted(rows, key=lambda item: item.position):
        record: dict[str, float | int] = {"match_id": row.match_id}
        record.update(_with_diffs(row.features))
        records.append(record)
    return pd.DataFrame(records, columns=_OUTPUT_COLUMNS)


def _with_diffs(features: dict[str, float]) -> dict[str, float]:
    completed = dict(features)
    for name in _BASE_FEATURES:
        completed[f"{name}_diff"] = (
            features[f"home_{name}"] - features[f"away_{name}"])
    return completed


def _required_int(value: object, column: str) -> int:
    if value is None or pd.isna(value):
        raise ValueError(f"Schedule rows require {column}")
    return int(value)


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return number


def _optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _optional_season(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)
