"""Season-format and per-league slices for model comparison.

The functions are pure. Season labels and league names come from
the caller, so this module does not open a database connection.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


SEASON_FORMAT_SPLIT_YEAR = "split_year"
SEASON_FORMAT_CALENDAR_YEAR = "calendar_year"
SEASON_FORMAT_UNKNOWN = "unknown"


def season_format_segments(
        season_ids: np.ndarray,
        years_by_season: dict[int, str]) -> np.ndarray:
    """Label each match by the season format.

    ``split_year`` when the season label contains ``/``, for example
    ``2026/27`` or ``2026/2027``. Any other label is
    ``calendar_year``. A season id absent from ``years_by_season``
    is ``unknown``. The result keeps the order of ``season_ids``.
    """
    ids = _integer_ids(season_ids, "season_ids")
    labels = [
        _season_label(years_by_season, int(season_id))
        for season_id in ids]
    return np.asarray(labels)


def league_table(
        league_ids: np.ndarray,
        p: np.ndarray,
        outcomes: np.ndarray,
        finals: np.ndarray,
        league_names: dict[int, str]) -> list[dict[str, int | float | str]]:
    """Summarise one binary market per league.

    ``p`` is the probability of the positive class, BTTS yes or Over.
    ``outcomes`` and ``finals`` are 1 for that class and 0 otherwise.
    ``std_p`` is the population standard deviation of ``p``.
    ``level_error`` is ``mean_p - actual``. Rows are ordered by
    league id. A missing name falls back to the id as text, because
    the table is read per league.
    """
    ids = _integer_ids(league_ids, "league_ids")
    probabilities = _vector(p, "p")
    observed = _binary(outcomes, "outcomes", len(ids))
    decisions = _binary(finals, "finals", len(ids))
    if len(probabilities) != len(ids):
        raise ValueError("league rows must have the same length")
    if len(ids) == 0:
        return []
    rows: list[dict[str, int | float | str]] = []
    for league_id in np.unique(ids):
        chosen = ids == league_id
        number = int(league_id)
        mean_p = float(np.mean(probabilities[chosen]))
        actual = float(np.mean(observed[chosen]))
        rows.append({
            "league_id": number,
            "league_name": _league_name(league_names, number),
            "n": int(np.sum(chosen)),
            "mean_p": mean_p,
            "std_p": float(np.std(probabilities[chosen])),
            "share_final_yes": float(np.mean(decisions[chosen])),
            "actual": actual,
            "level_error": mean_p - actual})
    return rows


def weighted_level_error(
        table: Sequence[dict[str, int | float | str]]) -> float:
    """Return the match-weighted mean of absolute level errors."""
    rows = _rows(table)
    if not rows:
        raise ValueError("table must contain at least one league")
    weights = np.array(
        [_row_count(row) for row in rows], dtype=float)
    errors = np.array(
        [abs(_row_float(row, "level_error")) for row in rows],
        dtype=float)
    total = float(np.sum(weights))
    if total <= 0.0:
        raise ValueError("table must contain at least one match")
    return float(np.sum(weights * errors) / total)


def median_within_league_std(
        table: Sequence[dict[str, int | float | str]],
        min_matches: int = 30) -> float:
    """Return the median within-league standard deviation.

    Leagues with fewer than ``min_matches`` matches are left out.
    An even count uses the mean of the two middle values.
    """
    _positive_int(min_matches, "min_matches")
    eligible = [
        _row_float(row, "std_p")
        for row in _rows(table)
        if _row_count(row) >= min_matches]
    if not eligible:
        raise ValueError(
            f"no league has at least {min_matches} matches")
    return float(np.median(np.asarray(eligible, dtype=float)))


def _season_label(
        years_by_season: dict[int, str],
        season_id: int) -> str:
    if season_id not in years_by_season:
        return SEASON_FORMAT_UNKNOWN
    label = years_by_season[season_id]
    if not isinstance(label, str):
        raise ValueError("season years must be strings")
    if "/" in label:
        return SEASON_FORMAT_SPLIT_YEAR
    return SEASON_FORMAT_CALENDAR_YEAR


def _league_name(league_names: dict[int, str], league_id: int) -> str:
    if league_id not in league_names:
        return str(league_id)
    name = league_names[league_id]
    if not isinstance(name, str):
        raise ValueError("league names must be strings")
    if not name:
        return str(league_id)
    return name


def _integer_ids(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if array.size == 0:
        return np.asarray([], dtype=int)
    if array.dtype == np.bool_ or not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} must be integers")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite")
    indexes = array.astype(int)
    if not np.all(indexes == array):
        raise ValueError(f"{name} must be integers")
    return indexes


def _vector(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if array.size and not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite")
    return array


def _binary(values: np.ndarray, name: str, count: int) -> np.ndarray:
    indexes = _integer_ids(values, name)
    if len(indexes) != count:
        raise ValueError(f"{name} must have one value per match")
    if np.any((indexes < 0) | (indexes > 1)):
        raise ValueError(f"{name} must be 0 or 1")
    return indexes


def _rows(
        table: Sequence[dict[str, int | float | str]]
        ) -> list[dict[str, int | float | str]]:
    if isinstance(table, (str, bytes)) or not isinstance(table, Sequence):
        raise ValueError("table must be a sequence of league rows")
    rows = list(table)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("table must be a sequence of league rows")
    return rows


def _row_count(row: dict[str, int | float | str]) -> int:
    number = _row_float(row, "n")
    if number < 0.0 or not math.isclose(number, round(number)):
        raise ValueError("n must be a non-negative integer")
    return int(round(number))


def _row_float(
        row: dict[str, int | float | str],
        key: str) -> float:
    if key not in row:
        raise ValueError(f"league row must include {key}")
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{key} must be finite")
    return number


def _positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
