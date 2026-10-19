"""Current NHL roster grouped into lines, pairs and special sections."""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd

from backend.repositories import hockey_team_roster_repository as roster_repository
from backend.repositories import team_repository
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from models.pipeline.data.hockey_history_repository import parse_toi_seconds
from models.pipeline.features.hockey.line_slots import slot_for_labels

_GROUP_ORDER = (
    "F1",
    "F2",
    "F3",
    "F4",
    "D1",
    "D2",
    "D3",
    "G",
    "injured",
    "outside")
_LINE_GROUPS = frozenset({
    "F1",
    "F2",
    "F3",
    "F4",
    "D1",
    "D2",
    "D3"})
_FORWARD_POSITIONS = frozenset({"LW", "C", "RW"})
_GOALIE_POSITION = "G"
_GOALIE_DEPTH = frozenset({1, 2})
_POWER_PLAY_UNITS = frozenset({1, 2})
_POSITION_ORDER = {"LW": 0, "C": 1, "RW": 2, "D": 3, "G": 4}
_SECONDS_PER_HOUR = 3600
_SEASON_WINDOW = "season"
_RECENT_WINDOW_SIZES = (
    ("last_5", 5),
    ("last_10", 10))


class HockeyRosterUnavailableError(Exception):
    """Raised when a roster is requested for a non-hockey team."""


def get_hockey_team_roster(
        team_id: int,
        season_id: int | None = None) -> dict[str, Any] | None:
    """Return the roster payload, or None when the team does not exist."""
    team_frame = team_repository.fetch_team_by_id(team_id)
    if team_frame.empty:
        return None
    team = team_frame.iloc[0]
    sport_raw = team["sport_id"]
    if pd.isna(sport_raw) or int(sport_raw) != HOCKEY_SPORT_ID:
        raise HockeyRosterUnavailableError(
            "Roster is available only for hockey teams")
    stats = _empty_stats()
    if season_id is not None:
        stats = roster_repository.fetch_season_player_stats(
            team_id,
            season_id)
    return build_hockey_team_roster(
        team_id,
        _text(team["name"]),
        roster_repository.fetch_current_roster(team_id),
        roster_repository.fetch_last_match_roster(team_id),
        stats)


def build_hockey_team_roster(
        team_id: int,
        team_name: str,
        roster: pd.DataFrame,
        last_match: pd.DataFrame,
        season_stats: pd.DataFrame) -> dict[str, Any]:
    """Group the current roster and attach season counting stats.

    ``hockey_rosters.line`` is the only slot. The last match supplies
    the jersey number and whether the player dressed. An empty line
    stays outside, and an injured player stays in the injured group.
    """
    players = _player_records(
        roster,
        _match_rows(last_match),
        _aggregate_stats(season_stats))
    return {
        "team_id": team_id,
        "team_name": team_name,
        "goalkeepers": _by_position(players, "G"),
        "defensemen": _by_position(players, "D"),
        "forwards": _forwards(players),
        "injured_players": sum(
            1 for player in players if player["is_injured"]),
        "groups": _groups(players)
    }


def _player_records(
        roster: pd.DataFrame,
        match_rows: dict[int, dict[str, Any]],
        stats: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    if roster.empty:
        return []
    players = [
        _one_player(row, match_rows, stats)
        for row in roster.itertuples(index=False)]
    players.sort(key=_player_sort_key)
    return players


def _one_player(
        row: Any,
        match_rows: dict[int, dict[str, Any]],
        stats: dict[int, dict[str, Any]]) -> dict[str, Any]:
    player_id = int(row.player_id)
    match = match_rows.get(player_id)
    in_last_lineup = match is not None
    roster_position = _position(_optional_text(row.roster_position))
    match_position = None
    match_number = None
    if match is not None:
        match_position = _position(match["position"])
        match_number = match["number"]
    position = roster_position or match_position or _position(
        _optional_text(row.player_position)) or ""
    roster_line = _optional_int(row.roster_line)
    slot = _chosen_slot(position or None, roster_line)
    injured = _is_injured(row.is_injured)
    counting = stats.get(player_id, _zero_stats())
    return {
        "player_id": player_id,
        "first_name": _text(row.first_name),
        "last_name": _text(row.last_name),
        "common_name": _text(row.common_name),
        "country": _text(row.country_name),
        "position": position,
        "number": _jersey_number(row.roster_number, match_number),
        "line": _published_line(position, slot, roster_line),
        "pp_unit": _power_play_unit(getattr(row, "roster_pp", None)),
        "is_injured": injured,
        "injury_status": _optional_text(row.injury_status),
        "injury_note": _optional_text(row.injury_note),
        "in_last_lineup": in_last_lineup,
        "group_id": _group_id(injured, slot),
        **counting
    }


def _chosen_slot(
        position: str | None,
        roster_line: int | None) -> str | None:
    # Bramkarz bez linii 1 albo 2 nie wchodzi do grupy G.
    if position == _GOALIE_POSITION:
        if roster_line in _GOALIE_DEPTH:
            return "G"
        return None
    if roster_line is None:
        return None
    return slot_for_labels(position, roster_line)


def _group_id(is_injured: bool, slot: str | None) -> str:
    if is_injured:
        return "injured"
    if slot not in _GROUP_ORDER:
        return "outside"
    return slot


def _groups(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        group_id: [] for group_id in _GROUP_ORDER}
    for player in players:
        grouped[player["group_id"]].append(_public_player(player))
    return [
        {"group_id": group_id, "players": grouped[group_id]}
        for group_id in _GROUP_ORDER
        if grouped[group_id]]


def _by_position(
        players: list[dict[str, Any]],
        position: str) -> list[dict[str, Any]]:
    return [
        _public_player(player)
        for player in players
        if player["position"] == position]


def _forwards(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _public_player(player)
        for player in players
        if player["position"] in _FORWARD_POSITIONS
        or player["position"] not in {"G", "D"}]


def _public_player(player: dict[str, Any]) -> dict[str, Any]:
    published = dict(player)
    published.pop("group_id", None)
    return published


def _match_rows(last_match: pd.DataFrame) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    if last_match.empty:
        return rows
    for row in last_match.itertuples(index=False):
        rows[int(row.player_id)] = {
            "position": _optional_text(row.position),
            "number": _optional_int(row.number)
        }
    return rows


def _aggregate_stats(frame: pd.DataFrame) -> dict[int, dict[str, Any]]:
    if frame.empty:
        return {}
    return {
        player_id: _player_stat_block(rows)
        for player_id, rows in _rows_by_player(frame).items()}


def _rows_by_player(frame: pd.DataFrame) -> dict[int, list[Any]]:
    grouped: dict[int, list[Any]] = {}
    for row in frame.itertuples(index=False):
        grouped.setdefault(int(row.player_id), []).append(row)
    return grouped


def _player_stat_block(rows: list[Any]) -> dict[str, Any]:
    # Ostatnie N to występy tego zawodnika, nie mecze całego klubu.
    ordered = sorted(rows, key=_recency_key, reverse=True)
    season = _finish_stats(_sum_rows(ordered))
    windows = {_SEASON_WINDOW: season}
    for name, limit in _RECENT_WINDOW_SIZES:
        windows[name] = _finish_stats(_sum_rows(ordered[:limit]))
    return {
        **season,
        "stat_windows": windows
    }


def _recency_key(row: Any) -> tuple[datetime.date, int]:
    return (_played_on(row.game_date), _as_int(row.match_id))


def _played_on(value: object) -> datetime.date:
    if value is None or pd.isna(value):
        return datetime.date.min
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value)[:10])


def _sum_rows(rows: list[Any]) -> dict[str, Any]:
    bucket = _stat_bucket()
    for row in rows:
        _add_counting(bucket, row)
    return bucket


def _add_counting(bucket: dict[str, Any], row: Any) -> None:
    bucket["games"] += 1
    bucket["goals"] += _as_int(row.goals)
    bucket["assists"] += _as_int(row.assists)
    bucket["points"] += _as_int(row.points)
    bucket["sog"] += _as_int(row.sog)
    bucket["shots_against"] += _as_int(row.shots_against)
    bucket["shots_saved"] += _as_int(row.shots_saved)
    seconds = parse_toi_seconds(row.toi)
    if seconds is None:
        return
    bucket["toi_seconds"] += seconds
    bucket["toi_games"] += 1


def _finish_stats(bucket: dict[str, Any]) -> dict[str, Any]:
    save_percentage, goals_against_average = _goalie_rates(bucket)
    return {
        "games_played": bucket["games"],
        "goals": bucket["goals"],
        "assists": bucket["assists"],
        "points": bucket["points"],
        "shots_on_goal": bucket["sog"],
        "shots_per_game": _shots_per_game(
            bucket["sog"],
            bucket["games"]),
        "average_toi": _format_average_toi(
            bucket["toi_seconds"],
            bucket["toi_games"]),
        "save_percentage": save_percentage,
        "goals_against_average": goals_against_average
    }


def _goalie_rates(
        bucket: dict[str, Any]) -> tuple[float | None, float | None]:
    shots = bucket["shots_against"]
    if shots <= 0:
        return None, None
    saved = min(bucket["shots_saved"], shots)
    save_percentage = round(100.0 * saved / shots, 2)
    if bucket["toi_seconds"] <= 0:
        return save_percentage, None
    goals_against = shots - saved
    average = goals_against * _SECONDS_PER_HOUR / bucket["toi_seconds"]
    return save_percentage, round(average, 2)


def _shots_per_game(shots: int, games: int) -> float | None:
    if games <= 0:
        return None
    return round(shots / games, 2)


def _format_average_toi(total_seconds: int, games: int) -> str | None:
    if games <= 0:
        return None
    average = total_seconds // games
    minutes, seconds = divmod(average, 60)
    return f"{minutes}:{seconds:02d}"


def _stat_bucket() -> dict[str, Any]:
    return {
        "games": 0,
        "goals": 0,
        "assists": 0,
        "points": 0,
        "sog": 0,
        "shots_against": 0,
        "shots_saved": 0,
        "toi_seconds": 0,
        "toi_games": 0
    }


def _zero_stats() -> dict[str, Any]:
    return _player_stat_block([])


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "player_id",
        "goals",
        "assists",
        "points",
        "sog",
        "toi",
        "shots_against",
        "shots_saved",
        "match_id",
        "game_date"])


def _player_sort_key(player: dict[str, Any]) -> tuple[object, ...]:
    line = player["line"]
    return (
        line is None,
        0 if line is None else line,
        _POSITION_ORDER.get(player["position"], 9),
        player["common_name"].lower(),
        player["player_id"])


def _jersey_number(
        roster_number: object,
        match_number: int | None) -> int | None:
    number = _optional_int(roster_number)
    if number is not None:
        return number
    return match_number


def _power_play_unit(value: object) -> int | None:
    # 0 i NULL znaczą „poza przewagą”; tylko 1PP i 2PP idą na zakładki.
    unit = _optional_int(value)
    if unit not in _POWER_PLAY_UNITS:
        return None
    return unit


def _published_line(
        position: str,
        slot: str | None,
        roster_line: int | None) -> int | None:
    # Głębokość bramkarza jest w hockey_rosters.line, nie w meczu.
    if position == _GOALIE_POSITION and roster_line in _GOALIE_DEPTH:
        return roster_line
    return _line_from_slot(slot)


def _line_from_slot(slot: str | None) -> int | None:
    if slot not in _LINE_GROUPS or slot is None:
        return None
    return int(slot[1])


def _position(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().upper()


def _is_injured(value: object) -> bool:
    number = _optional_int(value)
    return number == 1


def _optional_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _as_int(value: object) -> int:
    number = _optional_int(value)
    if number is None:
        return 0
    return number
