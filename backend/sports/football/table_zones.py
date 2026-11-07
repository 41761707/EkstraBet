"""Aggregate football table zones into top and bottom slot counts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


_CUP_ZONE_KINDS = frozenset({
    "champions_league",
    "europa_league",
    "conference_league"})

_ZONE_BANDS: dict[str, str] = {
    "champions_league": "top",
    "europa_league": "top",
    "conference_league": "top",
    "promotion": "top",
    "promotion_playoff": "top",
    "relegation": "bot",
    "relegation_playoff": "bot"}

_DIRECT_LABELS: dict[str, str] = {
    "promotion": "Awans",
    "promotion_playoff": "Baraż o awans",
    "relegation": "Spadek",
    "relegation_playoff": "Baraż o spadek"}

_ALLOWED_STAGES = frozenset({None, "qualification", "playoff"})


@dataclass(frozen=True)
class TableZone:
    """One contiguous block of table positions with a shared meaning."""

    position_from: int
    position_to: int
    zone_kind: str
    band: str
    stage: str | None
    target_league_id: int | None
    target_league_name: str | None
    sort_order: int
    label: str


@dataclass(frozen=True)
class TableZoneSet:
    """Validated zones plus the prefix and suffix lengths they imply."""

    zones: tuple[TableZone, ...]
    top_slots: int
    bot_slots: int


def zone_label(
        zone_kind: str,
        stage: str | None,
        target_league_name: str | None) -> str:
    """Polish legend text for one zone.

    A cup zone in the qualification stage appends ``(Kwalifikacje)``
    after the optional target league. Other kinds ignore ``stage``.
    A missing target league drops the `` – {name}`` fragment.
    """
    prefix, suffix = _label_parts(zone_kind, stage)
    if target_league_name:
        text = f"{prefix} – {target_league_name}"
    else:
        text = prefix
    if suffix:
        return f"{text} {suffix}"
    return text


def aggregate_zones(
        zones: Sequence[TableZone],
        table_size: int) -> TableZoneSet | None:
    """Return slot counts, or None when the configuration is invalid.

    An empty zone list is valid and yields both counts equal to 0.
    Positions with no row stay neutral and do not enter either count.
    """
    if table_size < 1:
        return None
    if not zones:
        # Liga bez wierszy stref nie jest błędem konfiguracji.
        return TableZoneSet(zones=(), top_slots=0, bot_slots=0)
    covered = _covered_positions(zones, table_size)
    if covered is None:
        return None
    top_slots = _slot_count(covered, "top")
    bot_slots = _slot_count(covered, "bot")
    if not _bands_are_edges(covered, table_size, top_slots, bot_slots):
        return None
    return TableZoneSet(
        zones=tuple(zones),
        top_slots=top_slots,
        bot_slots=bot_slots)


def _label_parts(zone_kind: str, stage: str | None) -> tuple[str, str]:
    if zone_kind in _CUP_ZONE_KINDS:
        if stage == "qualification":
            return "Awans", "(Kwalifikacje)"
        return "Awans", ""
    return _DIRECT_LABELS.get(zone_kind, zone_kind), ""


def _covered_positions(
        zones: Sequence[TableZone],
        table_size: int) -> dict[int, str] | None:
    covered: dict[int, str] = {}
    for zone in zones:
        if not _zone_shape_ok(zone, table_size):
            return None
        for position in range(zone.position_from, zone.position_to + 1):
            if position in covered:
                return None
            covered[position] = zone.band
    return covered


def _zone_shape_ok(zone: TableZone, table_size: int) -> bool:
    if zone.position_from < 1 or zone.position_from > zone.position_to:
        return False
    if zone.position_to > table_size:
        return False
    expected_band = _ZONE_BANDS.get(zone.zone_kind)
    if expected_band is None or zone.band != expected_band:
        return False
    return zone.stage in _ALLOWED_STAGES


def _slot_count(covered: dict[int, str], band: str) -> int:
    return sum(1 for value in covered.values() if value == band)


def _bands_are_edges(
        covered: dict[int, str],
        table_size: int,
        top_slots: int,
        bot_slots: int) -> bool:
    # Projekcja sumuje prefiks 1..K i sufiks ostatnich M miejsc.
    if top_slots + bot_slots > table_size:
        return False
    top_positions = {
        pos for pos, band in covered.items() if band == "top"}
    bot_positions = {
        pos for pos, band in covered.items() if band == "bot"}
    if top_positions != set(range(1, top_slots + 1)):
        return False
    expected_bot = set(
        range(table_size - bot_slots + 1, table_size + 1))
    return bot_positions == expected_bot
