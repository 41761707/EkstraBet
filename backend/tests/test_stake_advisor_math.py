"""Blend, joint probability, fractional Kelly and stake caps."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from backend.services import stake_advisor_math as math_mod
from backend.services.stake_advisor_config import AdvisorWeights
from backend.services.stake_advisor_math import (
    LIMIT_BANKROLL_PCT,
    LIMIT_MAX_UNITS,
    apply_caps,
    blend_probability,
    fractional_kelly,
    joint_probability)


_CFG = AdvisorWeights()


class TestBlendProbability(unittest.TestCase):
    """User confidence and the agent flag move the blended probability."""

    def test_confidence_zero_and_full_change_the_blend(self) -> None:
        low = blend_probability(0.55, 0.50, 0.0, False, _CFG)
        high = blend_probability(0.55, 0.50, 1.0, False, _CFG)
        expected_low = 0.50 * 0.55 + 0.35 * 0.01 + 0.15 * 0.50
        expected_high = 0.50 * 0.55 + 0.35 * 0.99 + 0.15 * 0.50
        self.assertAlmostEqual(low, expected_low)
        self.assertAlmostEqual(high, expected_high)
        self.assertGreater(high, low)

    def test_agent_liked_adds_the_configured_boost(self) -> None:
        plain = blend_probability(0.55, 0.50, 0.70, False, _CFG)
        boosted = blend_probability(0.55, 0.50, 0.70, True, _CFG)
        self.assertAlmostEqual(boosted, plain + _CFG.agent_boost)

    def test_missing_model_uses_user_and_implied_only(self) -> None:
        blended = blend_probability(None, 0.50, 0.70, False, _CFG)
        user_weight = 0.35 + 0.50 * 0.7
        implied_weight = 0.15 + 0.50 * 0.3
        expected = user_weight * 0.70 + implied_weight * 0.50
        self.assertAlmostEqual(blended, expected)

    def test_boost_cannot_leave_the_clip_band(self) -> None:
        capped = blend_probability(0.99, 0.99, 1.0, True, _CFG)
        self.assertAlmostEqual(capped, 0.99)


class TestJointProbability(unittest.TestCase):
    """Accumulator probability is the product of leg probabilities."""

    def test_product_of_two_legs(self) -> None:
        self.assertAlmostEqual(joint_probability([0.5, 0.8]), 0.4)

    def test_single_leg_is_unchanged(self) -> None:
        self.assertAlmostEqual(joint_probability([0.62]), 0.62)

    def test_empty_list_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            joint_probability([])


class TestFractionalKelly(unittest.TestCase):
    """Negative edge and a price at or below 1 stake nothing."""

    def test_negative_edge_is_zero(self) -> None:
        self.assertEqual(fractional_kelly(0.40, 2.0, 0.25), 0.0)

    def test_positive_edge_scales_by_the_fraction(self) -> None:
        self.assertAlmostEqual(fractional_kelly(0.60, 2.0, 0.25), 0.05)

    def test_price_at_one_is_zero(self) -> None:
        self.assertEqual(fractional_kelly(0.90, 1.0, 0.25), 0.0)


class TestApplyCaps(unittest.TestCase):
    """Bankroll share and max units both limit the suggested stake."""

    def test_max_units_caps_a_large_raw_stake(self) -> None:
        stake, limits = apply_caps(100.0, 10000.0, 10.0, _CFG)
        self.assertEqual(stake, 50.0)
        self.assertEqual(limits, [LIMIT_MAX_UNITS])

    def test_negative_balance_still_caps_from_unit_size(self) -> None:
        stake, limits = apply_caps(5.0, -100.0, 10.0, _CFG)
        self.assertEqual(stake, 1.0)
        self.assertEqual(limits, [LIMIT_BANKROLL_PCT])

    def test_both_caps_are_reported_in_order(self) -> None:
        stake, limits = apply_caps(500.0, 1000.0, 10.0, _CFG)
        self.assertEqual(stake, 50.0)
        self.assertEqual(limits, [LIMIT_BANKROLL_PCT, LIMIT_MAX_UNITS])

    def test_stake_under_both_caps_is_unchanged(self) -> None:
        stake, limits = apply_caps(1.235, 1000.0, 10.0, _CFG)
        self.assertEqual(stake, 1.24)
        self.assertEqual(limits, [])

    def test_bankroll_cap_floors_a_fractional_cent(self) -> None:
        stake, limits = apply_caps(20.0, 100.05, 10.0, _CFG)
        self.assertEqual(stake, 10.0)
        self.assertEqual(limits, [LIMIT_BANKROLL_PCT])

    def test_tiny_basis_does_not_round_the_cap_above_the_share(self) -> None:
        stake, limits = apply_caps(1.0, 0.05, 0.05, _CFG)
        self.assertEqual(stake, 0.0)
        self.assertEqual(limits, [LIMIT_BANKROLL_PCT])

    def test_zero_unit_size_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            apply_caps(1.0, 100.0, 0.0, _CFG)


class TestMathModuleBoundary(unittest.TestCase):
    """The math package stays free of HTTP and repository imports."""

    def test_config_and_math_do_not_import_api_or_repositories(self) -> None:
        root = Path(math_mod.__file__).resolve().parent
        names = (
            "stake_advisor_config.py",
            "stake_advisor_math.py")
        for name in names:
            tree = ast.parse((root / name).read_text(encoding="utf-8"))
            imported = _imported_modules(tree)
            for module_name in imported:
                self.assertNotIn("api", module_name.split("."))
                self.assertNotIn("repositories", module_name.split("."))


def _imported_modules(tree: ast.AST) -> list[str]:
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


if __name__ == "__main__":
    unittest.main()
