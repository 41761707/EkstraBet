"""Hit, line name and settlement rules for hockey player props."""

from __future__ import annotations

from typing import Literal, NamedTuple


PropStatColumn = Literal["sog", "points", "assists", "goals"]
PropSide = Literal["over", "under"]
SettlementStatus = Literal["pending", "won", "lost"]

HISTORY_WINDOWS = (5, 10)
DEFAULT_HISTORY_WINDOW = 10
LINE_MATCH_EPSILON = 0.001

_LINE_TOKEN = " X "


class PropStatSpec(NamedTuple):
    """Stat column and side for one player-prop event."""

    event_id: int
    column: PropStatColumn
    side: PropSide


# Under nie ma predykcji, więc 191, 193 i 195 nie wchodzą do słownika.
PROP_STAT_SPECS: dict[int, PropStatSpec] = {
    190: PropStatSpec(190, "sog", "over"),
    192: PropStatSpec(192, "points", "over"),
    194: PropStatSpec(194, "assists", "over"),
    196: PropStatSpec(196, "goals", "over")}

OVER_PROP_EVENT_IDS = tuple(PROP_STAT_SPECS)


def prop_stat_spec(event_id: int) -> PropStatSpec | None:
    """Return the catalog rule for an event, or None when unknown."""
    return PROP_STAT_SPECS.get(event_id)


def format_prop_event_name(event_name: str, line: float) -> str:
    """Replace the first `` X `` token with the numeric line.

    ``2.5`` stays ``2.5``. A name without the token is unchanged.
    """
    return event_name.replace(_LINE_TOKEN, f" {line:g} ", 1)


def is_prop_hit(value: int, line: float, side: PropSide) -> bool:
    """Return whether the stat clears the line. Equality is a miss."""
    if side == "over":
        return value > line
    return value < line


def settle_prop(
        value: int | None,
        line: float,
        side: PropSide) -> SettlementStatus:
    """Settle one prop, or pending when the match stat is missing."""
    if value is None:
        return "pending"
    if is_prop_hit(value, line, side):
        return "won"
    return "lost"


def settlement_case_sql(stats_alias: str, line_alias: str) -> str:
    """Build a CASE from the catalog.

    Aliases are caller constants such as ``hs`` and ``ppl``, not
    request data. Each event maps a missing stat to pending, a hit
    to won and every other value to lost.
    """
    branches: list[str] = []
    for spec in PROP_STAT_SPECS.values():
        branches.extend(_event_case_branches(
            spec, stats_alias, line_alias))
    joined = " ".join(branches)
    return f"CASE {joined} ELSE 'pending' END"


def _event_case_branches(
        spec: PropStatSpec,
        stats_alias: str,
        line_alias: str) -> list[str]:
    column = f"{stats_alias}.{spec.column}"
    line_ref = f"{line_alias}.line"
    event_match = f"{line_alias}.event_id = {spec.event_id}"
    comparator = ">" if spec.side == "over" else "<"
    # NULL przed porównaniem: w SQL nierówność z NULL nie jest fałszem.
    return [
        f"WHEN {event_match} AND {column} IS NULL THEN 'pending'",
        (
            f"WHEN {event_match} AND {column} {comparator} "
            f"{line_ref} THEN 'won'"),
        f"WHEN {event_match} THEN 'lost'"]
