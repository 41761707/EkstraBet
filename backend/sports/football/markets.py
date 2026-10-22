"""Football event ids grouped into pre-match market families.

Names match ``event_families.name``. The module lists ids only. It does
not settle a match.
"""

from __future__ import annotations


RESULT_EVENT_OUTCOMES = {
    1: "1",
    2: "X",
    3: "2"}
RESULT_EVENT_IDS = frozenset(RESULT_EVENT_OUTCOMES)

BTTS_YES_EVENT_ID = 6
BTTS_NO_EVENT_ID = 172
BTTS_YES_EVENT_IDS = frozenset({BTTS_YES_EVENT_ID})
BTTS_NO_EVENT_IDS = frozenset({BTTS_NO_EVENT_ID})
BTTS_EVENT_IDS = BTTS_YES_EVENT_IDS | BTTS_NO_EVENT_IDS

OVER_25_EVENT_ID = 8
UNDER_25_EVENT_ID = 12
OVER_25_EVENT_IDS = frozenset({OVER_25_EVENT_ID})
UNDER_25_EVENT_IDS = frozenset({UNDER_25_EVENT_ID})
OU_EVENT_IDS = OVER_25_EVENT_IDS | UNDER_25_EVENT_IDS

GOALS_EXACT_TOTAL_EVENTS = {
    174: 0,
    175: 1,
    176: 2,
    177: 3,
    178: 4,
    179: 5}
GOALS_6_PLUS_EVENT_ID = 180
# Etykieta „dokładna liczba goli”. Nie jest wynikiem partycji 0–6+.
EXACT_GOALS_GROUP_EVENT_ID = 173
GOALS_TOTAL_EVENT_IDS = (
    frozenset(GOALS_EXACT_TOTAL_EVENTS)
    | frozenset({GOALS_6_PLUS_EVENT_ID}))
GOALS_FAMILY_EVENT_IDS = (
    GOALS_TOTAL_EVENT_IDS
    | frozenset({EXACT_GOALS_GROUP_EVENT_ID}))

EXACT_SCORE_EVENT_IDS = frozenset(range(198, 234))

BET_MARKET_EVENT_IDS = RESULT_EVENT_IDS | BTTS_EVENT_IDS | OU_EVENT_IDS

# Etykiety cech. 173 należy do GOALS, ale nie domyka overroundu 0–6+.
_FAMILY_EVENTS = (
    ("REZULTAT", RESULT_EVENT_IDS),
    ("BTTS", BTTS_EVENT_IDS),
    ("OU", OU_EVENT_IDS),
    ("GOALS", GOALS_FAMILY_EVENT_IDS),
    ("EXACT", EXACT_SCORE_EVENT_IDS))

# Partycje jednego cennika. Niekompletny rynek nie dostaje de-vig.
DEVIG_MARKETS = (
    ("REZULTAT", RESULT_EVENT_IDS),
    ("BTTS", BTTS_EVENT_IDS),
    ("OU", OU_EVENT_IDS),
    ("GOALS", GOALS_TOTAL_EVENT_IDS),
    ("EXACT", EXACT_SCORE_EVENT_IDS))

_FAMILY_BY_EVENT_ID = {
    event_id: name
    for name, event_ids in _FAMILY_EVENTS
    for event_id in event_ids}


def market_family(event_id: int) -> str | None:
    """Return the family name for an event id, or None when unknown."""
    if isinstance(event_id, bool) or not isinstance(event_id, int):
        return None
    return _FAMILY_BY_EVENT_ID.get(event_id)


def _require_disjoint(
        groups: tuple[frozenset[int], ...],
        label: str) -> None:
    """Reject catalogs that assign one event id to two groups."""
    seen: set[int] = set()
    for event_ids in groups:
        overlap = seen.intersection(event_ids)
        if overlap:
            joined = ", ".join(str(event_id) for event_id in sorted(overlap))
            raise RuntimeError(f"{label} share event ids: {joined}")
        seen.update(event_ids)


_require_disjoint(
    tuple(event_ids for _name, event_ids in _FAMILY_EVENTS),
    "market families")
_require_disjoint(
    tuple(event_ids for _name, event_ids in DEVIG_MARKETS),
    "de-vig markets")
