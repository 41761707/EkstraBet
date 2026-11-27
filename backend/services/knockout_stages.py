"""Map a match round number onto a knockout stage."""

from __future__ import annotations

from dataclasses import dataclass


FAMILY_CUP = "cup"
FAMILY_RELEGATION = "relegation"
ROLE_TIE = "tie"
ROLE_THIRD_PLACE = "third_place"

# Sloty 900-966 kodują fazę i mecz serii. 970-976 kodują samą fazę.
_SERIES_LENGTH = 7
_CUP_SERIES_BANDS: tuple[tuple[int, int], ...] = (
    (900, 64),
    (910, 32),
    (920, 16),
    (930, 8),
    (940, 4),
    (950, 2),
    (960, 1))
_SINGLE_CUP_DEPTH: dict[int, int] = {
    976: 64,
    975: 32,
    974: 16,
    973: 8,
    972: 4,
    971: 2,
    970: 1}
# 969 nie jest kolumną drzewa, więc nie dostaje głębokości.
_THIRD_PLACE_ROUND = 969
_RELEGATION_PAIR_LENGTH = 2
_RELEGATION_BANDS: tuple[tuple[int, int], ...] = (
    (1001, 4),
    (1003, 2),
    (1005, 1))
_STAGE_LABELS: dict[int, str] = {
    64: "1/64 finału",
    32: "1/32 finału",
    16: "1/16 finału",
    8: "1/8 finału",
    4: "Ćwierćfinał",
    2: "Półfinał",
    1: "Finał"}


@dataclass(frozen=True)
class RoundClass:
    """Family, depth, series leg and role of one round number.

    ``depth`` is None only for the third-place match. That match is
    not a column of the tree.
    """

    family: str
    depth: int | None
    leg_index: int | None
    role: str


def classify_round(round_number: int) -> RoundClass | None:
    """Return the knockout class of a round number, or None.

    A number outside the cup and relegation tables stays out of the
    bracket and remains an ordinary round button.
    """
    readers = (
        _cup_series,
        _single_cup,
        _third_place,
        _relegation)
    for reader in readers:
        classified = reader(round_number)
        if classified is not None:
            return classified
    return None


def stage_label(depth: int) -> str:
    """Polish column title for a knockout depth.

    Depths 64, 32, 16 and 8 use a fraction. Depths 4, 2 and 1 use
    quarter-final, semi-final and final. Third place is not a depth.
    """
    return _STAGE_LABELS[depth]


def _cup_series(round_number: int) -> RoundClass | None:
    """Map a seven-game slot such as 930-936 onto one phase."""
    for base, depth in _CUP_SERIES_BANDS:
        offset = round_number - base
        if 0 <= offset < _SERIES_LENGTH:
            return RoundClass(
                FAMILY_CUP,
                depth,
                offset + 1,
                ROLE_TIE)
    return None


def _single_cup(round_number: int) -> RoundClass | None:
    """Map one number per phase, such as 974, onto a cup tie."""
    depth = _SINGLE_CUP_DEPTH.get(round_number)
    if depth is None:
        return None
    return RoundClass(FAMILY_CUP, depth, None, ROLE_TIE)


def _third_place(round_number: int) -> RoundClass | None:
    """Map round 969 onto the third-place role without a depth."""
    if round_number != _THIRD_PLACE_ROUND:
        return None
    return RoundClass(
        FAMILY_CUP,
        None,
        None,
        ROLE_THIRD_PLACE)


def _relegation(round_number: int) -> RoundClass | None:
    """Map a two-leg relegation band onto depth and leg."""
    for base, depth in _RELEGATION_BANDS:
        offset = round_number - base
        if 0 <= offset < _RELEGATION_PAIR_LENGTH:
            return RoundClass(
                FAMILY_RELEGATION,
                depth,
                offset + 1,
                ROLE_TIE)
    return None
