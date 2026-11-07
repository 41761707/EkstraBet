"""Unit tests for tipster cleanup in delete_match."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "db_funcs" / "Pilka" / "delete_match.py"
_MODULE: ModuleType | None = None


def _load_module() -> ModuleType:
    """Load delete_match.py without requiring a real db_module."""
    global _MODULE
    if _MODULE is not None:
        return _MODULE
    sys.modules.setdefault("db_module", MagicMock())
    spec = importlib.util.spec_from_file_location("delete_match", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _MODULE = module
    return module


class _TipsterDeleteCursor:
    """In-memory cursor for the SQL issued by _delete_children."""

    def __init__(self) -> None:
        # 100 = single na meczu 10; 200 = ako na meczach 10 i 11
        self.legs: dict[int, dict[str, int | str]] = {
            1: {"coupon_id": 100, "match_id": 10, "odds": "1.8000"},
            2: {"coupon_id": 200, "match_id": 10, "odds": "2.0000"},
            3: {"coupon_id": 200, "match_id": 11, "odds": "1.5000"}}
        self.leg_events: dict[int, list[int]] = {1: [6, 8],
            2: [1],
            3: [2]}
        self.coupons: set[int] = {100, 200}
        self.coupon_odds: dict[int, str] = {100: "1.8000", 200: "3.0000"}
        self.coupon_stake: dict[int, str] = {100: "5.00", 200: "10.00"}
        self.coupon_settled: dict[int, int] = {100: 0, 200: 1}
        self.coupon_outcome: dict[int, int | None] = {100: None, 200: 1}
        self.coupon_profit: dict[int, str | None] = {100: None, 200: "20.00"}
        self.recommendations: list[dict[str, int]] = [
            {"id": 1, "prediction_match_id": 10, "odds_match_id": 10},
            {"id": 2, "prediction_match_id": 11, "odds_match_id": 11}]
        self.statements: list[str] = []
        self.rowcount = 0
        self._rows: list[tuple[int, ...]] = []

    def execute(
            self,
            sql: str,
            params: tuple[Any, ...] = ()) -> None:
        self.statements.append(sql)
        compact = " ".join(sql.split())
        if "SELECT DISTINCT coupon_id FROM tipster_coupon_legs" in compact:
            self._rows = self._coupon_ids_for_matches(params)
            return
        if "SELECT l.coupon_id, l.odds" in compact:
            self._rows = self._remaining_leg_odds(params)
            return
        if compact.startswith("UPDATE tipster_coupons"):
            self._reprice_coupon(params)
            return
        if "DELETE e FROM tipster_coupon_leg_events" in compact:
            self._delete_leg_events_for_matches(params)
            return
        if compact.startswith("DELETE FROM tipster_coupon_legs"):
            self._delete_legs_for_matches(params)
            return
        if "DELETE br FROM betting_recommendations" in compact:
            self._delete_recommendations_for_matches(params)
            return
        if compact.startswith("DELETE FROM tipster_coupons"):
            self._delete_empty_coupons(params)
            return
        if "DELETE fp FROM final_predictions" in compact:
            self.rowcount = 0
            return
        raise AssertionError(f"Unexpected SQL: {compact}")

    def fetchall(self) -> list[tuple[int, ...]]:
        return list(self._rows)

    def _coupon_ids_for_matches(
            self, params: tuple[Any, ...]) -> list[tuple[int, ...]]:
        match_ids = {int(value) for value in params}
        coupon_ids = sorted({
            leg["coupon_id"]
            for leg in self.legs.values()
            if leg["match_id"] in match_ids})
        return [(coupon_id,) for coupon_id in coupon_ids]

    def _remaining_leg_odds(
            self, params: tuple[Any, ...]) -> list[tuple[int, str]]:
        coupon_ids = {int(value) for value in params}
        return [
            (int(leg["coupon_id"]), str(leg["odds"]))
            for leg in self.legs.values()
            if int(leg["coupon_id"]) in coupon_ids]

    def _reprice_coupon(self, params: tuple[Any, ...]) -> None:
        combined, _again, coupon_id = params
        coupon_id = int(coupon_id)
        self.coupon_odds[coupon_id] = str(combined)
        won = (
            self.coupon_settled.get(coupon_id) == 1
            and self.coupon_outcome.get(coupon_id) == 1)
        if won:
            stake = Decimal(self.coupon_stake[coupon_id])
            odds = Decimal(str(combined))
            profit = (stake * (odds - Decimal("1"))).quantize(Decimal("0.01"))
            self.coupon_profit[coupon_id] = format(profit, "f")
        self.rowcount = 1

    def _delete_leg_events_for_matches(
            self, params: tuple[Any, ...]) -> None:
        match_ids = {int(value) for value in params}
        removed = 0
        for leg_id, leg in self.legs.items():
            if leg["match_id"] not in match_ids:
                continue
            removed += len(self.leg_events.get(leg_id, []))
            self.leg_events.pop(leg_id, None)
        self.rowcount = removed

    def _delete_recommendations_for_matches(
            self, params: tuple[Any, ...]) -> None:
        match_ids = {int(value) for value in params}
        kept = [
            row for row in self.recommendations
            if row["prediction_match_id"] not in match_ids
            and row["odds_match_id"] not in match_ids]
        self.rowcount = len(self.recommendations) - len(kept)
        self.recommendations = kept

    def _delete_legs_for_matches(self, params: tuple[Any, ...]) -> None:
        match_ids = {int(value) for value in params}
        removed = [
            leg_id
            for leg_id, leg in list(self.legs.items())
            if leg["match_id"] in match_ids]
        for leg_id in removed:
            del self.legs[leg_id]
            # ON DELETE CASCADE — typy znikają razem ze zdarzeniem kuponu
            self.leg_events.pop(leg_id, None)
        self.rowcount = len(removed)

    def _delete_empty_coupons(self, params: tuple[Any, ...]) -> None:
        deleted = 0
        for coupon_id in (int(value) for value in params):
            has_leg = any(
                leg["coupon_id"] == coupon_id
                for leg in self.legs.values())
            if not has_leg and coupon_id in self.coupons:
                self.coupons.remove(coupon_id)
                deleted += 1
        self.rowcount = deleted


class TestDeleteMatchTipsterCleanup(unittest.TestCase):
    """Deleting a match must drop only affected tipster legs and empties."""

    def test_deletes_legs_events_and_recommendations_for_the_match(
            self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (10,))
        sql = " ".join(cursor.statements)
        events_at = sql.index("DELETE e FROM tipster_coupon_leg_events")
        legs_at = sql.index("DELETE FROM tipster_coupon_legs")
        self.assertLess(events_at, legs_at)
        self.assertIn("DELETE br FROM betting_recommendations", sql)
        self.assertNotIn(1, cursor.legs)
        self.assertNotIn(2, cursor.legs)
        self.assertNotIn(1, cursor.leg_events)
        self.assertNotIn(2, cursor.leg_events)
        self.assertEqual(
            cursor.recommendations,
            [{"id": 2, "prediction_match_id": 11, "odds_match_id": 11}])

    def test_single_coupon_removed_ako_with_other_leg_stays(self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (10,))
        self.assertNotIn(100, cursor.coupons)
        self.assertIn(200, cursor.coupons)
        self.assertEqual(
            cursor.legs,
            {3: {"coupon_id": 200, "match_id": 11, "odds": "1.5000"}})
        self.assertEqual(cursor.leg_events, {3: [2]})
        self.assertEqual(cursor.coupon_odds[200], "1.5000")
        self.assertEqual(cursor.coupon_profit[200], "5.00")
        self.assertEqual(cursor.coupon_odds[100], "1.8000")
        statements = " ".join(cursor.statements)
        self.assertLess(
            statements.index("DELETE FROM tipster_coupon_legs"),
            statements.index("UPDATE tipster_coupons"))
        self.assertIn("NOT EXISTS", statements)

    def test_unrelated_match_leaves_coupons_and_legs(self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (99,))
        self.assertEqual(cursor.coupons, {100, 200})
        self.assertEqual(set(cursor.legs), {1, 2, 3})
        self.assertEqual(set(cursor.leg_events), {1, 2, 3})
        self.assertEqual(len(cursor.recommendations), 2)
        self.assertEqual(cursor.coupon_odds, {100: "1.8000", 200: "3.0000"})
        deletes = [
            sql for sql in cursor.statements
            if sql.lstrip().startswith("DELETE FROM tipster_coupons")]
        self.assertEqual(deletes, [])


if __name__ == "__main__":
    unittest.main()
