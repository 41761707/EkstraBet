"""Rank upcoming NHL skaters by stored prop probabilities."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import pandas as pd


POINT_EVENT_ID = 192
GOAL_EVENT_ID = 196
ASSIST_EVENT_ID = 194
SHOT_EVENT_ID = 190
COUNTING_LINE = 0.5
SHOT_LINE = 2.5
LINE_EPSILON = 0.001
MIN_LIMIT = 1
MAX_LIMIT = 50
_METRIC_SPECS = (
    ("point", "Punkt", "P(punkt)", POINT_EVENT_ID, COUNTING_LINE),
    ("goal", "Gol", "P(gol)", GOAL_EVENT_ID, COUNTING_LINE),
    ("assist", "Asysta", "P(asysta)", ASSIST_EVENT_ID, COUNTING_LINE),
    ("shot", "Strzał", "P(SOG > 2.5)", SHOT_EVENT_ID, SHOT_LINE))


def build_hockey_player_event_rankings(
        frame: pd.DataFrame,
        limit: int | None) -> dict[str, Any]:
    """Return four rankings for unplayed matches that already have props.

    ``limit`` cuts each list after ranks are assigned. ``None`` keeps
    every skater. A player who still has props on two unplayed matches
    stays on the earlier ``game_date``.
    """
    _validate_limit(limit)
    appearances = _nearest_appearances(frame)
    return {
        "match_count": len({item["match_id"] for item in appearances}),
        "rankings": _build_rankings(appearances, limit)}


def _validate_limit(limit: int | None) -> None:
    """Reject a limit outside the public query range."""
    if limit is None:
        return
    if limit < MIN_LIMIT or limit > MAX_LIMIT:
        raise ValueError("Ranking limit must be between 1 and 50")


def _build_rankings(
        appearances: list[dict[str, Any]],
        limit: int | None) -> list[dict[str, Any]]:
    """Assemble the four metric boards in display order."""
    return [
        _ranking(spec, appearances, limit)
        for spec in _METRIC_SPECS]


def _ranking(
        spec: tuple[str, str, str, int, float],
        appearances: list[dict[str, Any]],
        limit: int | None) -> dict[str, Any]:
    """Sort one metric and assign ranks before the optional cut."""
    metric, label, hint, _event_id, _line = spec
    ranked = _sorted_rows(appearances, metric)
    visible = ranked if limit is None else ranked[:limit]
    return {
        "metric": metric,
        "label": label,
        "hint": hint,
        "rows": visible}


def _sorted_rows(
        appearances: list[dict[str, Any]],
        metric: str) -> list[dict[str, Any]]:
    """Highest probability first. Equal values break on the name."""
    candidates = []
    for appearance in appearances:
        probability = appearance["metrics"].get(metric)
        if probability is None:
            continue
        candidates.append(_row(appearance, metric, probability))
    candidates.sort(key=lambda item: (
        -item["probability"],
        item["player_name"].casefold()))
    rows = []
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index
        rows.append(candidate)
    return rows


def _row(
        appearance: dict[str, Any],
        metric: str,
        probability: float) -> dict[str, Any]:
    """Map one kept skater to the public ranking row."""
    expected_shots = None
    if metric == "shot":
        expected_shots = appearance["expected_shots"]
    return {
        "rank": 0,
        "player_id": appearance["player_id"],
        "player_name": appearance["player_name"],
        "team_id": appearance["team_id"],
        "team_name": appearance["team_name"],
        "team_shortcut": appearance["team_shortcut"],
        "match_id": appearance["match_id"],
        "game_date": appearance["game_date"],
        "opponent_name": appearance["opponent_name"],
        "opponent_shortcut": appearance["opponent_shortcut"],
        "is_home": appearance["is_home"],
        "probability": probability,
        "expected_shots": expected_shots}


def _nearest_appearances(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Keep one match per skater: the earlier date, then the smaller id."""
    if frame.empty:
        return []
    by_match: dict[tuple[int, int], dict[str, Any]] = {}
    for _, row in frame.iterrows():
        _absorb_line(by_match, row)
    by_player: dict[int, dict[str, Any]] = {}
    for appearance in by_match.values():
        player_id = appearance["player_id"]
        current = by_player.get(player_id)
        if current is None or _is_earlier(appearance, current):
            by_player[player_id] = appearance
    return list(by_player.values())


def _absorb_line(
        by_match: dict[tuple[int, int], dict[str, Any]],
        row: pd.Series) -> None:
    """Fold one prop line into the skater's match bucket."""
    key = _appearance_key(row)
    if key is None:
        return
    appearance = by_match.get(key)
    if appearance is None:
        created = _new_appearance(row, key)
        if created is None:
            return
        by_match[key] = created
        appearance = created
    _store_metric(appearance, row)


def _appearance_key(row: pd.Series) -> tuple[int, int] | None:
    """Return ``(player_id, match_id)`` when both identifiers exist."""
    player_id = _optional_int(row.get("player_id"))
    match_id = _optional_int(row.get("match_id"))
    if player_id is None or match_id is None:
        return None
    return player_id, match_id


def _new_appearance(
        row: pd.Series,
        key: tuple[int, int]) -> dict[str, Any] | None:
    """Build the match context for a skater, or None when it is incomplete."""
    team_id = _optional_int(row.get("team_id"))
    home_team_id = _optional_int(row.get("home_team_id"))
    away_team_id = _optional_int(row.get("away_team_id"))
    game_date = _as_datetime(row.get("game_date"))
    if (
            team_id is None
            or home_team_id is None
            or away_team_id is None
            or game_date is None):
        return None
    is_home = team_id == home_team_id
    if is_home:
        opponent_name = _required_text(row.get("away_name"))
        opponent_shortcut = _optional_text(row.get("away_shortcut"))
    else:
        opponent_name = _required_text(row.get("home_name"))
        opponent_shortcut = _optional_text(row.get("home_shortcut"))
    return {
        "player_id": key[0],
        "player_name": _required_text(row.get("player_name")),
        "team_id": team_id,
        "team_name": _required_text(row.get("team_name")),
        "team_shortcut": _optional_text(row.get("team_shortcut")),
        "match_id": key[1],
        "game_date": game_date,
        "opponent_name": opponent_name,
        "opponent_shortcut": opponent_shortcut,
        "is_home": is_home,
        "metrics": {},
        "expected_shots": None}


def _store_metric(appearance: dict[str, Any], row: pd.Series) -> None:
    """Keep the first valid probability for a metric on this match."""
    event_id = _optional_int(row.get("event_id"))
    line = _optional_float(row.get("line"))
    if event_id is None or line is None:
        return
    metric = _metric_for(event_id, line)
    if metric is None or metric in appearance["metrics"]:
        return
    probability = _valid_probability(row.get("probability"))
    if probability is None:
        return
    appearance["metrics"][metric] = probability
    if metric == "shot":
        appearance["expected_shots"] = _optional_float(
            row.get("expected_value"))


def _metric_for(event_id: int, line: float) -> str | None:
    """Map an event and line onto one ranking, or None when unused."""
    for metric, _label, _hint, spec_event, spec_line in _METRIC_SPECS:
        if event_id == spec_event and abs(line - spec_line) < LINE_EPSILON:
            return metric
    return None


def _is_earlier(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    """Prefer the sooner game, then the smaller match id."""
    candidate_key = (candidate["game_date"], candidate["match_id"])
    current_key = (current["game_date"], current["match_id"])
    return candidate_key < current_key


def _valid_probability(value: object) -> float | None:
    """Return a percent in ``[0, 100]``, or None when the value is unusable."""
    number = _optional_float(value)
    if number is None or number < 0.0 or number > 100.0:
        return None
    return number


def _optional_int(value: object) -> int | None:
    """Convert a nullable scalar to an int."""
    number = _optional_float(value)
    if number is None:
        return None
    return int(number)


def _optional_float(value: object) -> float | None:
    """Convert a nullable scalar to a finite float."""
    if _is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _optional_text(value: object) -> str | None:
    """Return a trimmed string, or None for blanks and nulls."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _required_text(value: object) -> str:
    """Return a display string. Null becomes an empty string."""
    return _optional_text(value) or ""


def _as_datetime(value: object) -> datetime | None:
    """Normalize a frame timestamp to ``datetime``."""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if _is_missing(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _is_missing(value: object) -> bool:
    """True for None and pandas nulls. Strings are never missing here."""
    if value is None:
        return True
    if isinstance(value, str):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
