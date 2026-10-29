"""Weights and hard limits for the coupon-agent selector."""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import REPO_ROOT


# Sufit fazy testowej: najwyżej 4 zdarzenia i iloczyn kursów 5, nie gonić
# longshota. Kara 0.10 (zamiast 0.05) odcina słabe zdarzenie, które mieści
# się w suficie, ale prawie nic nie wnosi. Dwa kursy 2.0 (iloczyn 4)
# nadal mogą wejść razem. Dwa kursy 3.0 (iloczyn 9) nie wejdą.


@dataclass(frozen=True)
class SelectorConfig:
    """Limits and weights for one pass of the coupon selector.

    ``max_legs`` is the hard cap on legs. ``max_combined_odds`` is a
    hard ceiling on the product of leg prices. ``leg_penalty`` is
    subtracted once per leg after the first from the sum of leg scores.
    """

    max_legs: int = 4
    min_legs: int = 1
    max_candidates: int = 200
    beam_width: int = 500
    w_confidence: float = 1.0
    w_disagreement: float = 1.5
    w_longshot: float = 0.75
    min_probability: float = 0.35
    max_abs_edge_pp: float = 15.0
    stake_units: float = 1.0
    max_combined_odds: float = 5.0
    leg_penalty: float = 0.10


# Jeden kupon na dobę i na agenta. Podniesienie stałej nie zdejmuje
# blokady tego samego zbioru (match_id, event_id) w tej dobie.
MAX_COUPONS_PER_DAY = 1


@dataclass(frozen=True)
class AgentSpec:
    """One system username and an optional selector override.

    ``selector`` replaces the default weights and stake. ``None`` keeps
    ``SelectorConfig`` defaults, including ``stake_units`` of 1.
    """

    username: str
    selector: SelectorConfig | None = None


# Seed EB-11. Kolejny agent to nowy users + bankroll + wpis tutaj.
AGENTS: list[AgentSpec] = [
    AgentSpec("agent-kuponowy")]

# Katalog EB-18. Bramka jest w strategy JSON (Brier, reliability, ROI).
# Brak katalogu albo raport poza bramką zostawia pulę predykcja–kurs.
BETTING_ARTIFACT_DIR = (
    REPO_ROOT / "models" / "artifacts" / "dev"
    / "football_betting_meta_v1")
BETTING_STRATEGY_PATH = (
    REPO_ROOT / "models" / "configs" / "prediction"
    / "football_betting_strategy_v1.json")
