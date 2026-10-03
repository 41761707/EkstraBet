"""Current NHL roster grouped into lines, pairs and special sections."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import hockey_team_roster_repository as roster_repository
from backend.repositories import team_repository
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from models.pipeline.data.hockey_history_repository import parse_toi_seconds
from models.pipeline.features.hockey.line_slots import LineSlotResolver
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
_POSITION_ORDER = {"LW": 0, "C": 1, "RW": 2, "D": 3, "G": 4}
_SECONDS_PER_HOUR = 3600


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

    A filled ``hockey_rosters.line`` names the slot, including for a
    player who missed the last game. An empty line uses
    ``LineSlotResolver`` on that match. Players with neither go to
    the outside group. Injured players stay in their own group.
    """
    players = _player_records(
        roster,
        _match_rows(last_match),
        _resolve_match_slots(last_match),
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
        match_slots: dict[int, str],
        stats: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    if roster.empty:
        return []
    players = [
        _one_player(row, match_rows, match_slots, stats)
        for row in roster.itertuples(index=False)]
    # Widok składu: linie 1-3 i pary 1-3 mają być pełne, gdy roster
    # ma dość zdrowych zawodników. Resolver modeli zostaje bez zmian.
    _fill_open_seats(players)
    players.sort(key=_player_sort_key)
    return players


def _one_player(
        row: Any,
        match_rows: dict[int, dict[str, Any]],
        match_slots: dict[int, str],
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
    slot = _chosen_slot(
        position or None,
        _optional_int(row.roster_line),
        match_slots.get(player_id))
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
        "line": _line_from_slot(slot),
        "is_injured": injured,
        "injury_status": _optional_text(row.injury_status),
        "injury_note": _optional_text(row.injury_note),
        "in_last_lineup": in_last_lineup,
        "group_id": _group_id(injured, slot),
        **counting
    }


def _fill_open_seats(players: list[dict[str, Any]]) -> None:
    _fill_seats(
        _healthy(players, _FORWARD_POSITIONS),
        ("F1", "F2", "F3"),
        3,
        ("F4", "outside"))
    _fill_seats(
        _healthy(players, frozenset({"D"})),
        ("D1", "D2", "D3"),
        2,
        ("outside",))


def _healthy(
        players: list[dict[str, Any]],
        positions: frozenset[str]) -> list[dict[str, Any]]:
    return [
        player for player in players
        if not player["is_injured"] and player["position"] in positions]


def _fill_seats(
        skaters: list[dict[str, Any]],
        must_slots: tuple[str, ...],
        capacity: int,
        donor_slots: tuple[str, ...]) -> None:
    counts = {slot: 0 for slot in must_slots}
    donors: dict[str, list[dict[str, Any]]] = {}
    for slot in donor_slots:
        donors[slot] = []
    for player in skaters:
        slot = player["group_id"]
        if slot in counts:
            counts[slot] += 1
            continue
        if slot in donors:
            donors[slot].append(player)
    for slot in donor_slots:
        donors[slot].sort(key=_donor_sort_key)
    for slot in must_slots:
        _fill_one_slot(slot, counts, capacity, donors, donor_slots)


def _fill_one_slot(
        slot: str,
        counts: dict[str, int],
        capacity: int,
        donors: dict[str, list[dict[str, Any]]],
        donor_slots: tuple[str, ...]) -> None:
    while counts[slot] < capacity:
        donor = _take_donor(donors, donor_slots)
        if donor is None:
            return
        donor["group_id"] = slot
        donor["line"] = _line_from_slot(slot)
        counts[slot] += 1


def _take_donor(
        donors: dict[str, list[dict[str, Any]]],
        donor_slots: tuple[str, ...]) -> dict[str, Any] | None:
    for slot in donor_slots:
        pool = donors[slot]
        if pool:
            return pool.pop(0)
    return None


def _donor_sort_key(player: dict[str, Any]) -> tuple[bool, int, int]:
    seconds = _average_toi_seconds(player["average_toi"])
    if seconds is None:
        return (True, 0, player["player_id"])
    return (False, -seconds, player["player_id"])


def _average_toi_seconds(value: object) -> int | None:
    text = _optional_text(value)
    if text is None or ":" not in text:
        return None
    minutes, seconds = text.split(":", 1)
    if not minutes.isdigit() or not seconds.isdigit():
        return None
    return int(minutes) * 60 + int(seconds)


def _chosen_slot(
        position: str | None,
        roster_line: int | None,
        match_slot: str | None) -> str | None:
    # Wpisana linia rosteru obowiązuje także poza ostatnim meczem.
    if roster_line is not None:
        labeled = slot_for_labels(position, roster_line)
        if labeled is not None:
            return labeled
    return match_slot


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


def _resolve_match_slots(last_match: pd.DataFrame) -> dict[int, str]:
    if last_match.empty:
        return {}
    prepared = pd.DataFrame({
        "match_id": last_match["match_id"],
        "player_id": last_match["player_id"],
        "team_id": last_match["team_id"],
        "position": last_match["position"],
        "line": last_match["line"],
        "toi_seconds": [
            parse_toi_seconds(value)
            for value in last_match["toi"].tolist()]
    })
    assigned = LineSlotResolver().assign(prepared)
    slots: dict[int, str] = {}
    for row in assigned.itertuples(index=False):
        if row.slot:
            slots[int(row.player_id)] = str(row.slot)
    return slots


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
    totals: dict[int, dict[str, Any]] = {}
    for row in frame.itertuples(index=False):
        player_id = int(row.player_id)
        bucket = totals.setdefault(player_id, _stat_bucket())
        _add_counting(bucket, row)
    return {
        player_id: _finish_stats(bucket)
        for player_id, bucket in totals.items()}


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
    return {
        "games_played": 0,
        "goals": 0,
        "assists": 0,
        "points": 0,
        "shots_on_goal": 0,
        "average_toi": None,
        "save_percentage": None,
        "goals_against_average": None
    }


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "player_id",
        "goals",
        "assists",
        "points",
        "sog",
        "toi",
        "shots_against",
        "shots_saved"])


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
