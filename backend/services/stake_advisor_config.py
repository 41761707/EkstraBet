"""Weights and hard limits for the stake advisor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisorWeights:
    """Blend weights, Kelly fraction and stake caps.

    ``agent_boost`` is added after the blend when a system agent has
    played the same event. ``kelly_fraction`` scales full Kelly.
    ``max_bankroll_pct`` caps the stake as a share of the caller's
    basis. ``max_units`` caps it in unit sizes.
    """

    w_model: float = 0.50
    w_user: float = 0.35
    w_implied: float = 0.15
    agent_boost: float = 0.03
    kelly_fraction: float = 0.25
    max_bankroll_pct: float = 0.10
    max_units: float = 5.0


# Okno flagi agenta. Otwarty kupon liczy się także poza tym oknem.
AGENT_LOOKBACK_DAYS = 14
