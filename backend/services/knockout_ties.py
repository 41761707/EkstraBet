"""Group knockout matches into ties and score a football tie."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime

from backend.services.knockout_stages import ROLE_THIRD_PLACE
from backend.services.knockout_stages import RoundClass
from backend.services.knockout_stages import classify_round
from backend.services.knockout_stages import stage_label


THIRD_PLACE_LABEL = "Mecz o 3. miejsce"
FOOTBALL_SPORT_ID = 1
DECIDED_REGULATION = "regulation"
DECIDED_EXTRA_TIME = "extra_time"
DECIDED_PENALTIES = "penalties"
_UNPLAYED_RESULT = "0"
_RESULT_HOME = "1"
_RESULT_AWAY = "2"
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

    ``team_ids`` lists the lower team id first. ``tie_with_score``
    fills the football score on a copy. Feeders and the champion
    path stay empty until a later step.
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


def football_match_winner(match: TieMatch) -> int | None:
    """Return the team that won one football match, or None.

    The first condition that names a winner stands. An unplayed
    match (empty result, ``"0"``, or missing goals) has none.
    Otherwise penalties, extra time, a split regulation score and
    a ``"1"`` or ``"2"`` result are tried in that order.
    """
    return _football_outcome(match)[0]


def resolve_score_winner(tie: BracketTie, sport_id: int) -> int | None:
    """Return the football score winner of a tie, or None.

    One match uses ``football_match_winner``. Two matches compare
    the aggregate once both legs are played. A level aggregate
    uses the penalty shootout. Hockey and basketball are not
    scored here.
    """
    # Seria hokeja i koszykówki ma osobny próg zwycięstw.
    if sport_id != FOOTBALL_SPORT_ID:
        return None
    return tie_with_score(tie, sport_id).score_winner_team_id


def tie_with_score(tie: BracketTie, sport_id: int) -> BracketTie:
    """Return a copy with the football score written onto the tie.

    ``decided_by`` is set on each match. A two-legged tie also gets
    ``aggregate_by_team``. ``score_winner_team_id`` is the value
    ``resolve_score_winner`` returns. The tie is frozen, so the
    fields are filled on a copy. Other sports come back unchanged.
    """
    if sport_id != FOOTBALL_SPORT_ID:
        return tie
    return _football_tie_with_score(tie)


def _football_outcome(match: TieMatch) -> tuple[int | None, str | None]:
    """Winner team id and how that winner was decided."""
    if _is_unplayed(match):
        return (None, None)
    penalty_winner = _side_winner(
        match.home_penalty_goals,
        match.away_penalty_goals,
        match)
    if penalty_winner is not None:
        return (penalty_winner, DECIDED_PENALTIES)
    extra_winner = _side_winner(
        match.home_extra_time_goals,
        match.away_extra_time_goals,
        match)
    if extra_winner is not None:
        return (extra_winner, DECIDED_EXTRA_TIME)
    regulation_winner = _side_winner(
        match.home_goals,
        match.away_goals,
        match)
    if regulation_winner is not None:
        return (regulation_winner, DECIDED_REGULATION)
    result_winner = _result_side(match)
    if result_winner is not None:
        return (result_winner, DECIDED_REGULATION)
    return (None, None)


def _is_unplayed(match: TieMatch) -> bool:
    """True when the result is empty or the regulation goals are missing."""
    result = match.result
    if result is None or result == "" or result == _UNPLAYED_RESULT:
        return True
    return match.home_goals is None or match.away_goals is None


def _result_side(match: TieMatch) -> int | None:
    """Team named by a 1 or 2 result, when the score did not split."""
    if match.result == _RESULT_HOME:
        return match.home_team_id
    if match.result == _RESULT_AWAY:
        return match.away_team_id
    return None


def _side_winner(
        home_goals: int | None,
        away_goals: int | None,
        match: TieMatch) -> int | None:
    """Team with the strictly higher total, otherwise None."""
    if home_goals is None or away_goals is None or home_goals == away_goals:
        return None
    if home_goals > away_goals:
        return match.home_team_id
    return match.away_team_id


def _football_tie_with_score(tie: BracketTie) -> BracketTie:
    """Fill decision, aggregate and score winner for football."""
    matches = [_with_decision(match) for match in tie.matches]
    scored = replace(tie, matches=matches)
    if len(matches) == 1:
        return replace(
            scored,
            score_winner_team_id=football_match_winner(matches[0]))
    if len(matches) == 2:
        return _two_legged_score(scored)
    return scored


def _with_decision(match: TieMatch) -> TieMatch:
    """Copy the match when ``decided_by`` changes."""
    decided_by = _football_outcome(match)[1]
    if match.decided_by == decided_by:
        return match
    return replace(match, decided_by=decided_by)


def _two_legged_score(tie: BracketTie) -> BracketTie:
    """Fill the running total, then the winner when both legs are played.

    The total of the played leg stays on the card. The pair winner
    waits, because a final would otherwise name a champion between
    the two matches.
    """
    aggregate = _aggregate_by_team(tie)
    # W finale ten identyfikator staje się awansem. W przerwie
    # między nogami ścieżka mistrza ma zostać zgaszona.
    if _has_unplayed_leg(tie):
        winner = None
    else:
        winner = _winner_from_aggregate(tie, aggregate)
    return replace(
        tie,
        aggregate_by_team=aggregate,
        score_winner_team_id=winner)


def _has_unplayed_leg(tie: BracketTie) -> bool:
    """True when either leg is still unplayed."""
    for match in tie.matches:
        if _is_unplayed(match):
            return True
    return False


def _aggregate_by_team(tie: BracketTie) -> dict[int, int] | None:
    """Sum played legs by team. Penalty kicks are not included."""
    if len(tie.team_ids) != 2:
        return None
    totals = {team_id: 0 for team_id in tie.team_ids}
    counted = False
    for match in tie.matches:
        pair = _goals_in_aggregate(match)
        if pair is None:
            continue
        home_goals, away_goals = pair
        totals[match.home_team_id] += home_goals
        totals[match.away_team_id] += away_goals
        counted = True
    if not counted:
        return None
    return totals


def _goals_in_aggregate(match: TieMatch) -> tuple[int, int] | None:
    """Goals that enter the two-legged sum for one match.

    Only a leg that ``football_match_winner`` would accept is
    counted. Extra-time totals already include regulation, so they
    replace it. A shootout never enters the sum.
    """
    if _is_unplayed(match):
        return None
    extra_home = match.home_extra_time_goals
    extra_away = match.away_extra_time_goals
    if extra_home is not None and extra_away is not None:
        return (extra_home, extra_away)
    home_goals = match.home_goals
    away_goals = match.away_goals
    if home_goals is None or away_goals is None:
        return None
    return (home_goals, away_goals)


def _winner_from_aggregate(
        tie: BracketTie,
        aggregate: dict[int, int] | None) -> int | None:
    """Higher aggregate, or the shootout when the sums are level."""
    if aggregate is None or len(tie.team_ids) != 2:
        return None
    first_id, second_id = tie.team_ids
    first_goals = aggregate[first_id]
    second_goals = aggregate[second_id]
    if first_goals > second_goals:
        return first_id
    if second_goals > first_goals:
        return second_id
    return _shootout_winner(tie)


def _shootout_winner(tie: BracketTie) -> int | None:
    """Team that won penalties on the latest match that had them."""
    # Karne dwumeczu padają na późniejszym meczu. Gdy są na obu,
    # rozstrzyga ten późniejszy.
    winner = None
    for match in tie.matches:
        shootout = _side_winner(
            match.home_penalty_goals,
            match.away_penalty_goals,
            match)
        if shootout is not None:
            winner = shootout
    return winner
