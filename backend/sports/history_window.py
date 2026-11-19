"""Recent-match windows shared by the team and player history strips."""

from __future__ import annotations

from typing import Any


HISTORY_WINDOWS = (5, 10)
DEFAULT_HISTORY_WINDOW = 10


def history_hit_rate(history: dict[str, Any] | None) -> float | None:
    """Return combined hits divided by combined played matches.

    Two strips add both counts, so 3 of 10 and 9 of 10 rank as
    12 of 20. A strip that played nothing adds nothing. When the
    denominator is zero the rate is unset.
    """
    if history is None:
        return None
    hits, played = _hit_counts(history)
    if played == 0:
        return None
    return hits / played


def page_by_history_rate(
        rows: list[dict[str, Any]],
        sort_order: str,
        page: int,
        page_size: int,
        id_key: str) -> list[dict[str, Any]]:
    """Return one page ordered by the combined hit rate.

    Descending puts the higher rate first. Rows with no rate stay
    last in either direction. Equal rates keep the smaller id first.
    """
    descending = sort_order != "asc"

    def sort_key(row: dict[str, Any]) -> tuple[int, float, int]:
        rate = history_hit_rate(row.get("history"))
        # Brak mianownika nie jest zerem, więc wiersz zostaje na końcu.
        if rate is None:
            return (1, 0.0, int(row[id_key]))
        signed = -rate if descending else rate
        return (0, signed, int(row[id_key]))

    ordered = sorted(rows, key=sort_key)
    start = max(page - 1, 0) * page_size
    return ordered[start:start + page_size]


def _hit_counts(history: dict[str, Any]) -> tuple[int, int]:
    """Sum hits and played. One strip stores the counts on itself."""
    series = history.get("series")
    if series is None:
        return int(history["hits"]), int(history["played"])
    hits = 0
    played = 0
    for item in series:
        hits += int(item["hits"])
        played += int(item["played"])
    return hits, played
