"""Compose hockey player-prop recommendations with EV and history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.repositories import player_prop_bet_repository
from backend.services.bet_service import (
    _compute_ev,
    _compute_ev_after_tax)
from backend.services.probability_service import to_unit_probability
from backend.sports.hockey.player_prop_history import (
    DEFAULT_HISTORY_WINDOW,
    HISTORY_WINDOWS,
    PropSide,
    format_prop_event_name,
    is_prop_hit,
    prop_stat_spec,
    settle_prop)


HistoryIndex = dict[tuple[int, int, str], list[int]]
StatsIndex = dict[tuple[int, int], dict[str, int | None]]
SortBy = Literal["ev", "probability", "game_date"]
SortOrder = Literal["asc", "desc"]


def get_player_prop_recommendations(
        league_ids: list[int] | None = None,
        event_ids: list[int] | None = None,
        model_ids: list[int] | None = None,
        match_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        from_now: bool = False,
        min_odds: float | None = None,
        positive_ev_only: bool = False,
        apply_tax: bool = False,
        settlement_status: str | None = None,
        sort_by: SortBy = "ev",
        sort_order: SortOrder = "desc",
        page: int = 1,
        page_size: int = 50,
        history_window: int = DEFAULT_HISTORY_WINDOW) -> dict[str, Any]:
    """Return one page of prop lines with EV, settlement and history.

    ``history_window`` must already be 5 or 10. The router rejects
    other values. This function raises ``ValueError`` if one arrives.
    """
    _require_history_window(history_window)
    search = player_prop_bet_repository.search_player_prop_recommendations
    frame, total = search(
        league_ids=league_ids,
        event_ids=event_ids,
        model_ids=model_ids,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        min_odds=min_odds,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=BETTING_TAX_RATE,
        settlement_status=settlement_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size)
    page_frame = _first_line_per_model(frame)
    history = _history_index(
        player_prop_bet_repository.fetch_recent_player_stats(
            _anchors(page_frame), history_window))
    stats = _stats_index(
        player_prop_bet_repository.fetch_match_player_stats(
            _pairs(page_frame)))
    recommendations = [
        _map_row(row, apply_tax, history_window, history, stats)
        for _, row in page_frame.iterrows()]
    return {
        "recommendations": recommendations,
        "total_count": total,
        "filters_applied": _filters_applied(
            league_ids=league_ids,
            event_ids=event_ids,
            model_ids=model_ids,
            match_date=match_date,
            date_from=date_from,
            date_to=date_to,
            from_now=from_now,
            min_odds=min_odds,
            positive_ev_only=positive_ev_only,
            apply_tax=apply_tax,
            settlement_status=settlement_status,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            history_window=history_window)}


def _require_history_window(history_window: int) -> None:
    """Reject a window outside the catalog."""
    if history_window in HISTORY_WINDOWS:
        return
    raise ValueError("history_window must be 5 or 10")


def _first_line_per_model(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the first row when one line is paired with one model twice."""
    # Unikalny indeks powinien to wykluczyć. Zostaje pierwszy wiersz.
    if frame.empty:
        return frame
    return frame.drop_duplicates(
        subset=["line_id", "model_id"], keep="first")


def _anchors(
        frame: pd.DataFrame) -> list[tuple[int, int, datetime, str]]:
    """Build history anchors from the page, one per recommendation."""
    anchors: list[tuple[int, int, datetime, str]] = []
    for _, row in frame.iterrows():
        spec = prop_stat_spec(int(row["event_id"]))
        if spec is None:
            continue
        anchors.append((
            int(row["player_id"]),
            int(row["match_id"]),
            _as_datetime(row["game_date"]),
            spec.column))
    return anchors


def _pairs(frame: pd.DataFrame) -> list[tuple[int, int]]:
    """Return player and match pairs for settlement stats."""
    return [
        (int(row["player_id"]), int(row["match_id"]))
        for _, row in frame.iterrows()]


def _as_datetime(value: object) -> datetime:
    """Return a datetime anchor. Timestamps become plain datetimes."""
    if isinstance(value, pd.Timestamp):
        converted = value.to_pydatetime()
        if isinstance(converted, datetime):
            return converted
    if isinstance(value, datetime):
        return value
    raise ValueError("game_date must be a datetime")


def _history_index(frame: pd.DataFrame) -> HistoryIndex:
    """Group history by player, anchor match and column.

    Each series is reversed once. The repository returns newest
    first, and the strip reads oldest first.
    """
    if frame.empty:
        return {}
    grouped: HistoryIndex = {}
    for _, row in frame.iterrows():
        key = (
            int(row["player_id"]),
            int(row["anchor_match_id"]),
            str(row["stat_column"]))
        grouped.setdefault(key, []).append(int(row["stat_value"]))
    # Repo zwraca malejąco. Samo odwrócenie daje najstarszy mecz.
    for values in grouped.values():
        values.reverse()
    return grouped


def _stats_index(frame: pd.DataFrame) -> StatsIndex:
    """Index the four prop columns by player and match."""
    if frame.empty:
        return {}
    indexed: StatsIndex = {}
    for _, row in frame.iterrows():
        key = (int(row["player_id"]), int(row["match_id"]))
        indexed[key] = {
            "sog": _optional_int(row.get("sog")),
            "points": _optional_int(row.get("points")),
            "assists": _optional_int(row.get("assists")),
            "goals": _optional_int(row.get("goals"))}
    return indexed


def _optional_int(value: object) -> int | None:
    """Convert a nullable stat or id to int."""
    if value is None or pd.isna(value):
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    """Convert a nullable label to str."""
    if value is None or pd.isna(value):
        return None
    return str(value)


def _team(row: pd.Series, prefix: str) -> dict[str, Any]:
    """Map home or away columns to the match-team shape."""
    return {
        "id": int(row[f"{prefix}_team_id"]),
        "name": str(row[f"{prefix}_team_name"]),
        "shortcut": _optional_str(row.get(f"{prefix}_team_shortcut"))}


def _history_payload(
        values: list[int],
        line: float,
        side: PropSide,
        window: int) -> dict[str, Any]:
    """Count hits on the already oldest-first series."""
    hits = sum(
        1 for value in values if is_prop_hit(value, line, side))
    return {
        "window": window,
        "played": len(values),
        "hits": hits,
        "points": [{"value": value} for value in values]}


def _settlement_value(
        stats: StatsIndex,
        player_id: int,
        match_id: int,
        column: str) -> int | None:
    """Return this match's stat, or None when the pair is missing."""
    match_stats = stats.get((player_id, match_id))
    if match_stats is None:
        return None
    return match_stats.get(column)


def _map_row(
        row: pd.Series,
        apply_tax: bool,
        history_window: int,
        history: HistoryIndex,
        stats: StatsIndex) -> dict[str, Any]:
    """Map one page row. EV is probability times odds, not Poisson mean."""
    spec = prop_stat_spec(int(row["event_id"]))
    if spec is None:
        raise ValueError(
            f"Unknown player prop event_id: {int(row['event_id'])}")
    line = float(row["line"])
    probability = to_unit_probability(float(row["probability"]))
    odds = float(row["odds"])
    player_id = int(row["player_id"])
    match_id = int(row["match_id"])
    values = history.get((player_id, match_id, spec.column), [])
    stat_value = _settlement_value(
        stats, player_id, match_id, spec.column)
    # Status liczy settle_prop. Kolumna SQL zostaje filtrem paginacji.
    return {
        "line_id": int(row["line_id"]),
        "player_id": player_id,
        "player_name": str(row["player_name"]),
        "line": line,
        "match_id": match_id,
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "season_id": int(row["season_id"]),
        "game_date": row["game_date"],
        "home_team": _team(row, "home"),
        "away_team": _team(row, "away"),
        "event_id": spec.event_id,
        "event_name": format_prop_event_name(
            str(row["event_name"]), line),
        "odds": odds,
        "probability": probability,
        "probability_pct": round(probability * 100, 2),
        "ev": _compute_ev(probability, odds),
        "ev_after_tax": _compute_ev_after_tax(
            probability, odds, apply_tax, BETTING_TAX_RATE),
        "bookmaker_id": _optional_int(row.get("bookmaker_id")),
        "bookmaker_name": _optional_str(row.get("bookmaker_name")),
        "model_id": int(row["model_id"]),
        "model_name": str(row["model_name"]),
        "settlement_status": settle_prop(stat_value, line, spec.side),
        "history": _history_payload(
            values, line, spec.side, history_window)}


def _iso(value: date | None) -> str | None:
    """Serialize a filter date the same way as team recommendations."""
    if value is None:
        return None
    return value.isoformat()


def _filters_applied(
        league_ids: list[int] | None,
        event_ids: list[int] | None,
        model_ids: list[int] | None,
        match_date: date | None,
        date_from: date | None,
        date_to: date | None,
        from_now: bool,
        min_odds: float | None,
        positive_ev_only: bool,
        apply_tax: bool,
        settlement_status: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        history_window: int) -> dict[str, Any]:
    """Echo the request. Dates are ISO strings, the window stays int."""
    return {
        "league_ids": league_ids,
        "event_ids": event_ids,
        "model_ids": model_ids,
        "match_date": _iso(match_date),
        "date_from": _iso(date_from),
        "date_to": _iso(date_to),
        "from_now": from_now,
        "min_odds": min_odds,
        "positive_ev_only": positive_ev_only,
        "apply_tax": apply_tax,
        "tax_rate": BETTING_TAX_RATE if apply_tax else None,
        "settlement_status": settlement_status,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": page_size,
        "history_window": history_window}
