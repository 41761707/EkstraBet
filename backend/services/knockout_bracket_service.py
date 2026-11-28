"""Build the knockout bracket response for one league season."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from backend.repositories import knockout_repository
from backend.repositories import league_repository
from backend.services.knockout_profiles import ByeProfile
from backend.services.knockout_profiles import SeededTeam
from backend.services.knockout_profiles import active_bye_profile
from backend.services.knockout_ties import BracketTie
from backend.services.knockout_ties import TieMatch
from backend.services.knockout_ties import group_ties
from backend.services.knockout_ties import tie_with_score
from backend.services.knockout_tree import KnockoutBracket
from backend.services.knockout_tree import apply_byes
from backend.services.knockout_tree import champion_path
from backend.services.knockout_tree import link_feeders
from backend.services.knockout_tree import order_ties
from backend.services.knockout_tree import visible_brackets
from backend.services.standings_service import get_league_standings


_TeamName = tuple[str, str | None]
_ProfileInputs = tuple[ByeProfile | None, list[SeededTeam], dict[int, str]]


def get_league_bracket(
        league_id: int,
        season_id: int) -> dict[str, Any] | None:
    """Return knockout brackets for one league season.

    ``None`` means the league does not exist. A season with
    nothing to draw has empty brackets and no consumed rounds.
    A round whose tie ``visible_brackets`` drops is absent.
    """
    if not league_repository.league_exists(league_id):
        return None
    frame = knockout_repository.fetch_knockout_matches(
        league_id,
        season_id)
    matches = _matches_from_frame(frame)
    profile, seeds, table_names = _profile_inputs(
        league_id,
        season_id)
    shown = _shown_brackets(
        matches,
        _sport_id(frame),
        profile,
        seeds)
    return _payload(
        league_id,
        season_id,
        shown,
        _team_names(matches, table_names))


def _profile_inputs(
        league_id: int,
        season_id: int) -> _ProfileInputs:
    """Profile, seeds and table names, or empties when it stays off.

    ``active_bye_profile`` already returns None unless every
    league-phase match is played and the league has a profile.
    Standings are read only in that case. Places stay unfiltered
    here. ``apply_byes`` keeps the ones the profile names.
    """
    unplayed = knockout_repository.count_unplayed_league_matches(
        league_id,
        season_id)
    profile = active_bye_profile(league_id, unplayed)
    if profile is None:
        return (None, [], {})
    payload = get_league_standings(league_id, season_id, "overall")
    if payload is None:
        return (None, [], {})
    return (profile, _seeds(payload), _table_names(payload))


def _seeds(payload: dict[str, Any]) -> list[SeededTeam]:
    """Map overall-table rows. Position starts at 1."""
    seeds: list[SeededTeam] = []
    for row in payload.get("standings", []):
        team_id = _optional_int(row.get("team_id"))
        position = _optional_int(row.get("position"))
        if team_id is None or position is None:
            continue
        seeds.append(SeededTeam(team_id, position))
    return seeds


def _table_names(payload: dict[str, Any]) -> dict[int, str]:
    """Team names from the table. It has no shortcut."""
    names: dict[int, str] = {}
    for row in payload.get("standings", []):
        team_id = _optional_int(row.get("team_id"))
        if team_id is None:
            continue
        names[team_id] = _required_text(row.get("team_name"))
    return names


def _shown_brackets(
        matches: list[TieMatch],
        sport_id: int | None,
        profile: ByeProfile | None,
        seeds: list[SeededTeam]) -> list[KnockoutBracket]:
    """Score, link, mark and keep only brackets that draw."""
    grouped = group_ties(matches)
    linked = link_feeders(_score_ties(grouped.ties, sport_id))
    # Ścieżka przed kolejnością. Mecz o 3. miejsce nie jest kolumną.
    prepared = order_ties(champion_path(
        apply_byes(linked, seeds, profile)))
    thirds = _score_ties(grouped.third_place, sport_id)
    return visible_brackets(_family_brackets(prepared, thirds))


def _score_ties(
        ties: list[BracketTie],
        sport_id: int | None) -> list[BracketTie]:
    """Fill the sport score. An unknown sport leaves the tie."""
    if sport_id is None:
        return list(ties)
    return [tie_with_score(tie, sport_id) for tie in ties]


def _family_brackets(
        ties: list[BracketTie],
        third_places: list[BracketTie]) -> list[KnockoutBracket]:
    """One bracket per family. The third-place tie stays beside it.

    Several third-place ties would not fit the single field, so
    the lowest ``tie_id`` is the one that is drawn.
    """
    grouped: dict[str, list[BracketTie]] = {}
    for tie in ties:
        if tie.depth is None:
            continue
        grouped.setdefault(tie.family, []).append(tie)
    thirds = _third_by_family(third_places)
    for family in thirds:
        grouped.setdefault(family, [])
    brackets: list[KnockoutBracket] = []
    for family in sorted(grouped):
        brackets.append(KnockoutBracket(
            bracket_id=family,
            title="",
            ties=grouped[family],
            third_place=thirds.get(family)))
    return brackets


def _third_by_family(
        ties: list[BracketTie]) -> dict[str, BracketTie]:
    """The first third-place tie of each family, by ``tie_id``."""
    chosen: dict[str, BracketTie] = {}
    ordered = sorted(ties, key=lambda tie: tie.tie_id)
    for tie in ordered:
        chosen.setdefault(tie.family, tie)
    return chosen


def _payload(
        league_id: int,
        season_id: int,
        shown: list[KnockoutBracket],
        names: dict[int, _TeamName]) -> dict[str, Any]:
    """Response dictionary. Columns run from the earliest phase."""
    return {
        "league_id": league_id,
        "season_id": season_id,
        "consumed_round_numbers": _consumed_rounds(shown),
        "brackets": [
            _bracket_payload(bracket, names)
            for bracket in shown]}


def _consumed_rounds(shown: list[KnockoutBracket]) -> list[int]:
    """Rounds of brackets that stayed. A hidden phase adds none."""
    found: set[int] = set()
    for bracket in shown:
        found.update(bracket.consumed_round_numbers)
    return sorted(found)


def _bracket_payload(
        bracket: KnockoutBracket,
        names: dict[int, _TeamName]) -> dict[str, Any]:
    """One drawn bracket, with the third-place tie under the final."""
    third = bracket.third_place
    return {
        "bracket_id": bracket.bracket_id,
        "title": bracket.title,
        "columns": _columns(bracket.ties, names),
        "third_place": (
            None if third is None else _tie_payload(third, names))}


def _columns(
        ties: list[BracketTie],
        names: dict[int, _TeamName]) -> list[dict[str, Any]]:
    """Group an ordered tie list. The earliest phase is first."""
    columns: list[dict[str, Any]] = []
    bucket: list[BracketTie] = []
    for tie in ties:
        if tie.depth is None:
            continue
        if bucket and bucket[0].depth != tie.depth:
            _append_column(columns, bucket, names)
            bucket = []
        bucket.append(tie)
    _append_column(columns, bucket, names)
    return columns


def _append_column(
        columns: list[dict[str, Any]],
        bucket: list[BracketTie],
        names: dict[int, _TeamName]) -> None:
    """Append one phase. An empty bucket adds nothing."""
    if not bucket:
        return
    head = bucket[0]
    depth = head.depth
    if depth is None:
        return
    columns.append({
        "depth": depth,
        "stage_label": head.stage_label,
        "ties": [_tie_payload(tie, names) for tie in bucket]})


def _tie_payload(
        tie: BracketTie,
        names: dict[int, _TeamName]) -> dict[str, Any]:
    """Fields the screen reads. The score winner stays internal."""
    return {
        "tie_id": tie.tie_id,
        "teams": [
            _team_payload(team_id, names)
            for team_id in tie.team_ids],
        "is_bye": tie.is_bye,
        "pending_opponent_label": tie.pending_opponent_label,
        "seed_position": tie.seed_position,
        "advanced_team_id": tie.advanced_team_id,
        "on_champion_path": tie.on_champion_path,
        "feeder_tie_ids": list(tie.feeder_tie_ids),
        "aggregate": _ordered_totals(
            tie.aggregate_by_team,
            tie.team_ids),
        "series_wins": _ordered_totals(
            tie.series_wins_by_team,
            tie.team_ids),
        "matches": [_match_payload(match) for match in tie.matches]}


def _team_payload(
        team_id: int,
        names: dict[int, _TeamName]) -> dict[str, Any]:
    """Name and shortcut. A missing team has an empty name."""
    name, shortcut = names.get(team_id, ("", None))
    return {
        "team_id": team_id,
        "name": name,
        "shortcut": shortcut}


def _ordered_totals(
        totals: dict[int, int] | None,
        team_ids: tuple[int, ...]) -> list[int] | None:
    """Two numbers in team order, or None when there is no sum."""
    if totals is None or len(team_ids) != 2:
        return None
    ordered: list[int] = []
    for team_id in team_ids:
        if team_id not in totals:
            return None
        ordered.append(totals[team_id])
    return ordered


def _match_payload(match: TieMatch) -> dict[str, Any]:
    """One leg. Extra-time goals stay beside the regulation score.

    A final stored as 0:0 can still be 1:0 after extra time. The
    card needs both totals, plus the penalty count.
    """
    return {
        "match_id": match.match_id,
        "game_date": match.game_date,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "home_extra_time_goals": match.home_extra_time_goals,
        "away_extra_time_goals": match.away_extra_time_goals,
        "home_penalty_goals": match.home_penalty_goals,
        "away_penalty_goals": match.away_penalty_goals,
        "is_played": match.is_played,
        "decided_by": match.decided_by}


def _team_names(
        matches: list[TieMatch],
        table_names: dict[int, str]) -> dict[int, _TeamName]:
    """Names from knockout matches, then the table for the rest.

    A placeholder never plays a knockout match, so its name comes
    from the standings row. That row has no shortcut.
    """
    names: dict[int, _TeamName] = {}
    for match in matches:
        names[match.home_team_id] = (
            match.home_team_name,
            match.home_team_shortcut)
        names[match.away_team_id] = (
            match.away_team_name,
            match.away_team_shortcut)
    for team_id, name in table_names.items():
        if team_id in names:
            continue
        names[team_id] = (name, None)
    return names


def _matches_from_frame(frame: pd.DataFrame) -> list[TieMatch]:
    """Map rows. A row without both teams is skipped."""
    if frame.empty:
        return []
    matches: list[TieMatch] = []
    for _, row in frame.iterrows():
        match = _match_from_row(row)
        if match is not None:
            matches.append(match)
    return matches


def _match_from_row(row: pd.Series) -> TieMatch | None:
    """One row, or None when the match cannot join a tie."""
    match_id = _optional_int(_cell(row, "match_id"))
    round_number = _optional_int(_cell(row, "round_number"))
    home_team_id = _optional_int(_cell(row, "home_team_id"))
    away_team_id = _optional_int(_cell(row, "away_team_id"))
    if (match_id is None or round_number is None
            or home_team_id is None or away_team_id is None):
        return None
    result = _optional_text(_cell(row, "result"))
    return TieMatch(
        match_id=match_id,
        round_number=round_number,
        leg_index=None,
        game_date=_game_date(_cell(row, "game_date")),
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team_name=_required_text(_cell(row, "home_team_name")),
        away_team_name=_required_text(_cell(row, "away_team_name")),
        home_team_shortcut=_optional_text(
            _cell(row, "home_team_shortcut")),
        away_team_shortcut=_optional_text(
            _cell(row, "away_team_shortcut")),
        home_goals=_optional_int(_cell(row, "home_goals")),
        away_goals=_optional_int(_cell(row, "away_goals")),
        result=result,
        is_played=_is_played(result),
        home_extra_time_goals=_optional_int(
            _cell(row, "home_extra_time_goals")),
        away_extra_time_goals=_optional_int(
            _cell(row, "away_extra_time_goals")),
        home_penalty_goals=_optional_int(
            _cell(row, "home_penalty_goals")),
        away_penalty_goals=_optional_int(
            _cell(row, "away_penalty_goals")),
        ot_winner=_optional_int(_cell(row, "ot_winner")),
        so_winner=_optional_int(_cell(row, "so_winner")))


def _sport_id(frame: pd.DataFrame) -> int | None:
    """The league's sport. One season uses the first value present."""
    if frame.empty or "sport_id" not in frame.columns:
        return None
    for value in frame["sport_id"]:
        sport_id = _optional_int(value)
        if sport_id is not None:
            return sport_id
    return None


def _cell(row: pd.Series, column: str) -> object:
    """Column value, or None when the frame did not select it."""
    if column not in row.index:
        return None
    return row[column]


def _is_played(result: str | None) -> bool:
    """True when a result other than empty or ``"0"`` is stored."""
    return result not in (None, "", "0")


def _optional_int(value: object) -> int | None:
    """Convert a nullable number. Missing stays None."""
    if value is None or _is_missing(value):
        return None
    return int(value)


def _optional_text(value: object) -> str | None:
    """Convert a nullable string. A blank stays None."""
    if value is None or _is_missing(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def _required_text(value: object) -> str:
    """String for a team name. A missing name is empty."""
    text = _optional_text(value)
    if text is None:
        return ""
    return text


def _game_date(value: object) -> datetime | None:
    """Match date, or None when the cell is empty."""
    if value is None or _is_missing(value):
        return None
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _is_missing(value: object) -> bool:
    """True for SQL NULL. A text result is never missing this way."""
    if isinstance(value, str):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
