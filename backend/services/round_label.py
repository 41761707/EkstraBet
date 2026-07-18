"""Helpers for mapping match round numbers to display labels."""

from __future__ import annotations

SPECIAL_ROUND_THRESHOLD = 100


def resolve_round_label(
    round_number: int | None,
    special_rounds: dict[int, str]) -> str | None:
    """Return user-facing round label, resolving special rounds by ID."""
    if round_number is None:
        return None
    if round_number in special_rounds:
        return special_rounds[round_number]
    if round_number > SPECIAL_ROUND_THRESHOLD:
        return str(round_number)
    return str(round_number)
