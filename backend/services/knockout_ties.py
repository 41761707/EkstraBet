"""Group knockout matches that share two teams into one tie."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime

from backend.services.knockout_stages import ROLE_THIRD_PLACE
from backend.services.knockout_stages import RoundClass
from backend.services.knockout_stages import classify_round
from backend.services.knockout_stages import stage_label


THIRD_PLACE_LABEL = "Mecz o 3. miejsce"
# Bez terminu mecz idzie za tymi, które datę mają.
_UNDATED = datetime.max


@dataclass(frozen=True)
class TieMatch:
    """One match that can join a knockout tie.

    ``round_number`` is ``matches.round``. Grouping classifies it
    instead of trusting a caller-supplied family or depth. The leg
    stored on the tie comes from that classification.
    """

    match_id: int
    round_number: int
    leg_index: int | None
    game_date: datetime | None
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    home_team_shortcut: str | None
    away_team_shortcut: str | None
    home_goals: int | None
    away_goals: int | None
    result: str | None
    is_played: bool
    decided_by: str | None = None
    home_extra_time_goals: int | None = None
    away_extra_time_goals: int | None = None
    home_penalty_goals: int | None = None
    away_penalty_goals: int | None = None


@dataclass(frozen=True)
class BracketTie:
    """All matches of one pair in a single knockout phase.

    ``team_ids`` lists the lower team id first. Score, feeders and
    the champion path stay empty until a later step fills them.
    """

    tie_id: str
    family: str
    depth: int | None
    stage_label: str
    matches: list[TieMatch]
    team_ids: tuple[int, ...]
    pending_opponent_label: str | None = None
    seed_position: int | None = None
    is_bye: bool = False
    score_winner_team_id: int | None = None
    advanced_team_id: int | None = None
    aggregate_by_team: dict[int, int] | None = None
    series_wins_by_team: dict[int, int] | None = None
    feeder_tie_ids: tuple[str, ...] = ()
    on_champion_path: bool = False
    source_round_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class GroupedTies:
    """Tree ties and the third-place ties kept out of the tree."""

    ties: list[BracketTie]
    third_place: list[BracketTie]


_TieKey = tuple[str, int | None, int, int]
_ClassifiedMatch = tuple[RoundClass, TieMatch]


def group_ties(matches: list[TieMatch]) -> GroupedTies:
    """Group matches of the same two teams within one phase.

    The pair key is family, depth and the two team ids sorted
    numerically, so home and away can swap without splitting the
    tie. Matches are ordered by series leg, then date, then match
    id. Third-place matches come back beside the tree. A round
    outside the stage map is ignored. Ties are ordered by family,
    depth and team ids.
    """
    tree: dict[_TieKey, list[_ClassifiedMatch]] = {}
    third: dict[_TieKey, list[_ClassifiedMatch]] = {}
    for match in matches:
        placed = _classify_for_tie(match)
        if placed is None:
            continue
        key, classified = placed
        if classified.role == ROLE_THIRD_PLACE:
            bucket = third
        else:
            bucket = tree
        bucket.setdefault(key, []).append((classified, match))
    return GroupedTies(
        ties=_build_ties(tree, False),
        third_place=_build_ties(third, True))


def _classify_for_tie(
        match: TieMatch) -> tuple[_TieKey, RoundClass] | None:
    """Return the pair key, or None when the round is not a stage."""
    classified = classify_round(match.round_number)
    if classified is None:
        return None
    low, high = _pair_ids(match.home_team_id, match.away_team_id)
    key = (classified.family, classified.depth, low, high)
    return (key, classified)


def _pair_ids(home_team_id: int, away_team_id: int) -> tuple[int, int]:
    """Order the two clubs so the key ignores who was home."""
    if home_team_id <= away_team_id:
        return (home_team_id, away_team_id)
    return (away_team_id, home_team_id)


def _build_ties(
        buckets: dict[_TieKey, list[_ClassifiedMatch]],
        third_place: bool) -> list[BracketTie]:
    keys = sorted(buckets, key=_bucket_sort_key)
    return [_build_tie(buckets[key], third_place) for key in keys]


def _bucket_sort_key(key: _TieKey) -> tuple[str, int, int, int]:
    family, depth, low, high = key
    depth_rank = -1 if depth is None else depth
    return (family, depth_rank, low, high)


def _build_tie(
        classified_matches: list[_ClassifiedMatch],
        third_place: bool) -> BracketTie:
    ordered = sorted(classified_matches, key=_match_sort_key)
    family = ordered[0][0].family
    stored = [
        replace(match, leg_index=classified.leg_index)
        for classified, match in ordered]
    low, high = _pair_ids(
        stored[0].home_team_id,
        stored[0].away_team_id)
    depth, label, token = _tie_identity(ordered[0][0], third_place)
    return BracketTie(
        tie_id=f"{family}-{token}-{low}-{high}",
        family=family,
        depth=depth,
        stage_label=label,
        matches=stored,
        team_ids=(low, high),
        source_round_numbers=_source_rounds(stored))


def _tie_identity(
        classified: RoundClass,
        third_place: bool) -> tuple[int | None, str, str]:
    """Depth, column title and the token used inside ``tie_id``."""
    if third_place:
        # 969 nie ma głębokości, a identyfikator pary musi być stabilny.
        return (None, THIRD_PLACE_LABEL, "third")
    depth = classified.depth
    if depth is None:
        raise ValueError("Knockout tie is missing a depth")
    return (depth, stage_label(depth), str(depth))


def _match_sort_key(
        item: _ClassifiedMatch) -> tuple[int, int, datetime, int]:
    classified, match = item
    leg = classified.leg_index
    if match.game_date is None:
        when = _UNDATED
    else:
        when = match.game_date
    if leg is None:
        return (1, 0, when, match.match_id)
    return (0, leg, when, match.match_id)


def _source_rounds(matches: list[TieMatch]) -> tuple[int, ...]:
    return tuple(sorted({match.round_number for match in matches}))
