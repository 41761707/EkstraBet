"""Link knockout ties, add byes and hide a lone phase."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from backend.services.knockout_profiles import PENDING_OPPONENT_LABEL
from backend.services.knockout_profiles import ByeProfile
from backend.services.knockout_profiles import SeededTeam
from backend.services.knockout_stages import FAMILY_CUP
from backend.services.knockout_stages import FAMILY_RELEGATION
from backend.services.knockout_stages import stage_label
from backend.services.knockout_ties import BracketTie


CUP_BRACKET_TITLE = "Drabinka"
RELEGATION_BRACKET_TITLE = "Baraż o utrzymanie"
# Poprzedni szczebel stałej drabinki. Profil wchodzi na 8 i dostaje
# wolny los na 16, nawet gdy tej fazy jeszcze nie ma w meczach.
_PHASE_BEFORE: dict[int, int] = {
    1: 2,
    2: 4,
    4: 8,
    8: 16,
    16: 32,
    32: 64}


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


def apply_byes(
        ties: list[BracketTie],
        seeds: list[SeededTeam],
        profile: ByeProfile | None) -> list[BracketTie]:
    """Add bye cards, then seeded entries when the profile is on.

    A team that first shows up in a later phase gets one bye in
    the previous phase this bracket already has. The profile adds
    its own cards only when a cup match exists. A placeholder is
    not linked to a playoff tie.
    """
    with_byes = _apply_structural_byes(ties)
    if profile is None or not _has_cup_match(with_byes):
        return with_byes
    return _apply_profile(with_byes, seeds, profile)


def _apply_structural_byes(
        ties: list[BracketTie]) -> list[BracketTie]:
    """One bye per team, on the nearest earlier phase that exists."""
    created: dict[str, BracketTie] = {}
    extra: dict[str, list[str]] = {}
    for family_ties in _drawn_by_family(ties).values():
        _byes_for_family(family_ties, created, extra)
    return _merge_cards(ties, created, extra)


def _byes_for_family(
        family_ties: list[BracketTie],
        created: dict[str, BracketTie],
        extra: dict[str, list[str]]) -> None:
    """Byes for teams that did not play an earlier drawn phase."""
    depths: list[int] = []
    for tie in family_ties:
        if tie.depth is not None:
            depths.append(tie.depth)
    for tie in family_ties:
        depth = tie.depth
        if depth is None:
            continue
        previous = _previous_existing_depth(depth, depths)
        if previous is None:
            continue
        _byes_for_tie(tie, previous, family_ties, created, extra)


def _byes_for_tie(
        tie: BracketTie,
        previous: int,
        family_ties: list[BracketTie],
        created: dict[str, BracketTie],
        extra: dict[str, list[str]]) -> None:
    """Attach a bye for each team that starts in this phase."""
    for team_id in tie.team_ids:
        if _played_earlier(team_id, previous, family_ties):
            continue
        bye = _bye_tie(tie.family, previous, team_id)
        created.setdefault(bye.tie_id, bye)
        _remember_feeder(extra, tie.tie_id, bye.tie_id)


def _previous_existing_depth(
        depth: int,
        depths: list[int]) -> int | None:
    """Nearest drawn phase further from the final, if there is one.

    A team that skips two rounds still gets a single card. The
    phase behind that card is not filled in again.
    """
    previous: int | None = None
    for candidate in depths:
        if candidate <= depth:
            continue
        if previous is None or candidate < previous:
            previous = candidate
    return previous


def _played_earlier(
        team_id: int,
        previous: int,
        family_ties: list[BracketTie]) -> bool:
    """True when the team already has a tie in that earlier phase.

    ``previous`` is the bye's own depth. A tie there, or still
    further from the final, means the team did not receive a bye.
    """
    for other in family_ties:
        other_depth = other.depth
        if other_depth is None or other_depth < previous:
            continue
        if team_id in other.team_ids:
            return True
    return False


def _apply_profile(
        ties: list[BracketTie],
        seeds: list[SeededTeam],
        profile: ByeProfile) -> list[BracketTie]:
    """Placeholders, or a ladder bye for a seed already drawn."""
    chosen = _seeds_in_profile(seeds, profile)
    if not chosen:
        return ties
    drawn = _drawn_at(ties, FAMILY_CUP, profile.enter_depth)
    if not drawn:
        # Brak fazy wejścia: rywal nie jest wylosowany, więc nie ma linii.
        return _merge_cards(
            ties,
            _placeholder_cards(chosen, profile.enter_depth, ties),
            {})
    return _seed_byes(ties, chosen, profile, drawn)


def _seeds_in_profile(
        seeds: list[SeededTeam],
        profile: ByeProfile) -> list[SeededTeam]:
    """Profile places, first row per team, ordered by the table."""
    allowed = set(profile.places)
    chosen: dict[int, SeededTeam] = {}
    for seed in seeds:
        if seed.position not in allowed:
            continue
        if seed.team_id in chosen:
            continue
        chosen[seed.team_id] = seed
    return sorted(
        chosen.values(),
        key=lambda seed: (seed.position, seed.team_id))


def _drawn_at(
        ties: list[BracketTie],
        family: str,
        depth: int) -> list[BracketTie]:
    """Real pairs of one family and depth. Byes are not a draw."""
    return [
        tie for tie in ties
        if tie.family == family
        and tie.depth == depth
        and _is_real_match(tie)]


def _placeholder_cards(
        seeds: list[SeededTeam],
        depth: int,
        ties: list[BracketTie]) -> dict[str, BracketTie]:
    """One undrawn card per seed. Existing ids are left alone."""
    existing = {tie.tie_id for tie in ties}
    cards: dict[str, BracketTie] = {}
    for seed in seeds:
        card = _placeholder_tie(seed, depth)
        if card.tie_id in existing:
            continue
        cards[card.tie_id] = card
    return cards


def _seed_byes(
        ties: list[BracketTie],
        seeds: list[SeededTeam],
        profile: ByeProfile,
        drawn: list[BracketTie]) -> list[BracketTie]:
    """A bye on the ladder step before entry, unless a real tie feeds it."""
    bye_depth = _PHASE_BEFORE.get(profile.enter_depth)
    if bye_depth is None:
        return ties
    by_id = {tie.tie_id: tie for tie in ties}
    created: dict[str, BracketTie] = {}
    extra: dict[str, list[str]] = {}
    for seed in seeds:
        _bye_for_seed(
            seed.team_id,
            bye_depth,
            drawn,
            by_id,
            created,
            extra)
    return _merge_cards(ties, created, extra)


def _bye_for_seed(
        team_id: int,
        bye_depth: int,
        drawn: list[BracketTie],
        by_id: dict[str, BracketTie],
        created: dict[str, BracketTie],
        extra: dict[str, list[str]]) -> None:
    """Bye for a seed that is already in the entry round."""
    homes = [tie for tie in drawn if team_id in tie.team_ids]
    if not homes:
        # Faza już jest. Ziarna spoza par nie dostają placeholdera.
        return
    if all(_has_real_feeder(tie, team_id, by_id) for tie in homes):
        return
    bye = _bye_tie(FAMILY_CUP, bye_depth, team_id)
    if bye.tie_id not in by_id:
        created.setdefault(bye.tie_id, bye)
    for tie in homes:
        if _has_real_feeder(tie, team_id, by_id):
            continue
        if bye.tie_id in tie.feeder_tie_ids:
            continue
        _remember_feeder(extra, tie.tie_id, bye.tie_id)


def _has_real_feeder(
        tie: BracketTie,
        team_id: int,
        by_id: dict[str, BracketTie]) -> bool:
    """True when a played tie of this team already feeds the pair."""
    for feeder_id in tie.feeder_tie_ids:
        feeder = by_id.get(feeder_id)
        if feeder is None or team_id not in feeder.team_ids:
            continue
        if _is_real_match(feeder):
            return True
    return False


def _merge_cards(
        ties: list[BracketTie],
        created: dict[str, BracketTie],
        extra: dict[str, list[str]]) -> list[BracketTie]:
    """Append new cards and point the destination ties at them."""
    if not created and not extra:
        return ties
    updated = [
        _with_extra_feeders(tie, extra.get(tie.tie_id, ()))
        for tie in ties]
    existing = {tie.tie_id for tie in ties}
    added = [
        created[tie_id]
        for tie_id in _card_order(created)
        if tie_id not in existing]
    return updated + added


def _card_order(created: dict[str, BracketTie]) -> list[str]:
    """Family, phase, table place, then team. Input order stays stable."""
    ordered = sorted(created.values(), key=_card_sort_key)
    return [card.tie_id for card in ordered]


def _card_sort_key(
        card: BracketTie) -> tuple[str, int, int, int, str]:
    """Placeholders follow the table. A bye has no place, so team id wins."""
    depth = card.depth if card.depth is not None else 0
    team_id = card.team_ids[0] if card.team_ids else 0
    position = card.seed_position if card.seed_position is not None else 0
    return (card.family, depth, position, team_id, card.tie_id)


def _remember_feeder(
        extra: dict[str, list[str]],
        destination_id: str,
        source_id: str) -> None:
    """Record one new feeder. A second pass adds nothing."""
    bucket = extra.setdefault(destination_id, [])
    if source_id in bucket:
        return
    bucket.append(source_id)


def _with_extra_feeders(
        tie: BracketTie,
        extra: list[str] | tuple[str, ...]) -> BracketTie:
    """Return the same tie when every extra id is already stored."""
    if not extra:
        return tie
    merged = list(tie.feeder_tie_ids)
    changed = False
    for feeder_id in extra:
        if feeder_id in merged:
            continue
        merged.append(feeder_id)
        changed = True
    if not changed:
        return tie
    return replace(tie, feeder_tie_ids=tuple(merged))


def _bye_tie(family: str, depth: int, team_id: int) -> BracketTie:
    """A card with one team and no match."""
    return BracketTie(
        tie_id=f"bye-{family}-{depth}-{team_id}",
        family=family,
        depth=depth,
        stage_label=stage_label(depth),
        matches=[],
        team_ids=(team_id,),
        is_bye=True)


def _placeholder_tie(seed: SeededTeam, depth: int) -> BracketTie:
    """A seeded team whose opponent has not been drawn."""
    return BracketTie(
        tie_id=f"{FAMILY_CUP}-{depth}-{seed.team_id}-pending",
        family=FAMILY_CUP,
        depth=depth,
        stage_label=stage_label(depth),
        matches=[],
        team_ids=(seed.team_id,),
        pending_opponent_label=PENDING_OPPONENT_LABEL,
        seed_position=seed.position)


def _drawn_by_family(
        ties: list[BracketTie]) -> dict[str, list[BracketTie]]:
    """Real pairs grouped by family, in input order."""
    grouped: dict[str, list[BracketTie]] = {}
    for tie in ties:
        if tie.depth is None or not _is_real_match(tie):
            continue
        grouped.setdefault(tie.family, []).append(tie)
    return grouped


def _has_cup_match(ties: list[BracketTie]) -> bool:
    """True when the cup has a match. A bye does not count."""
    for tie in ties:
        if tie.family != FAMILY_CUP:
            continue
        if _is_real_match(tie):
            return True
    return False
