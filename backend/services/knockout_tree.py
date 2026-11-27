"""Link knockout ties into family trees and hide a lone phase."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from backend.services.knockout_stages import FAMILY_CUP
from backend.services.knockout_stages import FAMILY_RELEGATION
from backend.services.knockout_ties import BracketTie


CUP_BRACKET_TITLE = "Drabinka"
RELEGATION_BRACKET_TITLE = "Baraż o utrzymanie"


@dataclass(frozen=True)
class KnockoutBracket:
    """One family drawn as columns, plus an optional third-place tie.

    ``ties`` stay in caller order until a later step sorts them.
    ``consumed_round_numbers`` lists rounds of a bracket that is
    actually drawn. A hidden one-phase bracket contributes none.
    """

    bracket_id: str
    title: str
    ties: list[BracketTie]
    third_place: BracketTie | None = None
    consumed_round_numbers: tuple[int, ...] = ()


def link_feeders(ties: list[BracketTie]) -> list[BracketTie]:
    """Point each earlier tie at the later tie its team played.

    Linking stays inside one family. The third-place match is not
    a later tie. When the next match and the score name different
    teams, advancement follows the next match. The closest phase
    takes its score winner when nobody from the pair played on.
    """
    feeders = {tie.tie_id: [] for tie in ties}
    advanced: dict[str, int] = {}
    for family_ties in _by_family(ties).values():
        advanced.update(_links_for_family(family_ties, feeders))
    return [
        _with_links(
            tie,
            advanced.get(tie.tie_id),
            tuple(feeders[tie.tie_id]))
        for tie in ties]


def visible_brackets(
        brackets: list[KnockoutBracket]) -> list[KnockoutBracket]:
    """Drop a one-phase bracket that has no bye and no placeholder.

    A kept cup is titled "Drabinka". A kept relegation bracket is
    titled "Baraż o utrzymanie". Consumed rounds are the rounds of
    ties that remain, including the attached third-place match.
    """
    return [
        _with_heading(bracket)
        for bracket in brackets
        if _is_visible(bracket)]


def _by_family(ties: list[BracketTie]) -> dict[str, list[BracketTie]]:
    """Keep input order inside each family."""
    grouped: dict[str, list[BracketTie]] = {}
    for tie in ties:
        grouped.setdefault(tie.family, []).append(tie)
    return grouped


def _links_for_family(
        family_ties: list[BracketTie],
        feeders: dict[str, list[str]]) -> dict[str, int]:
    """Advancers in one family. Feeders land in ``feeders``."""
    playable = [tie for tie in family_ties if tie.depth is not None]
    closest = _closest_depth(playable)
    advanced: dict[str, int] = {}
    for tie in playable:
        winner = _advancing_team(tie, playable, closest, feeders)
        if winner is not None:
            advanced[tie.tie_id] = winner
    return advanced


def _closest_depth(ties: list[BracketTie]) -> int | None:
    """Smallest depth in the family. That phase is the frontier."""
    closest: int | None = None
    for tie in ties:
        depth = tie.depth
        if depth is None:
            continue
        if closest is None or depth < closest:
            closest = depth
    return closest


def _advancing_team(
        tie: BracketTie,
        playable: list[BracketTie],
        closest: int | None,
        feeders: dict[str, list[str]]) -> int | None:
    """Team that played on, or the score winner on the frontier."""
    clear: list[int] = []
    blocked = False
    for team_id in tie.team_ids:
        destination, ambiguous = _later_tie(tie, team_id, playable)
        if ambiguous:
            # Dwie pary w tej samej fazie nie dostają linii.
            blocked = True
            continue
        if destination is None:
            continue
        clear.append(team_id)
        _add_feeder(feeders, destination.tie_id, tie.tie_id)
    if len(clear) == 1 and not blocked:
        return clear[0]
    if clear or blocked:
        # Dwie drużyny z dalszą parą albo dwie pary jednej drużyny.
        # Jedno pole awansu zostałoby zgadywaniem.
        return None
    if tie.depth == closest:
        return tie.score_winner_team_id
    return None


def _later_tie(
        source: BracketTie,
        team_id: int,
        playable: list[BracketTie]) -> tuple[BracketTie | None, bool]:
    """Nearest later tie, and whether that depth is ambiguous.

    ``(None, False)`` means the team does not play again.
    ``(None, True)`` means two ties share the nearest later depth.
    """
    source_depth = source.depth
    if source_depth is None:
        return (None, False)
    later = _ties_before(source_depth, team_id, playable)
    if not later:
        return (None, False)
    nearest = _nearest_depth(later)
    nearest_ties = [
        other for other in later if other.depth == nearest]
    if len(nearest_ties) != 1:
        return (None, True)
    return (nearest_ties[0], False)


def _ties_before(
        source_depth: int,
        team_id: int,
        playable: list[BracketTie]) -> list[BracketTie]:
    """Ties of this team closer to the final than ``source``."""
    found: list[BracketTie] = []
    for other in playable:
        other_depth = other.depth
        if other_depth is None or other_depth >= source_depth:
            continue
        if team_id not in other.team_ids:
            continue
        found.append(other)
    return found


def _nearest_depth(ties: list[BracketTie]) -> int:
    """Largest depth that is still closer to the final."""
    nearest: int | None = None
    for tie in ties:
        depth = tie.depth
        if depth is None:
            continue
        if nearest is None or depth > nearest:
            nearest = depth
    if nearest is None:
        raise ValueError("Later knockout ties have no depth")
    return nearest


def _add_feeder(
        feeders: dict[str, list[str]],
        destination_id: str,
        source_id: str) -> None:
    """Append one source. The other team of that tie adds nothing."""
    bucket = feeders[destination_id]
    if source_id in bucket:
        return
    bucket.append(source_id)


def _with_links(
        tie: BracketTie,
        advanced: int | None,
        feeder_ids: tuple[str, ...]) -> BracketTie:
    """Return the same tie when the links are already those values."""
    if (tie.advanced_team_id == advanced
            and tie.feeder_tie_ids == feeder_ids):
        return tie
    return replace(
        tie,
        advanced_team_id=advanced,
        feeder_tie_ids=feeder_ids)


def _is_visible(bracket: KnockoutBracket) -> bool:
    """True for two phases, or a match plus a bye or placeholder."""
    if len(_depths(bracket.ties)) >= 2:
        return True
    return _has_real_match(bracket.ties) and _has_open_card(bracket.ties)


def _depths(ties: list[BracketTie]) -> set[int]:
    found: set[int] = set()
    for tie in ties:
        depth = tie.depth
        if depth is not None:
            found.add(depth)
    return found


def _has_real_match(ties: list[BracketTie]) -> bool:
    for tie in ties:
        if _is_real_match(tie):
            return True
    return False


def _is_real_match(tie: BracketTie) -> bool:
    """A played or scheduled match. A bye and a placeholder are not."""
    if tie.is_bye or tie.pending_opponent_label is not None:
        return False
    return len(tie.matches) > 0


def _has_open_card(ties: list[BracketTie]) -> bool:
    for tie in ties:
        if tie.is_bye or tie.pending_opponent_label is not None:
            return True
    return False


def _with_heading(bracket: KnockoutBracket) -> KnockoutBracket:
    return replace(
        bracket,
        title=_title_for(_family_of(bracket)),
        consumed_round_numbers=_consumed_rounds(bracket))


def _family_of(bracket: KnockoutBracket) -> str:
    if bracket.ties:
        return bracket.ties[0].family
    if bracket.third_place is not None:
        return bracket.third_place.family
    return FAMILY_CUP


def _title_for(family: str) -> str:
    if family == FAMILY_RELEGATION:
        return RELEGATION_BRACKET_TITLE
    return CUP_BRACKET_TITLE


def _consumed_rounds(bracket: KnockoutBracket) -> tuple[int, ...]:
    """Rounds of the kept ties, plus the attached third-place match.

    The third-place tie is not a column, so its round is added from
    the side field. A bracket that was dropped never reaches here.
    """
    found: set[int] = set()
    for tie in bracket.ties:
        found.update(tie.source_round_numbers)
    third = bracket.third_place
    if third is not None:
        found.update(third.source_round_numbers)
    return tuple(sorted(found))
