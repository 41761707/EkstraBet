"""Domain rules for the Champions League Typer contest."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Literal

from backend.config import get_settings
from backend.repositories import league_repository
from backend.repositories import (
    champions_league_typer_repository as repository)
from backend.services.round_label import resolve_round_label


CHAMPIONS_LEAGUE_ID = 42
SUPERBET_BOOKMAKER_ID = 1
HOME_EVENT_ID = 1
DRAW_EVENT_ID = 2
AWAY_EVENT_ID = 3
GROUP_STAGE_MIN_ROUND = 1
GROUP_STAGE_MAX_ROUND = 8
KNOCKOUT_ROUND_MIN = 900

OUTCOME_TO_EVENT = {
    "1": HOME_EVENT_ID,
    "X": DRAW_EVENT_ID,
    "2": AWAY_EVENT_ID
}
EVENT_TO_OUTCOME = {
    HOME_EVENT_ID: "1",
    DRAW_EVENT_ID: "X",
    AWAY_EVENT_ID: "2"
}
REGULATION_RESULTS = frozenset({"1", "X", "2"})

TyperOutcome = Literal["1", "X", "2"]


class TyperServiceError(Exception):
    """Base error for Champions League Typer domain rules."""


class TyperNotFoundError(TyperServiceError):
    """Match, publication, season or user row was not found."""


class TyperConflictError(TyperServiceError):
    """Publication or pick cannot change in the current stored state."""


class TyperValidationError(TyperServiceError):
    """Request payload violates Typer contest rules."""


@contextmanager
def _repository_errors() -> Iterator[None]:
    try:
        yield
    except repository.TyperNotFoundError as exc:
        raise TyperNotFoundError(str(exc)) from exc
    except repository.TyperConflictError as exc:
        raise TyperConflictError(str(exc)) from exc
    except repository.TyperValidationError as exc:
        raise TyperValidationError(str(exc)) from exc


def is_group_stage_round(round_number: int) -> bool:
    """Return True for Champions League league-phase rounds 1-8."""
    return GROUP_STAGE_MIN_ROUND <= round_number <= GROUP_STAGE_MAX_ROUND


def is_knockout_round(round_number: int) -> bool:
    """Return True for cup rounds numbered 900 or higher."""
    return round_number >= KNOCKOUT_ROUND_MIN


def event_id_for_outcome(outcome: str) -> int:
    """Map a 1X2 outcome to the Superbet 1/X/2 event id."""
    event_id = OUTCOME_TO_EVENT.get(outcome)
    if event_id is None:
        raise TyperValidationError("outcome must be 1, X or 2")
    return event_id


def outcome_for_event_id(event_id: int | None) -> str | None:
    """Map a 1/X/2 event id to the public outcome letter."""
    if event_id is None:
        return None
    return EVENT_TO_OUTCOME.get(int(event_id))


def score_prediction(
        result: str | None,
        outcome: str | None,
        odds_home: float | None,
        odds_draw: float | None,
        odds_away: float | None) -> float | None:
    """Score a 1X2 pick from regulation result and Superbet odds.

    Canonical rule, identical to repository ``_POINTS_SQL``: a miss with
    an official 1/X/2 result is 0 even without odds; a hit without
    Superbet odds stays unsettled. Extra time and penalties are ignored
    because only ``matches.result`` is consulted.
    """
    if outcome is None:
        return None
    if result not in REGULATION_RESULTS:
        return None
    if outcome != result:
        return 0.0
    odds_by_outcome = {
        "1": odds_home,
        "X": odds_draw,
        "2": odds_away
    }
    odds = odds_by_outcome[outcome]
    if odds is None:
        return None
    return float(odds)


def publish_matches(
        season_id: int,
        round_number: int,
        match_ids: list[int],
        admin_id: int) -> list[dict[str, Any]]:
    """Publish a group-stage set of 9 or a complete knockout round.

    Odds rows are not required and are never written.
    """
    _validate_publication_set(season_id, round_number, match_ids)
    group_match_count = None
    if is_group_stage_round(round_number):
        group_match_count = get_settings().typer_lm_group_match_count
    with _repository_errors():
        rows = repository.publish_matches(
            season_id,
            round_number,
            match_ids,
            admin_id,
            group_match_count=group_match_count)
    return [_map_publication(row) for row in rows]


def save_prediction(
        user_id: int,
        match_id: int,
        outcome: TyperOutcome) -> dict[str, Any]:
    """Upsert the current 1X2 pick; identical picks skip audit."""
    event_id = event_id_for_outcome(outcome)
    with _repository_errors():
        stored = repository.save_prediction(user_id, match_id, event_id)
    return _map_saved_prediction(stored)


def get_dashboard(
        user_id: int,
        season_id: int | None) -> dict[str, Any]:
    """Return published rounds, private picks, odds and own audit."""
    with _repository_errors():
        document = repository.fetch_dashboard(user_id, season_id)
    special_rounds = league_repository.fetch_special_round_names()
    return {
        "season_id": int(document["season_id"]),
        "rounds": _group_dashboard_rounds(
            document["matches"],
            document["changes"],
            special_rounds)
    }


def get_revealed_predictions(
        season_id: int | None,
        round_number: int) -> dict[str, Any]:
    """Return started published matches with public 1X2 picks.

    Empty rounds before kick-off are a valid 200 with empty lists.
    """
    _validate_supported_round(round_number)
    with _repository_errors():
        document = repository.fetch_revealed_predictions(
            season_id, round_number)
    special_rounds = league_repository.fetch_special_round_names()
    matches, participants = _group_revealed_rows(document["rows"])
    resolved_round = int(document["round_number"])
    return {
        "season_id": int(document["season_id"]),
        "round_number": resolved_round,
        "round_label": _typer_round_label(
            resolved_round, special_rounds),
        "participants": participants,
        "matches": matches
    }


def get_leaderboard(season_id: int | None) -> list[dict[str, Any]]:
    """Return ranking scored from regulation results and Superbet odds."""
    with _repository_errors():
        return repository.fetch_leaderboard(season_id)


def get_own_prediction_history(
        user_id: int,
        match_id: int) -> list[dict[str, Any]]:
    """Return chronological audit rows for the caller's pick."""
    with _repository_errors():
        rows = repository.fetch_own_prediction_history(user_id, match_id)
    return [_map_change(row) for row in rows]


def get_admin_prediction_history(
        user_uuid: str,
        match_id: int | None = None,
        season_id: int | None = None) -> list[dict[str, Any]]:
    """Return audit rows for a user identified by public UUID."""
    with _repository_errors():
        rows = repository.fetch_admin_prediction_history(
            user_uuid, match_id, season_id)
    return [_map_change(row) for row in rows]


def get_admin_candidates(
        season_id: int,
        round_number: int) -> list[dict[str, Any]]:
    """Return CL matches for a round with publication and odds flags."""
    with _repository_errors():
        rows = repository.fetch_admin_candidates(season_id, round_number)
    return [_map_candidate(row) for row in rows]


def remove_publication(match_id: int, admin_id: int) -> None:
    """Delete a publication only before kickoff and when no picks exist.

    ``admin_id`` is accepted for the service contract; the repository
    does not persist who removed the row.
    """
    # repozytorium nie zapisuje, kto wycofał publikację
    _ = admin_id
    with _repository_errors():
        repository.remove_publication(match_id)


def _validate_publication_set(
        season_id: int,
        round_number: int,
        match_ids: list[int]) -> None:
    if not match_ids:
        raise TyperValidationError("At least one match id is required")
    if len(match_ids) != len(set(match_ids)):
        raise TyperValidationError(
            "Duplicate match ids in publication set")
    _validate_supported_round(round_number)
    if is_group_stage_round(round_number):
        _assert_group_stage_set(season_id, round_number, match_ids)
        return
    _assert_complete_knockout_set(season_id, round_number, match_ids)


def _validate_supported_round(round_number: int) -> None:
    if is_group_stage_round(round_number) or is_knockout_round(round_number):
        return
    raise TyperValidationError(
        "round_number must be a group-stage round 1-8 "
        "or a knockout round >= 900")


def _round_publication_sets(
        season_id: int,
        round_number: int) -> tuple[set[int], set[int]]:
    with _repository_errors():
        candidates = repository.fetch_admin_candidates(
            season_id, round_number)
    if not candidates:
        raise TyperNotFoundError(
            "No Champions League matches for this round")
    published_ids: set[int] = set()
    unpublished_ids: set[int] = set()
    for row in candidates:
        match_id = int(row["match_id"])
        if row["is_published"]:
            published_ids.add(match_id)
        else:
            unpublished_ids.add(match_id)
    return published_ids, unpublished_ids


def _reject_already_published(
        match_ids: list[int], published_ids: set[int]) -> None:
    if set(match_ids) & published_ids:
        raise TyperConflictError(
            "One or more matches are already published")


def _assert_group_stage_set(
        season_id: int,
        round_number: int,
        match_ids: list[int]) -> None:
    expected = get_settings().typer_lm_group_match_count
    published_ids, unpublished_ids = _round_publication_sets(
        season_id, round_number)
    _reject_already_published(match_ids, published_ids)
    # limit 9 dotyczy stanu kolejki, nie samej długości requestu
    if not set(match_ids).issubset(unpublished_ids):
        raise TyperValidationError(
            "Group-stage match ids must be unpublished matches "
            "of the requested round")
    if len(published_ids) + len(match_ids) != expected:
        raise TyperValidationError(
            f"Group-stage round must have exactly {expected} "
            "published matches")


def _assert_complete_knockout_set(
        season_id: int,
        round_number: int,
        match_ids: list[int]) -> None:
    published_ids, unpublished_ids = _round_publication_sets(
        season_id, round_number)
    _reject_already_published(match_ids, published_ids)
    if set(match_ids) != unpublished_ids:
        raise TyperValidationError(
            "Knockout publication must include every unpublished "
            "imported match of the round")


def _typer_round_label(
        round_number: int,
        special_rounds: dict[int, str]) -> str:
    label = resolve_round_label(round_number, special_rounds)
    return label if label else str(round_number)


def _group_revealed_rows(
        rows: list[dict[str, Any]]
        ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    matches_by_id: dict[int, dict[str, Any]] = {}
    participants_by_uuid: dict[str, dict[str, str]] = {}
    for row in rows:
        match_id = int(row["match_id"])
        if match_id not in matches_by_id:
            matches_by_id[match_id] = _map_revealed_match(row)
        pick = _map_revealed_pick(row)
        if pick is None:
            continue
        matches_by_id[match_id]["picks"].append(pick)
        user_uuid = pick["user_uuid"]
        if user_uuid not in participants_by_uuid:
            participants_by_uuid[user_uuid] = {
                "user_uuid": user_uuid,
                "display_name": _revealed_display_name(row)
            }
    participants = sorted(
        participants_by_uuid.values(),
        key=_participant_sort_key)
    return list(matches_by_id.values()), participants


def _participant_sort_key(item: dict[str, str]) -> tuple[str, str]:
    return (item["display_name"].casefold(), item["user_uuid"])


def _revealed_display_name(row: dict[str, Any]) -> str:
    # SQL już robi COALESCE do username; tu tylko normalizujemy etykietę
    raw = row["display_name"]
    if raw is None:
        return ""
    return str(raw).strip()


def _map_revealed_match(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": int(row["match_id"]),
        "game_date": row["game_date"],
        "home_team": _map_team(
            row["home_team_id"],
            row["home_team_name"],
            row["home_team_shortcut"]),
        "away_team": _map_team(
            row["away_team_id"],
            row["away_team_name"],
            row["away_team_shortcut"]),
        "picks": []
    }


def _map_revealed_pick(row: dict[str, Any]) -> dict[str, Any] | None:
    user_uuid = row["user_uuid"]
    if user_uuid is None:
        return None
    outcome = outcome_for_event_id(row["selected_event_id"])
    if outcome is None:
        raise TyperValidationError(
            "selected_event_id must be 1, 2 or 3")
    return {
        "user_uuid": str(user_uuid),
        "outcome": outcome
    }


def _group_dashboard_rounds(
        match_rows: list[dict[str, Any]],
        change_rows: list[dict[str, Any]],
        special_rounds: dict[int, str]) -> list[dict[str, Any]]:
    changes_by_match: dict[int, list[dict[str, Any]]] = {}
    for row in change_rows:
        match_id = int(row["match_id"])
        mapped = _map_change(row)
        changes_by_match.setdefault(match_id, []).append(mapped)
    rounds: list[dict[str, Any]] = []
    current_round: dict[str, Any] | None = None
    for row in match_rows:
        match_id = int(row["match_id"])
        match = _map_dashboard_match(
            row, changes_by_match.get(match_id, []))
        round_number = match["round_number"]
        if (
                current_round is None
                or current_round["round_number"] != round_number):
            current_round = {
                "round_number": round_number,
                "round_label": _typer_round_label(
                    round_number, special_rounds),
                "matches": []
            }
            rounds.append(current_round)
        current_round["matches"].append(match)
    return rounds


def _map_publication(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "published_at": row["published_at"]
    }


def _map_saved_prediction(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": int(row["match_id"]),
        "outcome": outcome_for_event_id(row["selected_event_id"]),
        "previous_outcome": outcome_for_event_id(
            row["previous_selected_event_id"]),
        "audit_written": bool(row["audit_written"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


def _map_dashboard_match(
        row: dict[str, Any],
        changes: list[dict[str, Any]]) -> dict[str, Any]:
    outcome = outcome_for_event_id(row["selected_event_id"])
    odds_home = row["odds_home"]
    odds_draw = row["odds_draw"]
    odds_away = row["odds_away"]
    return {
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "game_date": row["game_date"],
        "published_at": row["published_at"],
        "is_locked": bool(row["is_locked"]),
        "result": None if row["result"] is None else str(row["result"]),
        "home_team": _map_team(
            row["home_team_id"],
            row["home_team_name"],
            row["home_team_shortcut"]),
        "away_team": _map_team(
            row["away_team_id"],
            row["away_team_name"],
            row["away_team_shortcut"]),
        "odds_home": odds_home,
        "odds_draw": odds_draw,
        "odds_away": odds_away,
        "outcome": outcome,
        "points": score_prediction(
            row["result"],
            outcome,
            odds_home,
            odds_draw,
            odds_away),
        "changes": changes
    }


def _map_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "game_date": row["game_date"],
        "home_team": _map_team(
            row["home_team_id"],
            row["home_team_name"],
            row["home_team_shortcut"]),
        "away_team": _map_team(
            row["away_team_id"],
            row["away_team_name"],
            row["away_team_shortcut"]),
        "is_published": bool(row["is_published"]),
        "has_complete_superbet_odds": bool(
            row["has_complete_superbet_odds"])
    }


def _map_change(row: dict[str, Any]) -> dict[str, Any]:
    new_outcome = outcome_for_event_id(row["new_selected_event_id"])
    if new_outcome is None:
        raise TyperValidationError(
            "new_selected_event_id must be 1, 2 or 3")
    return {
        "match_id": int(row["match_id"]),
        "user_uuid": str(row["user_uuid"]),
        "display_name": str(row["display_name"]),
        "previous_outcome": outcome_for_event_id(
            row["previous_selected_event_id"]),
        "new_outcome": new_outcome,
        "changed_at": row["changed_at"]
    }


def _map_team(
        team_id: object,
        name: object,
        shortcut: object) -> dict[str, Any]:
    return {
        "id": int(team_id),
        "name": str(name),
        "shortcut": str(shortcut)
    }
