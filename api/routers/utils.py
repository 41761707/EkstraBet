"""Shared helpers for API routers."""

from __future__ import annotations

from fastapi import HTTPException


def parse_id_list(raw_value: str | None) -> list[int] | None:
    """Parse comma-separated positive integer IDs.

    Returns ``None`` when ``raw_value`` is ``None`` or empty after stripping
    blank entries. Raises ``HTTPException`` (400) when the value cannot be
    parsed as integers or contains non-positive entries.
    """
    if raw_value is None:
        return None
    try:
        parsed = [
            int(item.strip())
            for item in raw_value.split(",")
            if item.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid ID list format. Use e.g. '1,2,3'") from exc
    if not parsed:
        return None
    if any(item < 1 for item in parsed):
        raise HTTPException(
            status_code=400,
            detail="All IDs must be positive integers")
    return parsed
