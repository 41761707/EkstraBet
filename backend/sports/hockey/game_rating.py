"""Hockey game ratings: weights, counters and play-by-play credits."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd


PRODUCTION_GOAL = 1.00
PRODUCTION_ASSIST = 1.00
EMPTY_NET_GOAL = -0.30
UNCONVERTED_SHOT = 0.05
TEAMMATE_GOAL = 0.20
FACEOFF_DIFF = 0.02
GOAL_AGAINST = -0.35
MINOR_PENALTY = -0.15
MAJOR_PENALTY = -0.30
BLOCK_ABOVE_AVERAGE = 0.04
DEFAULT_SAVE_RATE = 0.907
MIN_SEASON_SHOTS_AGAINST = 100

BLOCK_AVERAGE_DEFENSE = 1.44
BLOCK_AVERAGE_CENTER = 0.57
BLOCK_AVERAGE_LEFT_WING = 0.45
BLOCK_AVERAGE_RIGHT_WING = 0.46
BLOCK_AVERAGE_FORWARD = 0.49

GOAL_EVENT_ID = 181
MINOR_PENALTY_EVENT_ID = 183
MAJOR_PENALTY_EVENT_ID = 185


@dataclass(frozen=True)
class SkaterCounts:
    """Ready-made counters. Even-strength points arrive already counted."""

    goals: int
    assists: int
    es_points: int
    empty_net_goals: int
    shots_on_goal: int
    plus_minus: int | None
    minor_penalties: int
    major_penalties: int
    blocked: int
    block_average: float
    faceoffs_taken: int
    faceoffs_won: int


@dataclass(frozen=True)
class RatingParts:
    """Nine rating leaves, each already rounded to one decimal."""

    production: Decimal
    empty_net: Decimal
    shots: Decimal
    teammate_goals: Decimal
    faceoffs: Decimal
    goals_against: Decimal
    penalties: Decimal
    blocks: Decimal
    goaltending: Decimal

    @property
    def offense(self) -> Decimal:
        """Sum the offensive leaves without rounding again."""
        return (self.production
            + self.empty_net
            + self.shots
            + self.teammate_goals
            + self.faceoffs)

    @property
    def defense(self) -> Decimal:
        """Sum the defensive leaves without rounding again."""
        return (self.goals_against
            + self.penalties
            + self.blocks
            + self.goaltending)

    @property
    def total(self) -> Decimal:
        """Sum offense and defense without rounding again."""
        return self.offense + self.defense


def _as_decimal(value: float) -> Decimal:
    """Use the decimal text of a float, so 0.15 stays 0.15."""
    return Decimal(str(value))


def _round_part(raw: Decimal) -> Decimal:
    """Round one rating leaf to a single decimal place."""
    # Iloczyn float psuje -1.05 i -0.45, więc surowiec jest Decimal.
    rounded = raw.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    # Ujemna waga razy zero zostawia -0.0, a protokół pokazuje 0.0.
    if rounded.is_zero():
        return Decimal("0.0")
    return rounded


def _on_ice_margin(counts: SkaterCounts) -> int | None:
    """Return plus/minus minus even-strength points, or None."""
    if counts.plus_minus is None:
        return None
    return counts.plus_minus - counts.es_points


def rate_skater(counts: SkaterCounts) -> RatingParts:
    """Turn ready-made skater counters into nine rounded parts.

    Goaltending stays zero. A missing plus/minus stays missing, so
    even-strength points are not treated as goals against.
    """
    margin = _on_ice_margin(counts)
    if margin is None:
        teammate_raw = Decimal("0")
        against_raw = Decimal("0")
    else:
        teammate_raw = _as_decimal(TEAMMATE_GOAL) * max(0, margin)
        against_raw = _as_decimal(GOAL_AGAINST) * max(0, -margin)
    faceoff_margin = (counts.faceoffs_won
        - (counts.faceoffs_taken - counts.faceoffs_won))
    unconverted_shots = max(0, counts.shots_on_goal - counts.goals)
    block_margin = counts.blocked - _as_decimal(counts.block_average)
    return RatingParts(
        production=_round_part(
            _as_decimal(PRODUCTION_GOAL) * counts.goals
            + _as_decimal(PRODUCTION_ASSIST) * counts.assists),
        empty_net=_round_part(
            _as_decimal(EMPTY_NET_GOAL) * counts.empty_net_goals),
        shots=_round_part(
            _as_decimal(UNCONVERTED_SHOT) * unconverted_shots),
        teammate_goals=_round_part(teammate_raw),
        faceoffs=_round_part(_as_decimal(FACEOFF_DIFF) * faceoff_margin),
        goals_against=_round_part(against_raw),
        penalties=_round_part(
            _as_decimal(MINOR_PENALTY) * counts.minor_penalties
            + _as_decimal(MAJOR_PENALTY) * counts.major_penalties),
        blocks=_round_part(_as_decimal(BLOCK_ABOVE_AVERAGE) * block_margin),
        goaltending=_round_part(Decimal("0")))


def rate_goalie(
    shots_against: int | None,
    shots_saved: int | None,
    save_rate: float) -> float:
    """Score saves above the season rate, rounded to one decimal.

    A missing or zero shot total scores 0.0. Missing saves count
    as zero.
    """
    if shots_against is None or shots_against == 0:
        return 0.0
    saved = 0 if shots_saved is None else shots_saved
    # Iloczyn float psuje 0.907, więc surowiec jest Decimal.
    expected_saves = _as_decimal(save_rate) * shots_against
    raw = Decimal(saved) - expected_saves
    return float(_round_part(raw))


@dataclass(frozen=True)
class EventCredits:
    """Even-strength points, empty-net goals and penalty counts."""

    es_points: int
    empty_net_goals: int
    minor_penalties: int
    major_penalties: int


@dataclass
class _CreditTotals:
    """Mutable counters while one match is attributed."""

    es_points: int = 0
    empty_net_goals: int = 0
    minor_penalties: int = 0
    major_penalties: int = 0

    def as_credits(self) -> EventCredits:
        """Return the frozen credit row for this player."""
        return EventCredits(
            es_points=self.es_points,
            empty_net_goals=self.empty_net_goals,
            minor_penalties=self.minor_penalties,
            major_penalties=self.major_penalties)


@dataclass
class _PlayerIndex:
    """Names and protocol points indexed from the player frame."""

    totals: dict[int, _CreditTotals]
    names: dict[tuple[int, str], list[int]]
    box_points: dict[int, int]


def _is_missing(value: object) -> bool:
    """Return True for None and pandas nulls."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _optional_int(value: object) -> int | None:
    """Return an int, or None when the cell is empty."""
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _non_negative_int(value: object) -> int:
    """Treat a missing or negative counter as zero."""
    number = _optional_int(value)
    if number is None or number < 0:
        return 0
    return number


def _plain_text(value: object) -> str | None:
    """Return stripped text, or None when the cell is empty."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _is_flag_set(value: object) -> bool:
    """Return True only when a play-by-play flag equals 1."""
    return _optional_int(value) == 1


def normalize(text: str) -> str:
    """Fold a name so a goal description matches a common name.

    Diacritics are removed and whitespace is collapsed, so
    ``Stützle T.`` and ``Stutzle T.`` compare equal.
    """
    # NFKD rozbija ü na u i znak łączący, którego opis bramki nie ma.
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in decomposed
        if unicodedata.category(char) != "Mn")
    return " ".join(without_marks.casefold().split())


def _remember_name(
    names: dict[tuple[int, str], list[int]],
    row: pd.Series,
    player_id: int) -> None:
    """Index one player under the team and the folded common name."""
    team_id = _optional_int(row.get("team_id"))
    # player_name to players.common_name po aliasie z odczytu meczu.
    player_name = _plain_text(row.get("player_name"))
    if team_id is None or player_name is None:
        return
    key = (team_id, normalize(player_name))
    found = names.setdefault(key, [])
    if player_id not in found:
        found.append(player_id)


def _index_players(players: pd.DataFrame) -> _PlayerIndex:
    """Index names and protocol points for every player row."""
    totals: dict[int, _CreditTotals] = {}
    names: dict[tuple[int, str], list[int]] = {}
    box_points: dict[int, int] = {}
    if not players.empty:
        for _, row in players.iterrows():
            player_id = _optional_int(row.get("player_id"))
            if player_id is None:
                continue
            totals.setdefault(player_id, _CreditTotals())
            if player_id not in box_points:
                box_points[player_id] = (
                    _non_negative_int(row.get("goals"))
                    + _non_negative_int(row.get("assists")))
            _remember_name(names, row, player_id)
    return _PlayerIndex(
        totals=totals,
        names=names,
        box_points=box_points)


def _assist_pieces(description: object) -> list[str]:
    """Split assist names from the head of a goal description."""
    # Ogon po przecinku to adnotacja, nie część nazwiska.
    text = _plain_text(description)
    if text is None:
        return []
    pieces = []
    for piece in text.split(",", 1)[0].split(" + "):
        cleaned = piece.strip()
        if cleaned:
            pieces.append(cleaned)
    return pieces


def _matching_assist(
    names: dict[tuple[int, str], list[int]],
    team_id: int | None,
    piece: str) -> int | None:
    """Return the only teammate with this name, or None."""
    # Zero albo kilka dopasowań: nie zgadujemy najbliższego nazwiska.
    if team_id is None:
        return None
    found = names.get((team_id, normalize(piece)), [])
    if len(found) != 1:
        return None
    return found[0]


def _apply_goal(
    totals: dict[int, _CreditTotals],
    names: dict[tuple[int, str], list[int]],
    row: pd.Series) -> None:
    """Credit the scorer and even-strength assists of one goal."""
    scorer_id = _optional_int(row.get("player_id"))
    team_id = _optional_int(row.get("team_id"))
    # Gol w przewadze nie wchodzi do plus/minus.
    even_strength = not _is_flag_set(row.get("pp_flag"))
    if scorer_id is not None:
        credit = totals.setdefault(scorer_id, _CreditTotals())
        if _is_flag_set(row.get("en_flag")):
            credit.empty_net_goals += 1
        if even_strength:
            credit.es_points += 1
    if not even_strength:
        return
    seen: set[int] = set()
    for piece in _assist_pieces(row.get("description")):
        assist_id = _matching_assist(names, team_id, piece)
        if assist_id is None or assist_id in seen:
            continue
        seen.add(assist_id)
        credit = totals.setdefault(assist_id, _CreditTotals())
        credit.es_points += 1


def _apply_penalty(
    totals: dict[int, _CreditTotals],
    row: pd.Series,
    major: bool) -> None:
    """Count one minor or major penalty for the event player."""
    player_id = _optional_int(row.get("player_id"))
    if player_id is None:
        return
    credit = totals.setdefault(player_id, _CreditTotals())
    if major:
        credit.major_penalties += 1
        return
    credit.minor_penalties += 1


def _apply_events(
    events: pd.DataFrame,
    totals: dict[int, _CreditTotals],
    names: dict[tuple[int, str], list[int]]) -> int:
    """Apply goals and penalties. Return how many goals were seen."""
    # 184 oraz kary 186-189 nie wchodzą do licznika.
    goal_count = 0
    if events.empty:
        return 0
    for _, row in events.iterrows():
        event_id = _optional_int(row.get("event_id"))
        if event_id == GOAL_EVENT_ID:
            goal_count += 1
            _apply_goal(totals, names, row)
        elif event_id == MINOR_PENALTY_EVENT_ID:
            _apply_penalty(totals, row, major=False)
        elif event_id == MAJOR_PENALTY_EVENT_ID:
            _apply_penalty(totals, row, major=True)
    return goal_count


def _apply_box_score_fallback(
    totals: dict[int, _CreditTotals],
    box_points: dict[int, int]) -> None:
    """Use protocol points when the match has no goal events."""
    for player_id, points in box_points.items():
        credit = totals.setdefault(player_id, _CreditTotals())
        credit.es_points = points
        credit.empty_net_goals = 0


def _freeze(
    totals: dict[int, _CreditTotals]) -> dict[int, EventCredits]:
    """Copy mutable totals into the public credit rows."""
    credited = {}
    for player_id, credit in totals.items():
        credited[player_id] = credit.as_credits()
    return credited


def attribute_events(
    players: pd.DataFrame,
    events: pd.DataFrame) -> dict[int, EventCredits]:
    """Credit even-strength points, empty-net goals and penalties.

    ``player_name`` holds ``players.common_name``. With no goal
    events, even-strength points fall back to goals plus assists
    for every player row. One goal event disables that fallback
    for the whole match. Penalties are counted either way.
    """
    indexed = _index_players(players)
    goal_count = _apply_events(events, indexed.totals, indexed.names)
    if goal_count == 0:
        _apply_box_score_fallback(indexed.totals, indexed.box_points)
    return _freeze(indexed.totals)
