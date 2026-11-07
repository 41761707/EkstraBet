"""Unit tests for football table-zone labels and slot aggregation."""

from __future__ import annotations

import unittest

from backend.sports.football.table_zones import TableZone
from backend.sports.football.table_zones import aggregate_zones
from backend.sports.football.table_zones import zone_label


def _zone(
        *,
        position_from: int,
        position_to: int,
        zone_kind: str,
        band: str,
        stage: str | None = None,
        target_league_id: int | None = None,
        target_league_name: str | None = None,
        sort_order: int = 1) -> TableZone:
    return TableZone(
        position_from=position_from,
        position_to=position_to,
        zone_kind=zone_kind,
        band=band,
        stage=stage,
        target_league_id=target_league_id,
        target_league_name=target_league_name,
        sort_order=sort_order,
        label=zone_label(zone_kind, stage, target_league_name))


def _ekstraklasa_zones() -> list[TableZone]:
    return [
        _zone(
            position_from=1,
            position_to=1,
            zone_kind="champions_league",
            band="top",
            stage="qualification",
            target_league_id=42,
            target_league_name="Liga Mistrzów",
            sort_order=1),
        _zone(
            position_from=2,
            position_to=2,
            zone_kind="europa_league",
            band="top",
            stage="qualification",
            target_league_id=43,
            target_league_name="Liga Europy",
            sort_order=2),
        _zone(
            position_from=3,
            position_to=4,
            zone_kind="conference_league",
            band="top",
            stage="qualification",
            target_league_id=44,
            target_league_name="Liga Konferencji",
            sort_order=3),
        _zone(
            position_from=16,
            position_to=18,
            zone_kind="relegation",
            band="bot",
            target_league_id=21,
            target_league_name="Betclic 1 Liga",
            sort_order=4)]


class TestZoneLabel(unittest.TestCase):
    """Polish legend copy for each documented zone kind."""

    def test_cup_qualification_with_league(self) -> None:
        self.assertEqual(
            zone_label(
                "champions_league",
                "qualification",
                "Liga Mistrzów"),
            "Awans – Liga Mistrzów (Kwalifikacje)")

    def test_cup_without_stage(self) -> None:
        self.assertEqual(
            zone_label("europa_league", None, "Liga Europy"),
            "Awans – Liga Europy")

    def test_cup_qualification_without_league(self) -> None:
        self.assertEqual(
            zone_label("conference_league", "qualification", None),
            "Awans (Kwalifikacje)")

    def test_promotion_with_and_without_league(self) -> None:
        self.assertEqual(
            zone_label("promotion", None, "Premier League"),
            "Awans – Premier League")
        self.assertEqual(zone_label("promotion", None, None), "Awans")

    def test_promotion_playoff_with_and_without_league(self) -> None:
        self.assertEqual(
            zone_label("promotion_playoff", "playoff", "Premier League"),
            "Baraż o awans – Premier League")
        self.assertEqual(
            zone_label("promotion_playoff", None, None),
            "Baraż o awans")

    def test_relegation_with_and_without_league(self) -> None:
        self.assertEqual(
            zone_label("relegation", None, "Betclic 1 Liga"),
            "Spadek – Betclic 1 Liga")
        self.assertEqual(zone_label("relegation", None, None), "Spadek")

    def test_relegation_playoff_with_and_without_league(self) -> None:
        self.assertEqual(
            zone_label("relegation_playoff", "playoff", "League One"),
            "Baraż o spadek – League One")
        self.assertEqual(
            zone_label("relegation_playoff", None, None),
            "Baraż o spadek")


class TestAggregateZones(unittest.TestCase):
    """Prefix and suffix slot counts from a season zone list."""

    def test_ekstraklasa_seed_yields_four_and_three(self) -> None:
        result = aggregate_zones(_ekstraklasa_zones(), 18)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.top_slots, 4)
        self.assertEqual(result.bot_slots, 3)
        self.assertEqual(
            [zone.label for zone in result.zones],
            [
                "Awans – Liga Mistrzów (Kwalifikacje)",
                "Awans – Liga Europy (Kwalifikacje)",
                "Awans – Liga Konferencji (Kwalifikacje)",
                "Spadek – Betclic 1 Liga"])

    def test_empty_list_yields_zero_slots(self) -> None:
        result = aggregate_zones([], 18)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.top_slots, 0)
        self.assertEqual(result.bot_slots, 0)
        self.assertEqual(result.zones, ())

    def test_prefix_gap_returns_none(self) -> None:
        zones = [
            _zone(
                position_from=1,
                position_to=1,
                zone_kind="champions_league",
                band="top",
                stage="qualification",
                sort_order=1),
            _zone(
                position_from=3,
                position_to=3,
                zone_kind="europa_league",
                band="top",
                stage="qualification",
                sort_order=2)]
        self.assertIsNone(aggregate_zones(zones, 18))

    def test_bot_not_at_the_end_returns_none(self) -> None:
        zones = [
            _zone(
                position_from=14,
                position_to=16,
                zone_kind="relegation",
                band="bot",
                sort_order=1)]
        self.assertIsNone(aggregate_zones(zones, 18))

    def test_overlap_returns_none(self) -> None:
        zones = [
            _zone(
                position_from=1,
                position_to=2,
                zone_kind="champions_league",
                band="top",
                sort_order=1),
            _zone(
                position_from=2,
                position_to=3,
                zone_kind="europa_league",
                band="top",
                sort_order=2)]
        self.assertIsNone(aggregate_zones(zones, 18))

    def test_band_mismatch_returns_none(self) -> None:
        zones = [
            _zone(
                position_from=1,
                position_to=1,
                zone_kind="champions_league",
                band="bot",
                sort_order=1)]
        self.assertIsNone(aggregate_zones(zones, 18))

    def test_position_past_table_size_returns_none(self) -> None:
        zones = [
            _zone(
                position_from=16,
                position_to=19,
                zone_kind="relegation",
                band="bot",
                sort_order=1)]
        self.assertIsNone(aggregate_zones(zones, 18))

    def test_table_size_below_one_returns_none(self) -> None:
        self.assertIsNone(aggregate_zones([], 0))
        self.assertIsNone(aggregate_zones(_ekstraklasa_zones(), 0))


if __name__ == "__main__":
    unittest.main()
