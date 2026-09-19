"""Unit tests for tipster cleanup in delete_match."""

from __future__ import annotations

import importlib.util
import sys
import unittest
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
        self.legs: dict[int, dict[str, int]] = {1: {"coupon_id": 100,
            "match_id": 10},
            2: {"coupon_id": 200, "match_id": 10},
            3: {"coupon_id": 200, "match_id": 11}}
        self.leg_events: dict[int, list[int]] = {1: [6, 8],
            2: [1],
            3: [2]}
        self.coupons: set[int] = {100, 200}
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
        if compact.startswith("DELETE FROM tipster_coupon_legs"):
            self._delete_legs_for_matches(params)
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

    def _delete_legs_for_matches(self, params: tuple[Any, ...]) -> None:
        match_ids = {int(value) for value in params}
        removed = [
            leg_id
            for leg_id, leg in list(self.legs.items())
            if leg["match_id"] in match_ids]
        for leg_id in removed:
            del self.legs[leg_id]
            # ON DELETE CASCADE — eventy nogi znikają razem z nogą
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

    def test_deletes_legs_by_match_id_without_touching_leg_events(
            self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (10,))
        sql = " ".join(cursor.statements)
        self.assertIn("DELETE FROM tipster_coupon_legs", sql)
        self.assertIn("match_id IN", sql)
        self.assertNotIn("tipster_coupon_leg_events", sql)
        self.assertNotIn(1, cursor.legs)
        self.assertNotIn(2, cursor.legs)

    def test_single_coupon_removed_ako_with_other_leg_stays(self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (10,))
        self.assertNotIn(100, cursor.coupons)
        self.assertIn(200, cursor.coupons)
        self.assertEqual(cursor.legs, {3: {"coupon_id": 200, "match_id": 11}})
        self.assertEqual(cursor.leg_events, {3: [2]})
        self.assertIn("NOT EXISTS", " ".join(cursor.statements))

    def test_unrelated_match_leaves_coupons_and_legs(self) -> None:
        module = _load_module()
        cursor = _TipsterDeleteCursor()
        module._delete_children(cursor, "%s", (99,))
        self.assertEqual(cursor.coupons, {100, 200})
        self.assertEqual(set(cursor.legs), {1, 2, 3})
        self.assertEqual(set(cursor.leg_events), {1, 2, 3})
        deletes = [
            sql for sql in cursor.statements
            if sql.lstrip().startswith("DELETE FROM tipster_coupons")]
        self.assertEqual(deletes, [])


if __name__ == "__main__":
    unittest.main()
