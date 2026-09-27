"""Catalog of football events that can be settled from match boxscore."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


LineStat = Literal["goals", "corners", "fouls", "yellows", "offsides"]
LineSide = Literal["total", "home", "away"]
LineComparator = Literal["over", "under"]

# Parent event 173 i player/hockey props 181-197 nie mają boxscore meczu.
UNSUPPORTED_TIPSTER_EVENT_IDS = frozenset({173, *range(181, 198)})
# Rynki rozliczane po id, bez parsera nazw linii (1X2, 1X/X2, BTTS, AH, exact).
EXPLICIT_SETTLEABLE_EVENT_IDS = frozenset({
    1, 2, 3, 4, 5, 6, 8, 12, 172, 49, 50, 51, 52
}) | frozenset(range(174, 181)) | frozenset(range(198, 234))

_LINE_MARKET_PATTERN = re.compile(
    r"^(Gospodarz |Gość )?(Powyżej|Poniżej|powyżej|poniżej) "
    r"(\d+\.5) (.+)$")
_STAT_BY_TAIL = {
    "gola": "goals",
    "goli": "goals",
    "rożnych": "corners",
    "fauli": "fouls",
    "żółtej kartki": "yellows",
    "spalonych": "offsides"
}
_OVER_WORDS = frozenset({"Powyżej", "powyżej"})
_HOME_PREFIX = "Gospodarz "
_AWAY_PREFIX = "Gość "


@dataclass(frozen=True)
class LineMarketRule:
    """Over/under rule parsed from a Polish catalog event name."""

    stat: LineStat
    side: LineSide
    comparator: LineComparator
    line: float


@dataclass(frozen=True)
class MatchBoxscore:
    """Finished-match statistics used by tipster-leg settlement."""

    result: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_ck: int | None = None
    away_ck: int | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_yc: int | None = None
    away_yc: int | None = None
    home_rc: int | None = None
    away_rc: int | None = None
    home_off: int | None = None
    away_off: int | None = None


def parse_line_market(event_name: str) -> LineMarketRule | None:
    """Parse a full-match over/under catalog name, or return None."""
    match = _LINE_MARKET_PATTERN.fullmatch(event_name.strip())
    if match is None:
        return None
    prefix, word, line_token, tail = match.groups()
    stat = _STAT_BY_TAIL.get(tail)
    if stat is None:
        return None
    side: LineSide = "total"
    if prefix == _HOME_PREFIX:
        side = "home"
    elif prefix == _AWAY_PREFIX:
        side = "away"
    comparator: LineComparator = "over" if word in _OVER_WORDS else "under"
    return LineMarketRule(
        stat=stat,
        side=side,
        comparator=comparator,
        line=float(line_token))


def is_settleable_event(event_id: int, event_name: str) -> bool:
    """Return True when a complete boxscore can settle this catalog event."""
    if event_id in UNSUPPORTED_TIPSTER_EVENT_IDS:
        return False
    if event_id in EXPLICIT_SETTLEABLE_EVENT_IDS:
        return True
    return parse_line_market(event_name) is not None
