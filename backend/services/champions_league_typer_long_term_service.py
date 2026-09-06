"""Domain rules for Typer long-term markets, picks and settlement."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from backend.repositories import (
    champions_league_typer_long_term_repository as repository)
from backend.repositories import user_repository


LEAGUE_PHASE_TEAM_COUNT = repository.LEAGUE_PHASE_TEAM_COUNT
LEAGUE_PHASE_MATCHES_PER_TEAM = repository.LEAGUE_PHASE_MATCHES_PER_TEAM
LEAGUE_PHASE_SETTLED_MATCH_COUNT = (
    repository.LEAGUE_PHASE_SETTLED_MATCH_COUNT)
MARKET_KIND_RANKED_TEAM_TABLE = "ranked_team_table"
MARKET_KIND_SINGLE_TEAM = "single_team"
MARKET_KIND_FREE_TEXT = "free_text"
MARKET_KIND_YES_NO = "yes_no"
SCORING_KIND_ZONE_AND_POSITION = "zone_and_position"
SCORING_KIND_EXACT_SUBJECT = "exact_subject"


class TyperServiceError(Exception):
    """Base error for long-term Typer domain rules."""


class TyperNotFoundError(TyperServiceError):
    """Market, season or user row was not found."""


class TyperConflictError(TyperServiceError):
    """Pick or settlement cannot proceed in the current stored state."""


class TyperValidationError(TyperServiceError):
    """Request payload violates long-term contest rules."""


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


def zone_for_position(
        position: int,
        selection_size: int,
        top_zone_size: int,
        bot_zone_size: int) -> str | None:
    """Return 'top', 'bot' or None for a 1-based table slot."""
    # -1 i 0 oznaczają brak strefy (kolumny rynku nieużywane)
    if top_zone_size > 0 and position <= top_zone_size:
        return "top"
    if bot_zone_size > 0 and position > selection_size - bot_zone_size:
        return "bot"
    return None


def score_zone_and_position(
        pick_team_ids: list[int],
        result_team_ids: list[int],
        points_per_zone: float,
        points_per_exact_position: float,
        top_zone_size: int,
        bot_zone_size: int) -> float:
    """Score ranked table. Middle slots never score.

    Same zone -> points_per_zone; same position -> plus exact bonus.
    """
    selection_size = len(pick_team_ids)
    result_positions = {
        team_id: index + 1
        for index, team_id in enumerate(result_team_ids)
    }
    total = 0.0
    for index, team_id in enumerate(pick_team_ids):
        pick_position = index + 1
        pick_zone = zone_for_position(
            pick_position,
            selection_size,
            top_zone_size,
            bot_zone_size)
        if pick_zone is None:
            continue
        # join po team_id: ta sama drużyna może stać na innym miejscu
        result_position = result_positions.get(team_id)
        if result_position is None:
            continue
        result_zone = zone_for_position(
            result_position,
            selection_size,
            top_zone_size,
            bot_zone_size)
        if result_zone != pick_zone:
            continue
        total += float(points_per_zone)
        if result_position == pick_position:
            total += float(points_per_exact_position)
    return total


def normalize_subject_text(raw: str) -> str:
    """Trim, collapse whitespace, Unicode casefold (user: lower + spaces)."""
    return " ".join(raw.split()).casefold()


def score_exact_subject(
        pick_values: list[str] | list[int] | list[bool],
        result_values: list[str] | list[int] | list[bool],
        points_per_correct: float) -> float:
    """Return |set(picks) ∩ set(results)| * points_per_correct."""
    return (
        float(len(set(pick_values) & set(result_values)))
        * float(points_per_correct))


def score_long_term(
        scoring_kind: str,
        pick_team_ids: list[int],
        result_team_ids: list[int],
        points_per_correct: float,
        points_per_exact_position: float,
        top_zone_size: int,
        bot_zone_size: int,
        market_kind: str = "",
        pick_subject_texts: list[str] | None = None,
        result_subject_texts: list[str] | None = None,
        pick_is_text_correct: bool | None = None,
        result_is_text_correct: bool | None = None) -> float:
    """Dispatch zone_and_position or exact_subject.

    Unknown scoring_kind or exact_subject market_kind -> 0.0.
    Text values must already be normalized.
    """
    if scoring_kind == SCORING_KIND_ZONE_AND_POSITION:
        return score_zone_and_position(
            pick_team_ids,
            result_team_ids,
            points_per_correct,
            points_per_exact_position,
            top_zone_size,
            bot_zone_size)
    if scoring_kind != SCORING_KIND_EXACT_SUBJECT:
        return 0.0
    return _score_exact_subject_for_kind(
        market_kind,
        pick_team_ids,
        result_team_ids,
        pick_subject_texts,
        result_subject_texts,
        pick_is_text_correct,
        result_is_text_correct,
        points_per_correct)


def _score_exact_subject_for_kind(
        market_kind: str,
        pick_team_ids: list[int],
        result_team_ids: list[int],
        pick_subject_texts: list[str] | None,
        result_subject_texts: list[str] | None,
        pick_is_text_correct: bool | None,
        result_is_text_correct: bool | None,
        points_per_correct: float) -> float:
    # dispatch po market_kind: bool True == 1 w Pythonie, nie mieszać list
    if market_kind == MARKET_KIND_FREE_TEXT:
        return score_exact_subject(
            list(pick_subject_texts or []),
            list(result_subject_texts or []),
            points_per_correct)
    if market_kind == MARKET_KIND_SINGLE_TEAM:
        return score_exact_subject(
            pick_team_ids,
            result_team_ids,
            points_per_correct)
    if market_kind == MARKET_KIND_YES_NO:
        picks: list[bool] = (
            [] if pick_is_text_correct is None
            else [pick_is_text_correct])
        results: list[bool] = (
            [] if result_is_text_correct is None
            else [result_is_text_correct])
        return score_exact_subject(picks, results, points_per_correct)
    return 0.0


def is_league_phase_complete(auto_result: dict[str, Any]) -> bool:
    """Return True when 36 teams each have 8 settled league-phase matches."""
    return (
        int(auto_result["participant_count"]) == LEAGUE_PHASE_TEAM_COUNT
        and int(auto_result["min_matches_per_team"])
        == LEAGUE_PHASE_MATCHES_PER_TEAM
        and int(auto_result["max_matches_per_team"])
        == LEAGUE_PHASE_MATCHES_PER_TEAM
        and int(auto_result["settled_match_count"])
        == LEAGUE_PHASE_SETTLED_MATCH_COUNT)


def get_dashboard(
        user_id: int,
        season_id: int | None) -> dict[str, Any]:
    """Return markets, candidates and the caller's private picks."""
    with _repository_errors():
        document = repository.fetch_long_term_dashboard(
            user_id, season_id)
    return _map_dashboard(document)


def save_picks(
        user_id: int,
        market_id: int,
        team_ids: list[int]) -> dict[str, Any]:
    """Replace the caller's ordered table; identical sequences skip audit."""
    with _repository_errors():
        stored = repository.save_long_term_picks(
            user_id, market_id, team_ids)
    return _map_saved_picks(stored)


def get_own_history(
        user_id: int,
        market_id: int) -> list[dict[str, Any]]:
    """Return chronological audit rows for the caller's market set."""
    with _repository_errors():
        return repository.fetch_own_long_term_history(
            user_id, market_id)


def get_admin_history(
        user_uuid: str,
        market_id: int | None = None,
        season_id: int | None = None) -> list[dict[str, Any]]:
    """Return audit rows for a user identified by public UUID."""
    with _repository_errors():
        return repository.fetch_admin_long_term_history(
            user_uuid, market_id, season_id)


def get_auto_result(market_id: int) -> dict[str, Any]:
    """Return ranked-table proposal and league-phase completeness.

    Auto-calculation never writes results or awards points.
    """
    with _repository_errors():
        document = repository.fetch_auto_result(market_id)
    return _map_auto_result(document)


def settle_market(
        market_id: int,
        team_ids: list[int],
        admin_id: int) -> dict[str, Any]:
    """Approve or correct the ranked table after a complete league phase."""
    with _repository_errors():
        auto_result = repository.fetch_auto_result(market_id)
        if not is_league_phase_complete(auto_result):
            raise TyperConflictError("League phase is not complete")
        stored = repository.settle_market(market_id, team_ids, admin_id)
    return _map_settled(stored)


def _map_auto_result(document: dict[str, Any]) -> dict[str, Any]:
    complete = is_league_phase_complete(document)
    selection_size = int(document["selection_size"])
    top_zone_size = int(document["top_zone_size"])
    bot_zone_size = int(document["bot_zone_size"])
    standings = list(document["standings"])
    # pełna tabela 36, nie prefiks TOP 8
    proposed = standings if complete else []
    proposed_ids = [int(row["team_id"]) for row in proposed]
    settler = _settler_public_identity(document.get("settled_by"))
    return {
        "market_id": int(document["market_id"]),
        "league_id": int(document["league_id"]),
        "season_id": int(document["season_id"]),
        "market_key": str(document["market_key"]),
        "selection_size": selection_size,
        "points_per_correct": float(document["points_per_correct"]),
        "points_per_exact_position": float(
            document["points_per_exact_position"]),
        "top_zone_size": top_zone_size,
        "bot_zone_size": bot_zone_size,
        "settled_at": document["settled_at"],
        "settled_by_uuid": settler["settled_by_uuid"],
        "settled_by_display_name": settler["settled_by_display_name"],
        "is_complete": complete,
        "is_proposal": True,
        "participant_count": int(document["participant_count"]),
        "settled_match_count": int(document["settled_match_count"]),
        "min_matches_per_team": int(document["min_matches_per_team"]),
        "max_matches_per_team": int(document["max_matches_per_team"]),
        "required_participant_count": LEAGUE_PHASE_TEAM_COUNT,
        "required_matches_per_team": LEAGUE_PHASE_MATCHES_PER_TEAM,
        "required_settled_match_count": LEAGUE_PHASE_SETTLED_MATCH_COUNT,
        "proposed_team_ids": proposed_ids,
        "proposed_top_team_ids": _zone_prefix(
            proposed_ids, top_zone_size),
        "proposed_bot_team_ids": _zone_suffix(
            proposed_ids, bot_zone_size),
        "proposed_teams": proposed,
        "result_team_ids": [
            int(team_id)
            for team_id in document.get("result_team_ids") or []],
        "standings": standings
    }


def _map_dashboard(document: dict[str, Any]) -> dict[str, Any]:
    changes_by_market: dict[int, list[dict[str, Any]]] = {}
    for row in document.get("changes") or []:
        market_id = int(row["market_id"])
        changes_by_market.setdefault(market_id, []).append(row)
    markets = [
        _map_dashboard_market(
            market,
            changes_by_market.get(int(market["market_id"]), []))
        for market in document.get("markets") or []]
    return {
        "season_id": int(document["season_id"]),
        "markets": markets
    }


def _map_dashboard_market(
        market: dict[str, Any],
        changes: list[dict[str, Any]]) -> dict[str, Any]:
    picked = [int(team_id) for team_id in market["picked_team_ids"]]
    results = [int(team_id) for team_id in market["result_team_ids"]]
    points = None
    if results:
        # punkty dopiero po settle: puste result_team_ids to brak wyniku
        points = score_long_term(
            str(market["scoring_kind"]),
            picked,
            results,
            float(market["points_per_correct"]),
            float(market["points_per_exact_position"]),
            int(market["top_zone_size"]),
            int(market["bot_zone_size"]))
    return {
        "market_id": int(market["market_id"]),
        "league_id": int(market["league_id"]),
        "season_id": int(market["season_id"]),
        "market_key": str(market["market_key"]),
        "title": str(market["title"]),
        "description": market["description"],
        "selection_size": int(market["selection_size"]),
        "points_per_correct": float(market["points_per_correct"]),
        "points_per_exact_position": float(
            market["points_per_exact_position"]),
        "market_kind": str(market["market_kind"]),
        "scoring_kind": str(market["scoring_kind"]),
        "top_zone_size": int(market["top_zone_size"]),
        "bot_zone_size": int(market["bot_zone_size"]),
        "settled_at": market["settled_at"],
        "deadline_at": market["deadline_at"],
        "is_locked": bool(market["is_locked"]),
        "candidates": list(market["candidates"]),
        "picked_team_ids": picked,
        "result_team_ids": results,
        "points": points,
        "changes": changes
    }


def _map_saved_picks(stored: dict[str, Any]) -> dict[str, Any]:
    previous = stored["previous_team_ids"]
    return {
        "market_id": int(stored["market_id"]),
        "team_ids": [int(team_id) for team_id in stored["team_ids"]],
        "previous_team_ids": (
            None if previous is None
            else [int(team_id) for team_id in previous]),
        "audit_written": bool(stored["audit_written"])
    }


def _map_settled(stored: dict[str, Any]) -> dict[str, Any]:
    team_ids = [int(team_id) for team_id in stored["team_ids"]]
    settler = _settler_public_identity(stored.get("settled_by"))
    return {
        "market_id": int(stored["market_id"]),
        "team_ids": team_ids,
        "settled_by_uuid": settler["settled_by_uuid"],
        "settled_by_display_name": settler["settled_by_display_name"],
        "settled_at": stored["settled_at"],
        "result_team_ids": [
            int(team_id) for team_id in stored["result_team_ids"]]
    }


def _zone_prefix(team_ids: list[int], zone_size: int) -> list[int]:
    if zone_size <= 0:
        return []
    return list(team_ids[:zone_size])


def _zone_suffix(team_ids: list[int], zone_size: int) -> list[int]:
    if zone_size <= 0:
        return []
    return list(team_ids[-zone_size:])


def _settler_public_identity(
        settled_by: object) -> dict[str, str | None]:
    empty = {
        "settled_by_uuid": None,
        "settled_by_display_name": None
    }
    if settled_by is None:
        return empty
    user = user_repository.fetch_user_by_id(int(settled_by))
    if user is None:
        return empty
    display_name = user.get("display_name")
    return {
        "settled_by_uuid": str(user["uuid"]),
        "settled_by_display_name": (
            None if display_name is None else str(display_name))
    }
