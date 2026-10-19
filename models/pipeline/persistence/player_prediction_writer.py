"""Upsert beta skater probabilities into ``player_predictions``."""

from __future__ import annotations

import math
from collections.abc import Collection
from collections.abc import Mapping
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any
from typing import Iterable

from backend.database import get_db_connection
from models.pipeline.labels.hockey_player_props import LINES_PER_SKATER
from models.pipeline.labels.hockey_player_props import PROP_LINES
from models.pipeline.labels.hockey_player_props import (
    poisson_over_probability)


_DELETE_TEAM_SQL = """
DELETE FROM player_predictions
WHERE match_id = %s
  AND model_id = %s
  AND team_id = %s
"""

_DELETE_ABSENT_SQL = """
DELETE FROM player_predictions
WHERE match_id = %s
  AND model_id = %s
  AND team_id = %s
  AND player_id NOT IN ({placeholders})
"""

_UPSERT_SQL = """
INSERT INTO player_predictions (
    match_id,
    player_id,
    team_id,
    model_id,
    event_id,
    line,
    expected_value,
    probability)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    team_id = VALUES(team_id),
    expected_value = VALUES(expected_value),
    probability = VALUES(probability)
"""


@dataclass(frozen=True)
class PlayerPredictionRow:
    """One over-probability for a skater, model, event and line."""

    match_id: int
    player_id: int
    team_id: int
    model_id: int
    event_id: int
    line: float
    expected_value: float
    probability: float


def build_player_prediction_rows(
        match_id: int,
        player_id: int,
        team_id: int,
        model_id: int,
        rates: Mapping[str, float],
        event_ids: Mapping[str, int]) -> list[PlayerPredictionRow]:
    """Expand four Poisson means into the seven beta lines.

    ``rates`` maps ``sog``, ``goals``, ``assists`` and ``points`` to
    lambda. ``event_ids`` maps the config keys ``sog_over``,
    ``goals_over``, ``assists_over`` and ``points_over``.
    """
    rows = [
        _line_row(
            match_id, player_id, team_id, model_id, rates, event_ids, spec)
        for spec in PROP_LINES]
    if len(rows) != LINES_PER_SKATER:
        raise RuntimeError("Skater prop expansion did not yield 7 lines")
    return rows


def write_player_predictions(
        rows: Iterable[PlayerPredictionRow],
        conn: Any | None = None,
        *,
        match_id: int | None = None,
        model_id: int | None = None,
        dressed_player_ids: Mapping[int, Collection[int]] | None = None
) -> int:
    """Upsert rows on ``(match, player, model, event, line)``.

    ``dressed_player_ids`` maps a team to the players still in the
    stage lineup. Skaters of that team who are absent are deleted
    before the upsert, in the same transaction. A team missing from
    the map is left untouched.
    """
    prepared = [_bound_row(row) for row in rows]
    scope = _prediction_scope(prepared, match_id, model_id)
    if not prepared and not dressed_player_ids:
        return 0
    context = nullcontext(conn) if conn is not None else get_db_connection()
    with context as connection:
        cursor = connection.cursor()
        try:
            if dressed_player_ids and scope is not None:
                # Upsert nie rusza zawodnika, który wypadł ze składu etapu.
                _delete_absent_players(
                    cursor, scope[0], scope[1], dressed_player_ids)
            if prepared:
                cursor.executemany(_UPSERT_SQL, prepared)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    return len(prepared)


def _prediction_scope(
        prepared: list[tuple[object, ...]],
        match_id: int | None,
        model_id: int | None) -> tuple[int, int] | None:
    """Return the match and model the delete should cover."""
    if prepared:
        row_match = int(prepared[0][0])
        row_model = int(prepared[0][3])
        if match_id is not None and int(match_id) != row_match:
            raise ValueError(
                "player prediction rows do not match match_id")
        if model_id is not None and int(model_id) != row_model:
            raise ValueError(
                "player prediction rows do not match model_id")
        return row_match, row_model
    if match_id is None or model_id is None:
        return None
    return int(match_id), int(model_id)


def _delete_absent_players(
        cursor: Any,
        match_id: int,
        model_id: int,
        dressed_player_ids: Mapping[int, Collection[int]]) -> None:
    """Delete this match's rows for dressed teams outside the lineup."""
    for team_id in sorted(dressed_player_ids):
        player_ids = sorted({
            int(player_id) for player_id in dressed_player_ids[team_id]})
        if not player_ids:
            cursor.execute(
                _DELETE_TEAM_SQL, (match_id, model_id, int(team_id)))
            continue
        placeholders = ", ".join(["%s"] * len(player_ids))
        sql = _DELETE_ABSENT_SQL.format(placeholders=placeholders)
        cursor.execute(sql, (
            match_id, model_id, int(team_id), *player_ids))


def _line_row(
        match_id: int,
        player_id: int,
        team_id: int,
        model_id: int,
        rates: Mapping[str, float],
        event_ids: Mapping[str, int],
        spec: tuple[str, float, str]) -> PlayerPredictionRow:
    target, line, event_key = spec
    if target not in rates:
        raise KeyError(f"Missing prop rate '{target}'")
    if event_key not in event_ids:
        raise KeyError(f"Missing prop event '{event_key}'")
    rate = float(rates[target])
    return PlayerPredictionRow(
        match_id=int(match_id),
        player_id=int(player_id),
        team_id=int(team_id),
        model_id=int(model_id),
        event_id=int(event_ids[event_key]),
        line=float(line),
        expected_value=rate,
        probability=poisson_over_probability(rate, float(line)))


def _bound_row(row: PlayerPredictionRow) -> tuple[object, ...]:
    expected = float(row.expected_value)
    probability = float(row.probability)
    if not math.isfinite(expected) or expected < 0.0:
        raise ValueError("expected_value must be finite and non-negative")
    if (
            not math.isfinite(probability)
            or probability < 0.0
            or probability > 100.0):
        raise ValueError("probability must be between 0 and 100")
    return (
        int(row.match_id),
        int(row.player_id),
        int(row.team_id),
        int(row.model_id),
        int(row.event_id),
        float(row.line),
        expected,
        probability)
