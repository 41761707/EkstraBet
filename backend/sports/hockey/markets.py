"""Hockey bet-market catalog settled including overtime."""

from __future__ import annotations

from typing import Literal, NamedTuple


MarketStat = Literal["goals", "margin"]
MarketSide = Literal["total", "home", "away"]
MarketComparator = Literal["over", "under"]


class HockeyMarketRule(NamedTuple):
    """One event mapped to ``(stat, side, comparator, line)``."""

    stat: MarketStat
    side: MarketSide
    comparator: MarketComparator
    line: float


# Moneyline to margin > 0, żeby każdy event miał ten sam kształt reguły.
# Po dogrywce albo karnych remis już nie występuje.
HOCKEY_MARKET_RULES: dict[int, HockeyMarketRule] = {
    234: HockeyMarketRule("margin", "home", "over", 0.0),
    235: HockeyMarketRule("margin", "away", "over", 0.0),
    236: HockeyMarketRule("goals", "total", "over", 5.5),
    237: HockeyMarketRule("goals", "total", "under", 5.5),
    238: HockeyMarketRule("goals", "total", "over", 6.5),
    239: HockeyMarketRule("goals", "total", "under", 6.5),
    240: HockeyMarketRule("margin", "home", "over", 1.5),
    241: HockeyMarketRule("margin", "home", "over", -1.5),
    242: HockeyMarketRule("margin", "away", "over", 1.5),
    243: HockeyMarketRule("margin", "away", "over", -1.5),
    244: HockeyMarketRule("goals", "home", "over", 2.5),
    245: HockeyMarketRule("goals", "home", "under", 2.5),
    246: HockeyMarketRule("goals", "home", "over", 3.5),
    247: HockeyMarketRule("goals", "home", "under", 3.5),
    248: HockeyMarketRule("goals", "away", "over", 2.5),
    249: HockeyMarketRule("goals", "away", "under", 2.5),
    250: HockeyMarketRule("goals", "away", "over", 3.5),
    251: HockeyMarketRule("goals", "away", "under", 3.5)}

HOCKEY_BET_MARKET_EVENT_IDS = frozenset(HOCKEY_MARKET_RULES)
