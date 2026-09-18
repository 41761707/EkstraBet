"""Aggregate championship, top-N and bottom-N outcome probabilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutcomeProbabilities:
    """Marginal probabilities for champion, top slice and bottom slice."""

    champion: float
    top: float | None
    bot: float | None


def sum_position_slice(
        probabilities: list[float],
        start: int,
        end: int) -> float:
    """Sum probabilities[start:end]; empty or out of range is 0.0."""
    # ujemne indeksy w Pythonie liczą od końca — tu oznaczają brak zakresu
    if start < 0 or end < 0 or start >= end:
        return 0.0
    return float(sum(probabilities[start:end]))


def outcome_probabilities(
        position_probabilities: list[float],
        top_slots: int,
        bot_slots: int) -> OutcomeProbabilities:
    """Return champion, top-N and bottom-N probabilities.

    Index 0 is first place. Top includes the champion. Zero slots
    yield None for that slice rather than 0.0.
    """
    n = len(position_probabilities)
    # mistrz zawsze z 1. miejsca, niezależnie od progów ligi
    champion = sum_position_slice(position_probabilities, 0, 1)
    top_n = min(max(top_slots, 0), n)
    bot_n = min(max(bot_slots, 0), n)
    top = None
    if top_n > 0:
        top = sum_position_slice(position_probabilities, 0, top_n)
    bot = None
    if bot_n > 0:
        bot = sum_position_slice(position_probabilities, n - bot_n, n)
    return OutcomeProbabilities(champion=champion, top=top, bot=bot)
