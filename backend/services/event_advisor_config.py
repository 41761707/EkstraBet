"""Thresholds and weights for the event advisor."""

from __future__ import annotations

from dataclasses import dataclass, field


# Świeży słownik na instancję: frozen nie zamraża zawartości.
def _default_tier_caps() -> dict[str, int]:
    return {"S": 3, "A": 4, "B": 4}


@dataclass(frozen=True)
class AdvisorConfig:
    """Caps, blend weights and tier cuts for event suggestions.

    The numbers are the scoring contract. A user's taste moves when
    new coupons land in the history window, not by a per-user model.
    """

    history_days: int = 180
    horizon_days: int = 7
    cold_start_min_events: int = 8
    max_scored_candidates: int = 400
    w_league: float = 0.65
    w_event: float = 0.35
    slip_league_floor: float = 0.85
    odds_band_floor: float = 0.30
    computer_bet: float = 1.0
    computer_lean: float = 0.65
    computer_fair: float = 0.40
    computer_weak: float = 0.15
    lean_min_probability: float = 0.45
    lean_max_abs_edge_pp: float = 12.0
    tier_s_min: float = 0.72
    tier_a_min: float = 0.55
    tier_b_min: float = 0.40
    tier_s_min_computer: float = 0.65
    tier_s_min_odds_fit: float = 0.50
    tier_caps: dict[str, int] = field(
        default_factory=_default_tier_caps)
    reason_limit: int = 3
