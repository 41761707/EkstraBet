"""Taste profile, scoring and S/A/B tiers for the event advisor."""

from __future__ import annotations

import ast
import unittest
from datetime import datetime
from pathlib import Path

from backend.services import event_advisor_math as math_mod
from backend.services.event_advisor_config import AdvisorConfig
from backend.services.event_advisor_math import (
    Candidate,
    HistoryRow,
    ScoredCandidate,
    TasteProfile,
    assign_tiers,
    build_profile,
    computer_score,
    event_weight,
    keep_best_event_per_match,
    league_weight,
    odds_fit_score,
    score_candidate)


_REASONS = {
    "computer_bet",
    "league_on_slip",
    "league_history",
    "event_history",
    "odds_in_band",
    "computer_lean"}


class TestAdvisorConfig(unittest.TestCase):
    """Defaults are the scoring contract from the design."""

    def test_contract_defaults(self) -> None:
        cfg = AdvisorConfig()
        self.assertEqual(cfg.history_days, 180)
        self.assertEqual(cfg.horizon_days, 7)
        self.assertEqual(cfg.cold_start_min_events, 8)
        self.assertEqual(cfg.max_scored_candidates, 400)
        self.assertEqual(cfg.w_league, 0.65)
        self.assertEqual(cfg.w_event, 0.35)
        self.assertEqual(cfg.slip_league_floor, 0.85)
        self.assertEqual(cfg.odds_band_floor, 0.30)
        self.assertEqual(cfg.computer_bet, 1.0)
        self.assertEqual(cfg.computer_lean, 0.65)
        self.assertEqual(cfg.computer_fair, 0.40)
        self.assertEqual(cfg.computer_weak, 0.15)
        self.assertEqual(cfg.lean_min_probability, 0.45)
        self.assertEqual(cfg.lean_max_abs_edge_pp, 12.0)
        self.assertEqual(cfg.tier_s_min, 0.72)
        self.assertEqual(cfg.tier_a_min, 0.55)
        self.assertEqual(cfg.tier_b_min, 0.40)
        self.assertEqual(cfg.tier_s_min_computer, 0.65)
        self.assertEqual(cfg.tier_s_min_odds_fit, 0.50)
        self.assertEqual(cfg.tier_caps, {"S": 3, "A": 4, "B": 4})
        self.assertEqual(cfg.reason_limit, 3)

    def test_tier_caps_are_not_shared_between_instances(self) -> None:
        first = AdvisorConfig()
        second = AdvisorConfig()
        first.tier_caps["S"] = 9
        self.assertEqual(second.tier_caps["S"], 3)


class TestKoreaJapanExample(unittest.TestCase):
    """Ten Korean events and one Japanese event, slip in Japan."""

    def setUp(self) -> None:
        self.profile = build_profile(_korea_japan_rows(), ())
        self.slip = frozenset({2})

    def test_affinity_and_slip_floor(self) -> None:
        profile = self.profile
        self.assertFalse(profile.cold_start)
        self.assertEqual(profile.history_events, 11)
        self.assertAlmostEqual(profile.league_affinity[1], 1.0)
        self.assertAlmostEqual(profile.league_affinity[2], 0.1)
        self.assertAlmostEqual(profile.event_affinity[7], 1.0)
        self.assertEqual(profile.odds_low, 1.80)
        self.assertEqual(profile.odds_high, 1.80)
        self.assertEqual(league_weight(1, profile, self.slip), 1.0)
        self.assertAlmostEqual(
            league_weight(2, profile, set()), 0.1)
        self.assertEqual(league_weight(2, profile, self.slip), 0.85)
        self.assertEqual(league_weight(9, profile, self.slip), 0.0)

    def test_home_league_with_a_bet_is_tier_s(self) -> None:
        scored = score_candidate(
            _candidate(101, 7, 1, 1.80, has_computer_bet=True),
            self.profile,
            self.slip)
        self.assertEqual(scored.score, 1.0)
        self.assertEqual(scored.computer, 1.0)
        self.assertEqual(scored.odds_fit, 1.0)
        self.assertEqual(
            scored.reasons,
            ("computer_bet", "league_history", "event_history"))

    def test_slip_league_with_a_bet_is_tier_s(self) -> None:
        scored = score_candidate(
            _candidate(102, 7, 2, 1.80, has_computer_bet=True),
            self.profile,
            self.slip)
        self.assertAlmostEqual(scored.score, 0.9675, places=4)
        self.assertAlmostEqual(scored.score, 0.968, delta=0.001)
        self.assertIn("league_on_slip", scored.reasons)
        self.assertNotIn("league_history", scored.reasons)
        self.assertEqual(
            scored.reasons,
            ("computer_bet", "league_on_slip", "event_history"))

    def test_foreign_league_falls_out_of_every_tier(self) -> None:
        foreign = score_candidate(
            _candidate(
                103, 99, 9, 4.50,
                has_computer_bet=False,
                model_probability=0.20),
            self.profile,
            self.slip)
        self.assertEqual(foreign.computer, 0.15)
        self.assertEqual(foreign.odds_fit, 0.0)
        self.assertAlmostEqual(foreign.score, 0.05, places=4)
        tiers = _tiers_for(self.profile, self.slip)
        self.assertEqual(
            [row.league_id for row in tiers["S"]],
            [1, 2])
        self.assertEqual(tiers["A"], [])
        self.assertEqual(tiers["B"], [])
        self.assertNotIn(9, _league_ids(tiers))

    def test_ten_identical_tier_calls_keep_order(self) -> None:
        first = _tiers_for(self.profile, self.slip)
        for _ in range(9):
            self.assertEqual(_tiers_for(self.profile, self.slip), first)
        for row in first["S"] + first["A"] + first["B"]:
            self.assertLessEqual(len(row.reasons), 3)
            self.assertTrue(set(row.reasons).issubset(_REASONS))
            self.assertFalse(
                "computer_bet" in row.reasons
                and "computer_lean" in row.reasons)


class TestBestEventPerMatch(unittest.TestCase):
    """One match keeps a single event."""

    def test_higher_score_wins(self) -> None:
        low = _scored(10, 1, 0.50, datetime(2026, 11, 1))
        high = _scored(10, 9, 0.90, datetime(2026, 11, 2))
        kept = keep_best_event_per_match([low, high])
        self.assertEqual([row.event_id for row in kept], [9])
        tiers = assign_tiers([low, high])
        self.assertEqual(
            [row.event_id for row in tiers["S"]],
            [9])
        self.assertEqual(tiers["A"], [])
        self.assertEqual(tiers["B"], [])

    def test_tie_keeps_the_lower_event_id(self) -> None:
        later_id = _scored(11, 8, 0.70, datetime(2026, 11, 1))
        earlier_id = _scored(11, 4, 0.70, datetime(2026, 11, 2))
        kept = keep_best_event_per_match([later_id, earlier_id])
        self.assertEqual([row.event_id for row in kept], [4])
        tiers = assign_tiers([later_id, earlier_id])
        self.assertEqual(
            [row.event_id for row in tiers["A"]],
            [4])
        self.assertEqual(tiers["S"], [])
        self.assertEqual(tiers["B"], [])


class TestColdStart(unittest.TestCase):
    """Fewer than eight events ignores history and uses favorites."""

    def test_seven_events_are_cold_start(self) -> None:
        rows = [_row(3, 7, 1.80) for _ in range(7)]
        profile = build_profile(rows, (5,))
        self.assertTrue(profile.cold_start)
        self.assertEqual(profile.history_events, 7)
        self.assertEqual(profile.league_affinity, {})
        self.assertEqual(profile.event_affinity, {})
        self.assertIsNone(profile.odds_low)
        self.assertIsNone(profile.odds_high)
        self.assertEqual(profile.favorite_league_ids, (5,))
        self.assertEqual(league_weight(5, profile, set()), 1.0)
        self.assertEqual(league_weight(3, profile, set()), 0.15)
        self.assertEqual(league_weight(3, profile, {3}), 0.85)
        self.assertEqual(event_weight(7, profile), 0.50)
        self.assertEqual(event_weight(99, profile), 0.50)
        self.assertEqual(odds_fit_score(4.50, profile), 0.50)
        scored = score_candidate(
            _candidate(1, 7, 5, 1.80, has_computer_bet=True),
            profile,
            set())
        self.assertNotIn("league_history", scored.reasons)
        self.assertEqual(scored.reasons, ("computer_bet",))

    def test_cold_flag_hides_event_and_band_reasons(self) -> None:
        cold = _profile(
            cold_start=True,
            event_affinity={7: 1.0},
            odds_low=1.50,
            odds_high=2.20)
        warm = _profile(
            cold_start=False,
            history_events=8,
            event_affinity={7: 1.0},
            odds_low=1.50,
            odds_high=2.20)
        candidate = _candidate(
            1, 7, 1, 1.80, model_probability=0.55)
        cold_reasons = score_candidate(
            candidate, cold, set()).reasons
        warm_reasons = score_candidate(
            candidate, warm, set()).reasons
        self.assertNotIn("event_history", cold_reasons)
        self.assertNotIn("odds_in_band", cold_reasons)
        self.assertEqual(
            warm_reasons,
            ("event_history", "odds_in_band", "computer_lean"))


class TestOddsBand(unittest.TestCase):
    """Quartiles use single-event prices only."""

    def test_one_single_price_sets_both_ends(self) -> None:
        rows = [_row(1, 7, 9.99, 2) for _ in range(7)]
        rows.append(_row(1, 7, 1.70, 1))
        profile = build_profile(rows, ())
        self.assertFalse(profile.cold_start)
        self.assertEqual(profile.odds_low, 1.70)
        self.assertEqual(profile.odds_high, 1.70)

    def test_percentiles_skip_combined_prices(self) -> None:
        rows = [_row(1, 7, price, 1) for price in (1.0, 2.0, 3.0, 4.0)]
        rows.extend(_row(1, 7, 100.0, 2) for _ in range(4))
        profile = build_profile(rows, ())
        self.assertAlmostEqual(profile.odds_low, 1.75)
        self.assertAlmostEqual(profile.odds_high, 3.25)
        self.assertAlmostEqual(profile.league_affinity[1], 1.0)

    def test_combined_only_history_has_no_band(self) -> None:
        rows = [_row(1, 7, 3.50, 2) for _ in range(8)]
        profile = build_profile(rows, ())
        self.assertFalse(profile.cold_start)
        self.assertIsNone(profile.odds_low)
        self.assertIsNone(profile.odds_high)
        self.assertEqual(odds_fit_score(9.0, profile), 0.50)

    def test_price_falls_off_outside_a_narrow_band(self) -> None:
        profile = _profile(
            cold_start=False,
            history_events=8,
            odds_low=1.80,
            odds_high=1.80)
        self.assertEqual(odds_fit_score(1.80, profile), 1.0)
        self.assertAlmostEqual(odds_fit_score(1.65, profile), 0.5)
        self.assertAlmostEqual(odds_fit_score(1.95, profile), 0.5)
        self.assertEqual(odds_fit_score(1.50, profile), 0.0)
        self.assertEqual(odds_fit_score(2.10, profile), 0.0)
        self.assertEqual(odds_fit_score(4.50, profile), 0.0)


class TestComputerScore(unittest.TestCase):
    """Bet, lean, fair, weak and the early zeros."""

    def test_bet_flag_is_the_top_score(self) -> None:
        self.assertEqual(computer_score(None, 1.0, True), 1.0)
        self.assertEqual(computer_score(0.20, 4.50, True), 1.0)

    def test_missing_probability_or_short_price_is_zero(self) -> None:
        self.assertEqual(computer_score(None, 1.80, False), 0.0)
        self.assertEqual(computer_score(0.60, 1.0, False), 0.0)
        self.assertEqual(computer_score(0.60, 0.90, False), 0.0)

    def test_lean_fair_and_weak_bands(self) -> None:
        self.assertEqual(computer_score(0.55, 2.0, False), 0.65)
        self.assertEqual(computer_score(0.45, 2.0, False), 0.65)
        self.assertEqual(computer_score(0.80, 2.0, False), 0.40)
        self.assertEqual(computer_score(0.20, 2.0, False), 0.15)


class TestAssignTiers(unittest.TestCase):
    """Caps, gates and a stable order."""

    def test_sort_uses_kickoff_then_ids(self) -> None:
        later = _scored(1, 2, 0.90, datetime(2026, 11, 5))
        earlier = _scored(2, 1, 0.90, datetime(2026, 11, 1))
        weaker = _scored(3, 1, 0.80, datetime(2026, 11, 3))
        tiers = assign_tiers([weaker, later, earlier])
        self.assertEqual(
            [row.match_id for row in tiers["S"]],
            [2, 1, 3])

    def test_same_kickoff_orders_by_match_id(self) -> None:
        kickoff = datetime(2026, 11, 1, 18, 0)
        tiers = assign_tiers([
            _scored(5, 1, 0.90, kickoff),
            _scored(2, 1, 0.90, kickoff)])
        self.assertEqual(
            [row.match_id for row in tiers["S"]],
            [2, 5])

    def test_tier_s_stops_at_three(self) -> None:
        rows = [
            _scored(match_id, 1, 0.90, datetime(2026, 11, match_id))
            for match_id in range(1, 6)]
        tiers = assign_tiers(rows)
        self.assertEqual(
            [row.match_id for row in tiers["S"]],
            [1, 2, 3])
        self.assertEqual(tiers["A"], [])
        self.assertEqual(tiers["B"], [])

    def test_s_requires_computer_and_odds_fit(self) -> None:
        kickoff = datetime(2026, 11, 1)
        weak_computer = _scored(
            1, 1, 0.80, kickoff, computer=0.40, odds_fit=1.0)
        weak_odds = _scored(
            2, 1, 0.80, kickoff, computer=1.0, odds_fit=0.49)
        exact_s = _scored(
            3, 1, 0.72, kickoff, computer=0.65, odds_fit=0.50)
        tiers = assign_tiers([weak_computer, weak_odds, exact_s])
        self.assertEqual(
            [row.match_id for row in tiers["S"]],
            [3])
        self.assertEqual(
            [row.match_id for row in tiers["A"]],
            [1, 2])

    def test_b_is_the_floor_and_below_it_drops(self) -> None:
        kickoff = datetime(2026, 11, 1)
        in_b = _scored(1, 1, 0.40, kickoff, computer=0.15, odds_fit=0.0)
        below = _scored(2, 1, 0.39, kickoff, computer=1.0, odds_fit=1.0)
        tiers = assign_tiers([below, in_b])
        self.assertEqual(tiers["S"], [])
        self.assertEqual(tiers["A"], [])
        self.assertEqual([row.match_id for row in tiers["B"]], [1])

    def test_empty_input_has_three_empty_tiers(self) -> None:
        self.assertEqual(
            assign_tiers([]),
            {"S": [], "A": [], "B": []})

    def test_league_history_starts_at_half_affinity(self) -> None:
        profile = _profile(
            cold_start=False,
            history_events=8,
            league_affinity={1: 0.50, 2: 0.49})
        at_half = score_candidate(
            _candidate(1, 1, 1, 2.0, has_computer_bet=True),
            profile,
            set())
        below = score_candidate(
            _candidate(2, 1, 2, 2.0, has_computer_bet=True),
            profile,
            set())
        self.assertIn("league_history", at_half.reasons)
        self.assertNotIn("league_history", below.reasons)


class TestMathModuleBoundary(unittest.TestCase):
    """Scoring stays free of I/O, HTTP and randomness."""

    def test_modules_do_not_import_io_or_random(self) -> None:
        root = Path(math_mod.__file__).resolve().parent
        names = (
            "event_advisor_config.py",
            "event_advisor_math.py")
        forbidden = ("api", "repositories", "random")
        for name in names:
            tree = ast.parse((root / name).read_text(encoding="utf-8"))
            for module_name in _imported_modules(tree):
                parts = module_name.split(".")
                for token in forbidden:
                    self.assertNotIn(token, parts)


def _korea_japan_rows() -> list[HistoryRow]:
    rows = [_row(1, 7, 1.80) for _ in range(10)]
    rows.append(_row(2, 7, 1.80))
    return rows


def _tiers_for(
        profile: TasteProfile,
        slip: frozenset[int]) -> dict[str, list[ScoredCandidate]]:
    rows = [
        score_candidate(
            _candidate(
                103, 99, 9, 4.50,
                has_computer_bet=False,
                model_probability=0.20),
            profile,
            slip),
        score_candidate(
            _candidate(102, 7, 2, 1.80, has_computer_bet=True),
            profile,
            slip),
        score_candidate(
            _candidate(101, 7, 1, 1.80, has_computer_bet=True),
            profile,
            slip)]
    return assign_tiers(rows)


def _league_ids(
        tiers: dict[str, list[ScoredCandidate]]) -> set[int]:
    found: set[int] = set()
    for bucket in tiers.values():
        for row in bucket:
            found.add(row.league_id)
    return found


def _row(
        league_id: int,
        event_id: int,
        odds: float,
        event_count_on_leg: int = 1) -> HistoryRow:
    return HistoryRow(
        league_id=league_id,
        event_id=event_id,
        odds=odds,
        event_count_on_leg=event_count_on_leg)


def _candidate(
        match_id: int,
        event_id: int,
        league_id: int,
        odds: float,
        *,
        has_computer_bet: bool = False,
        model_probability: float | None = 0.55,
        kickoff: datetime | None = None) -> Candidate:
    when = kickoff if kickoff is not None else datetime(2026, 11, 1, 18, 0)
    return Candidate(
        match_id=match_id,
        event_id=event_id,
        event_name="Home win",
        league_id=league_id,
        league_name="League",
        home_name="Home",
        away_name="Away",
        kickoff=when,
        odds=odds,
        bookmaker_id=1,
        model_probability=model_probability,
        has_computer_bet=has_computer_bet)


def _scored(
        match_id: int,
        event_id: int,
        score: float,
        kickoff: datetime,
        *,
        computer: float = 1.0,
        odds_fit: float = 1.0) -> ScoredCandidate:
    return ScoredCandidate(
        match_id=match_id,
        event_id=event_id,
        event_name="Home win",
        league_id=1,
        league_name="League",
        home_name="Home",
        away_name="Away",
        kickoff=kickoff,
        odds=1.80,
        bookmaker_id=1,
        model_probability=0.60,
        has_computer_bet=True,
        score=score,
        computer=computer,
        odds_fit=odds_fit,
        reasons=())


def _profile(
        *,
        cold_start: bool,
        history_events: int = 7,
        league_affinity: dict[int, float] | None = None,
        event_affinity: dict[int, float] | None = None,
        odds_low: float | None = None,
        odds_high: float | None = None,
        favorite_league_ids: tuple[int, ...] = ()) -> TasteProfile:
    return TasteProfile(
        cold_start=cold_start,
        history_events=history_events,
        league_affinity=league_affinity or {},
        event_affinity=event_affinity or {},
        odds_low=odds_low,
        odds_high=odds_high,
        favorite_league_ids=favorite_league_ids)


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
