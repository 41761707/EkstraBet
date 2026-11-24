"""Read-only lookups used by model comparison reports."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from backend.database import get_db_connection


_SEASON_YEARS_QUERY = """
    SELECT id, years AS label
    FROM seasons
    WHERE id IN ({placeholders})
"""

_LEAGUE_NAMES_QUERY = """
    SELECT id, name AS label
    FROM leagues
    WHERE id IN ({placeholders})
"""


def fetch_season_years(season_ids: Sequence[int]) -> dict[int, str]:
    """Return ``seasons.years`` keyed by season id.

    A null label is omitted. The segment helper then marks that
    season as unknown.
    """
    return _labels_by_id(season_ids, _SEASON_YEARS_QUERY)


def fetch_league_names(league_ids: Sequence[int]) -> dict[int, str]:
    """Return ``leagues.name`` keyed by league id.

    A null name is omitted.
    """
    return _labels_by_id(league_ids, _LEAGUE_NAMES_QUERY)


def _labels_by_id(
        raw_ids: Sequence[int],
        query_template: str) -> dict[int, str]:
    ids = _unique_ids(raw_ids)
    if not ids:
        return {}
    query = query_template.format(
        placeholders=", ".join(["%s"] * len(ids)))
    with get_db_connection() as connection:
        frame = pd.read_sql(query, connection, params=tuple(ids))
    return _label_map(frame)


def _label_map(frame: pd.DataFrame) -> dict[int, str]:
    labels: dict[int, str] = {}
    if frame.empty:
        return labels
    for _, row in frame.iterrows():
        if pd.isna(row["id"]) or pd.isna(row["label"]):
            continue
        labels[int(row["id"])] = str(row["label"])
    return labels


def _unique_ids(values: Sequence[int] | np.ndarray) -> list[int]:
    seen: set[int] = set()
    unique: list[int] = []
    for value in _id_values(values):
        number = _plain_int(value)
        if number in seen:
            continue
        seen.add(number)
        unique.append(number)
    return unique


def _id_values(values: Sequence[int] | np.ndarray) -> list[object]:
    # Payload batcha trzyma id sezonu i ligi w tablicy, nie na liście.
    if isinstance(values, np.ndarray):
        if values.ndim != 1:
            raise ValueError("ids must be a sequence of integers")
        return values.tolist()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("ids must be a sequence of integers")
    return list(values)


def _plain_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError("ids must be integers")
    return int(value)
