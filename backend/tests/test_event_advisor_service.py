"""Event advisor service: mocked reads, no coupon write."""

from __future__ import annotations

import ast
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services import event_advisor_service as service_mod
from backend.services.event_advisor_config import AdvisorConfig
from backend.services.event_advisor_math import Candidate
from backend.services.event_advisor_math import TasteProfile
from backend.services.event_advisor_service import _cap_candidates
from backend.services.event_advisor_service import suggest_events
from backend.services.tipster_service import TipsterUnprocessableError


_NOW = datetime(2026, 10, 30, 12, 0)
_USER = {"id": 15}
_MODULE = "backend.services.event_advisor_service"
_HISTORY = f"{_MODULE}.advisor_repo.fetch_history"
_SLIP = f"{_MODULE}.advisor_repo.fetch_slip_leagues"
_CANDIDATES = f"{_MODULE}.advisor_repo.fetch_candidates"
_BETS = f"{_MODULE}.advisor_repo.fetch_computer_bet_pairs"
_FAVORITES = f"{_MODULE}.fetch_favorite_league_ids"
_FINGERPRINT = f"{_MODULE}.ready_model_fingerprint"
_CLOCK = f"{_MODULE}._warsaw_now"
_INSERT = "backend.repositories.tipster_repository.insert_coupon"
_SELECT = "backend.services.coupon_agent_selector.select_coupon"
_PUBLISH = "backend.services.coupon_agent_service.publish_daily"


class TestKoreaJapanSuggestion(unittest.TestCase):
    """Korean history and a Japanese draft both land in S."""

    def test_home_and_slip_leagues_are_s_and_foreign_is_out(self) -> None:
        request = {
            "legs": [
                {"match_id": 201, "event_ids": [7]},
                {"match_id": 202, "event_ids": [7]}]}
        with _reads(
                history=_korea_history(),
                slip={201: 2, 202: 2},
                candidates=_korea_pool(),
                bets={(101, 7), (102, 7)}) as mocks:
            payload = suggest_events(_USER, request)
        self.assertFalse(payload["cold_start"])
        self.assertEqual(payload["history_events"], 11)
        self.assertEqual(payload["odds_low"], 1.8)
        self.assertEqual(payload["odds_high"], 1.8)
        tiers = payload["tiers"]
        self.assertEqual(
            [row["league_id"] for row in tiers["S"]],
            [1, 2])
        self.assertEqual(tiers["A"], [])
        self.assertEqual(tiers["B"], [])
        self.assertNotIn(9, _league_ids(payload))
        home, slip = tiers["S"]
        self.assertEqual(f"{home['score']:.3f}", "1.000")
        self.assertEqual(f"{slip['score']:.3f}", "0.968")
        self.assertEqual(
            home["reasons"],
            ["computer_bet", "league_history", "event_history"])
        self.assertEqual(
            slip["reasons"],
            ["computer_bet", "league_on_slip", "event_history"])
        self.assertNotIn("league_history", slip["reasons"])
        self.assertEqual(home["match_id"], 101)
        self.assertEqual(home["event_id"], 7)
        self.assertEqual(home["event_name"], "Home win")
        self.assertEqual(home["league_name"], "K-League")
        self.assertEqual(home["home_name"], "Seoul")
        self.assertEqual(home["away_name"], "Busan")
        self.assertEqual(home["game_date"], "2026-11-02T18:00:00")
        self.assertEqual(f"{home['odds']:.2f}", "1.80")
        self.assertEqual(home["bookmaker_id"], 4)
        self.assertEqual(home["tier"], "S")
        mocks["history"].assert_called_once_with(
            15, _NOW - timedelta(days=180))
        mocks["favorites"].assert_called_once_with(15)
        mocks["slip"].assert_called_once_with([201, 202])
        mocks["candidates"].assert_called_once_with(
            _NOW, _NOW + timedelta(days=7))
        mocks["bets"].assert_called_once_with(
            "digest", _NOW, _NOW + timedelta(days=7))
        _assert_no_writes(mocks)


class TestMissingArtifact(unittest.TestCase):
    """No digest means no bet flag and still three tiers."""

    def test_none_fingerprint_skips_bet_pairs(self) -> None:
        with _reads(
                history=_korea_history(),
                slip={201: 2, 202: 2},
                candidates=_korea_pool(),
                bets={(101, 7), (102, 7)},
                fingerprint=None) as mocks:
            payload = suggest_events(_USER, _japan_slip())
        self.assertEqual(set(payload["tiers"]), {"S", "A", "B"})
        self.assertNotIn("computer_bet", _reasons(payload))
        mocks["bets"].assert_not_called()
        _assert_no_writes(mocks)

    def test_fingerprint_error_still_returns_three_tiers(self) -> None:
        with _reads(
                history=_korea_history(),
                candidates=_korea_pool(),
                fingerprint_error=RuntimeError("unreadable")) as mocks:
            payload = suggest_events(_USER, {"legs": []})
        self.assertEqual(set(payload["tiers"]), {"S", "A", "B"})
        self.assertNotIn("computer_bet", _reasons(payload))
        mocks["bets"].assert_not_called()
        _assert_no_writes(mocks)


class TestDraftValidation(unittest.TestCase):
    """Bad drafts fail before any read. A missing list is empty."""

    def test_duplicate_match_is_unprocessable(self) -> None:
        request = {"legs": [
            {"match_id": 10, "event_ids": [7]},
            {"match_id": 10, "event_ids": [8]}]}
        with _reads() as mocks:
            with self.assertRaises(TipsterUnprocessableError):
                suggest_events(_USER, request)
            mocks["history"].assert_not_called()

    def test_nine_legs_are_unprocessable(self) -> None:
        legs = [
            {"match_id": index, "event_ids": [7]}
            for index in range(1, 10)]
        with _reads() as mocks:
            with self.assertRaises(TipsterUnprocessableError):
                suggest_events(_USER, {"legs": legs})
            mocks["history"].assert_not_called()

    def test_bad_ids_are_unprocessable(self) -> None:
        cases = (
            {"legs": [{"match_id": 1, "event_ids": []}]},
            {"legs": [{"match_id": 1, "event_ids": [0]}]},
            {"legs": [{"match_id": 0, "event_ids": [7]}]},
            {"legs": [{"match_id": True, "event_ids": [7]}]},
            {"legs": [{"match_id": 1, "event_ids": ["x"]}]},
            {"legs": "nope"},
            ["not-a-request"])
        for request in cases:
            with self.subTest(request=request):
                with _reads() as mocks:
                    with self.assertRaises(TipsterUnprocessableError):
                        suggest_events(_USER, request)
                    mocks["history"].assert_not_called()

    def test_missing_legs_is_an_empty_slip(self) -> None:
        for request in ({}, None):
            with self.subTest(request=request):
                with _reads() as mocks:
                    payload = suggest_events(_USER, request)
                mocks["slip"].assert_called_once_with([])
                self.assertTrue(payload["cold_start"])
                self.assertEqual(payload["history_events"], 0)
                self.assertEqual(payload["tiers"]["S"], [])


class TestColdStartAndExclusions(unittest.TestCase):
    """Empty taste, unknown matches and prices under 1.01."""

    def test_empty_history_is_cold_start_and_writes_nothing(self) -> None:
        with _reads(history=[], favorites=[]) as mocks:
            payload = suggest_events(_USER, {"legs": []})
        self.assertTrue(payload["cold_start"])
        self.assertEqual(payload["history_events"], 0)
        self.assertIsNone(payload["odds_low"])
        self.assertIsNone(payload["odds_high"])
        self.assertEqual(payload["tiers"]["S"], [])
        self.assertEqual(payload["tiers"]["A"], [])
        self.assertEqual(payload["tiers"]["B"], [])
        _assert_no_writes(mocks)

    def test_unknown_slip_match_is_excluded(self) -> None:
        pool = [
            _pool_row(999, 7, 5, 1.80),
            _pool_row(50, 7, 5, 1.80)]
        with _reads(
                history=[],
                slip={},
                favorites=[5],
                candidates=pool,
                bets={(999, 7), (50, 7)}):
            payload = suggest_events(
                _USER,
                {"legs": [{"match_id": 999, "event_ids": [7]}]})
        self.assertEqual(_match_ids(payload), [50])
        self.assertNotIn(999, _match_ids(payload))

    def test_price_below_minimum_after_quantize_is_dropped(self) -> None:
        pool = [
            _pool_row(1, 7, 5, 1.004),
            _pool_row(2, 7, 5, 1.009)]
        with _reads(
                history=[],
                favorites=[5],
                candidates=pool,
                bets={(1, 7), (2, 7)}):
            payload = suggest_events(_USER, {"legs": []})
        self.assertEqual(_match_ids(payload), [2])
        kept = payload["tiers"]["S"][0]
        self.assertEqual(f"{kept['odds']:.2f}", "1.01")


class TestCandidateCap(unittest.TestCase):
    """Over 400 rows, protected buckets beat a later kickoff fill."""

    def test_bet_affinity_and_slip_beat_early_fillers(self) -> None:
        profile = TasteProfile(
            cold_start=False,
            history_events=11,
            league_affinity={1: 1.0},
            event_affinity={},
            odds_low=1.8,
            odds_high=1.8,
            favorite_league_ids=())
        kept = _cap_candidates(
            _overflow(protected=_history_protected()),
            profile,
            {2})
        self.assertEqual(len(kept), AdvisorConfig().max_scored_candidates)
        self.assertTrue({1001, 1002, 1003}.issubset(_ids(kept)))

    def test_cold_start_keeps_bet_slip_and_favorite(self) -> None:
        profile = TasteProfile(
            cold_start=True,
            history_events=0,
            league_affinity={},
            event_affinity={},
            odds_low=None,
            odds_high=None,
            favorite_league_ids=(5,))
        kept = _cap_candidates(
            _overflow(protected=_cold_protected()),
            profile,
            {2})
        self.assertEqual(len(kept), AdvisorConfig().max_scored_candidates)
        self.assertTrue({1001, 1003, 1004}.issubset(_ids(kept)))


class TestServiceModuleBoundary(unittest.TestCase):
    """The only agent import is the artifact digest."""

    def test_service_does_not_import_writes_or_the_selector(self) -> None:
        path = Path(service_mod.__file__)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("insert_coupon", text)
        self.assertNotIn("select_coupon", text)
        self.assertNotIn("publish_daily", text)
        self.assertNotIn("create_coupon", text)
        self.assertNotIn("model.joblib", text)
        tree = ast.parse(text)
        modules = _imported_modules(tree)
        self.assertNotIn("random", modules)
        agent = [name for name in modules if "coupon_agent" in name]
        self.assertEqual(
            agent,
            ["backend.repositories.coupon_agent_repository"])
        names = _imported_names(
            tree,
            "backend.repositories.coupon_agent_repository")
        self.assertEqual(names, ["ready_model_fingerprint"])


@contextmanager
def _reads(
        *,
        history: list[dict[str, Any]] | None = None,
        slip: dict[int, int] | None = None,
        candidates: list[dict[str, Any]] | None = None,
        bets: set[tuple[int, int]] | None = None,
        favorites: list[int] | None = None,
        fingerprint: str | None = "digest",
        fingerprint_error: Exception | None = None
        ) -> Iterator[dict[str, MagicMock]]:
    """Patch every read and every write the service could reach."""
    if fingerprint_error is None:
        gate = patch(_FINGERPRINT, return_value=fingerprint)
    else:
        gate = patch(_FINGERPRINT, side_effect=fingerprint_error)
    mocks: dict[str, MagicMock] = {}
    with patch(_HISTORY, return_value=_or_empty(history)) as history_mock, \
            patch(_SLIP, return_value=_or_mapping(slip)) as slip_mock, \
            patch(
                _CANDIDATES,
                return_value=_or_empty(candidates)) as pool_mock, \
            patch(_BETS, return_value=_or_pairs(bets)) as bet_mock, \
            patch(
                _FAVORITES,
                return_value=_or_empty(favorites)) as fav_mock, \
            patch(_CLOCK, return_value=_NOW), \
            patch(_INSERT) as insert_mock, \
            patch(_SELECT) as select_mock, \
            patch(_PUBLISH) as publish_mock, \
            gate as gate_mock:
        mocks["history"] = history_mock
        mocks["slip"] = slip_mock
        mocks["candidates"] = pool_mock
        mocks["bets"] = bet_mock
        mocks["favorites"] = fav_mock
        mocks["fingerprint"] = gate_mock
        mocks["insert"] = insert_mock
        mocks["select"] = select_mock
        mocks["publish"] = publish_mock
        yield mocks


def _assert_no_writes(mocks: dict[str, MagicMock]) -> None:
    """The suggestion path must not place or publish a coupon."""
    mocks["insert"].assert_not_called()
    mocks["select"].assert_not_called()
    mocks["publish"].assert_not_called()


def _or_empty(rows: list[Any] | None) -> list[Any]:
    """Return the given list, or a new empty one."""
    if rows is None:
        return []
    return rows


def _or_mapping(slip: dict[int, int] | None) -> dict[int, int]:
    """Return the given map, or a new empty one."""
    if slip is None:
        return {}
    return slip


def _or_pairs(
        bets: set[tuple[int, int]] | None) -> set[tuple[int, int]]:
    """Return the given pairs, or a new empty set."""
    if bets is None:
        return set()
    return bets


def _japan_slip() -> dict[str, Any]:
    """Two draft matches in league 2."""
    return {
        "legs": [
            {"match_id": 201, "event_ids": [7]},
            {"match_id": 202, "event_ids": [7]}]}


def _korea_history() -> list[dict[str, Any]]:
    """Ten events in league 1 and one in league 2, all single legs."""
    rows = [_history_row(1) for _ in range(10)]
    rows.append(_history_row(2))
    return rows


def _history_row(league_id: int) -> dict[str, Any]:
    return {
        "league_id": league_id,
        "event_id": 7,
        "odds": 1.80,
        "event_count_on_leg": 1}


def _korea_pool() -> list[dict[str, Any]]:
    """Home league, slip league, and a weak foreign league."""
    return [
        _pool_row(
            101, 7, 1, 1.80,
            league_name="K-League",
            home_name="Seoul",
            away_name="Busan",
            kickoff=datetime(2026, 11, 2, 18, 0)),
        _pool_row(
            102, 7, 2, 1.80,
            league_name="J-League",
            home_name="Tokyo",
            away_name="Osaka",
            kickoff=datetime(2026, 11, 1, 18, 0)),
        _pool_row(
            103, 99, 9, 4.50,
            probability=0.20,
            league_name="Other",
            kickoff=datetime(2026, 11, 1, 12, 0))]


def _pool_row(
        match_id: int,
        event_id: int,
        league_id: int,
        odds: float,
        *,
        probability: float = 0.55,
        league_name: str = "League",
        home_name: str = "Home",
        away_name: str = "Away",
        kickoff: datetime | None = None) -> dict[str, Any]:
    when = kickoff if kickoff is not None else datetime(2026, 11, 1, 18, 0)
    return {
        "match_id": match_id,
        "event_id": event_id,
        "event_name": "Home win",
        "league_id": league_id,
        "league_name": league_name,
        "home_name": home_name,
        "away_name": away_name,
        "kickoff": when,
        "odds": odds,
        "bookmaker_id": 4,
        "model_probability": probability}


def _overflow(*, protected: list[Candidate]) -> list[Candidate]:
    """Fill the cap with early weak rows, then the protected ones."""
    limit = AdvisorConfig().max_scored_candidates
    base = datetime(2026, 11, 1, 12, 0)
    fillers = [
        _input(index, 9, base + timedelta(minutes=index))
        for index in range(1, limit + 1)]
    return fillers + protected


def _history_protected() -> list[Candidate]:
    """A late bet, a high-affinity league and a slip league."""
    late = datetime(2026, 11, 8, 18, 0)
    return [
        _input(1001, 8, late, has_computer_bet=True),
        _input(1002, 1, late + timedelta(hours=1)),
        _input(1003, 2, late + timedelta(hours=2))]


def _cold_protected() -> list[Candidate]:
    """A late bet, a slip league and a favorite league."""
    late = datetime(2026, 11, 8, 18, 0)
    return [
        _input(1001, 8, late, has_computer_bet=True),
        _input(1003, 2, late + timedelta(hours=1)),
        _input(1004, 5, late + timedelta(hours=2))]


def _input(
        match_id: int,
        league_id: int,
        kickoff: datetime,
        *,
        has_computer_bet: bool = False) -> Candidate:
    return Candidate(
        match_id=match_id,
        event_id=7,
        event_name="Home win",
        league_id=league_id,
        league_name="League",
        home_name="Home",
        away_name="Away",
        kickoff=kickoff,
        odds=1.80,
        bookmaker_id=1,
        model_probability=0.55,
        has_computer_bet=has_computer_bet)


def _match_ids(payload: dict[str, Any]) -> list[int]:
    found: list[int] = []
    for rows in payload["tiers"].values():
        for row in rows:
            found.append(row["match_id"])
    return found


def _league_ids(payload: dict[str, Any]) -> set[int]:
    return {row["league_id"] for row in _rows(payload)}


def _reasons(payload: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for row in _rows(payload):
        found.update(row["reasons"])
    return found


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket in payload["tiers"].values():
        rows.extend(bucket)
    return rows


def _ids(rows: list[Candidate]) -> set[int]:
    return {row.match_id for row in rows}


def _imported_modules(tree: ast.AST) -> list[str]:
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def _imported_names(tree: ast.AST, module: str) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != module:
            continue
        names.extend(alias.name for alias in node.names)
    return names


if __name__ == "__main__":
    unittest.main()
