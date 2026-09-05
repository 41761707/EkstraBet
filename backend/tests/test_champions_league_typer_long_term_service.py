"""Unit tests for Typer long-term scoring, completeness and settlement."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from backend.repositories import (
    champions_league_typer_long_term_repository as repo)
from backend.services import (
    champions_league_typer_long_term_service as service)


_REPO = (
    "backend.services.champions_league_typer_long_term_service.repository")
_MARKET_ID = 20
_ADMIN_ID = 7
_SEASON_ID = 13
_TEAM_IDS = [12, 45, 101, 200, 201, 202, 203, 204]
_TABLE_SIZE = 36
_TOP_ZONE = 8
_BOT_ZONE = 8
_POINTS_ZONE = 2.0
_POINTS_EXACT = 2.0
_BARCELONA_ID = 6
_PICK_FILLERS = list(range(201, 237))
_RESULT_FILLERS = list(range(301, 337))
_SETTLED_AT = datetime(2026, 12, 1, 23, 0)
_ADMIN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_FETCH_USER = (
    "backend.services.champions_league_typer_long_term_service"
    ".user_repository.fetch_user_by_id")
_ADMIN_USER = {
    "id": _ADMIN_ID,
    "uuid": _ADMIN_UUID,
    "display_name": "Admin"
}


def _standing_row(
        team_id: int,
        *,
        played: int = 8,
        points: int = 12) -> dict[str, object]:
    return {
        "team_id": team_id,
        "team_name": f"Team {team_id}",
        "team_shortcut": f"T{team_id}",
        "played": played,
        "points": points,
        "goal_difference": team_id,
        "goals_for": team_id * 2
    }


def _auto_result_document(
        *,
        participant_count: int = 36,
        min_matches: int = 8,
        max_matches: int = 8,
        settled_matches: int = 144,
        standings: list[dict[str, object]] | None = None,
        settled_at: datetime | None = None,
        settled_by: int | None = None,
        result_team_ids: list[int] | None = None
        ) -> dict[str, object]:
    rows = standings if standings is not None else [
        _standing_row(team_id) for team_id in range(1, 37)]
    return {
        "market_id": _MARKET_ID,
        "league_id": repo.CHAMPIONS_LEAGUE_ID,
        "season_id": _SEASON_ID,
        "market_key": "league_phase_table",
        "selection_size": _TABLE_SIZE,
        "points_per_correct": 2.0,
        "points_per_exact_position": 2.0,
        "market_kind": service.MARKET_KIND_RANKED_TEAM_TABLE,
        "scoring_kind": service.SCORING_KIND_ZONE_AND_POSITION,
        "top_zone_size": _TOP_ZONE,
        "bot_zone_size": _BOT_ZONE,
        "settled_at": settled_at,
        "settled_by": settled_by,
        "participant_count": participant_count,
        "settled_match_count": settled_matches,
        "min_matches_per_team": min_matches,
        "max_matches_per_team": max_matches,
        "standings": rows,
        "result_team_ids": (
            [] if result_team_ids is None else list(result_team_ids))
    }


def _dashboard_market_row(
        *,
        picked_team_ids: list[int] | None = None,
        result_team_ids: list[int] | None = None,
        settled_at: datetime | None = None,
        settled_by: int | None = None,
        is_locked: bool = False
        ) -> dict[str, object]:
    return {
        "market_id": _MARKET_ID,
        "league_id": repo.CHAMPIONS_LEAGUE_ID,
        "season_id": _SEASON_ID,
        "market_key": "league_phase_table",
        "title": "Tabela fazy ligowej",
        "description": None,
        "selection_size": _TABLE_SIZE,
        "points_per_correct": _POINTS_ZONE,
        "points_per_exact_position": _POINTS_EXACT,
        "market_kind": service.MARKET_KIND_RANKED_TEAM_TABLE,
        "scoring_kind": service.SCORING_KIND_ZONE_AND_POSITION,
        "top_zone_size": _TOP_ZONE,
        "bot_zone_size": _BOT_ZONE,
        "settled_at": settled_at,
        "settled_by": settled_by,
        "deadline_at": _SETTLED_AT,
        "is_locked": is_locked,
        "candidates": [],
        "picked_team_ids": (
            [] if picked_team_ids is None else list(picked_team_ids)),
        "result_team_ids": (
            [] if result_team_ids is None else list(result_team_ids))
    }


def _table_with_team_at(
        fillers: list[int],
        team_id: int,
        position: int) -> list[int]:
    table = list(fillers)
    table[position - 1] = team_id
    return table


def _score_ranked(
        pick_position: int,
        result_position: int,
        *,
        team_id: int = _BARCELONA_ID,
        points_per_correct: float = _POINTS_ZONE,
        points_per_exact: float = _POINTS_EXACT) -> float:
    return service.score_long_term(
        service.SCORING_KIND_ZONE_AND_POSITION,
        _table_with_team_at(_PICK_FILLERS, team_id, pick_position),
        _table_with_team_at(_RESULT_FILLERS, team_id, result_position),
        points_per_correct,
        points_per_exact,
        _TOP_ZONE,
        _BOT_ZONE)


class TestScoreLongTerm(unittest.TestCase):
    """Ranked table: zone points plus exact-position bonus."""

    def test_barcelona_outside_top_eight_is_zero(self) -> None:
        self.assertEqual(_score_ranked(6, 13), 0.0)

    def test_barcelona_in_top_eight_wrong_place(self) -> None:
        self.assertEqual(_score_ranked(6, 2), _POINTS_ZONE)

    def test_barcelona_exact_sixth_place(self) -> None:
        self.assertEqual(
            _score_ranked(6, 6), _POINTS_ZONE + _POINTS_EXACT)

    def test_bot_eight_outside_zone_is_zero(self) -> None:
        self.assertEqual(_score_ranked(36, 20), 0.0)

    def test_bot_eight_wrong_place(self) -> None:
        self.assertEqual(_score_ranked(36, 30), _POINTS_ZONE)

    def test_bot_eight_exact_place(self) -> None:
        self.assertEqual(
            _score_ranked(36, 36), _POINTS_ZONE + _POINTS_EXACT)

    def test_middle_slot_does_not_score(self) -> None:
        self.assertEqual(_score_ranked(9, 2), 0.0)

    def test_uses_market_rates_not_fixed_two(self) -> None:
        self.assertEqual(
            _score_ranked(6, 2, points_per_correct=1.5, points_per_exact=0.5),
            1.5)
        self.assertEqual(
            _score_ranked(6, 6, points_per_correct=1.5, points_per_exact=0.5),
            2.0)

    def test_unknown_scoring_kind_is_zero(self) -> None:
        picks = _table_with_team_at(_PICK_FILLERS, _BARCELONA_ID, 6)
        results = _table_with_team_at(_RESULT_FILLERS, _BARCELONA_ID, 6)
        self.assertEqual(
            service.score_long_term(
                "exact_subject",
                picks,
                results,
                _POINTS_ZONE,
                _POINTS_EXACT,
                _TOP_ZONE,
                _BOT_ZONE),
            0.0)

    def test_zone_for_position_top_middle_bot(self) -> None:
        self.assertEqual(
            service.zone_for_position(1, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE),
            "top")
        self.assertEqual(
            service.zone_for_position(8, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE),
            "top")
        self.assertIsNone(
            service.zone_for_position(9, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE))
        self.assertIsNone(
            service.zone_for_position(28, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE))
        self.assertEqual(
            service.zone_for_position(29, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE),
            "bot")
        self.assertEqual(
            service.zone_for_position(36, _TABLE_SIZE, _TOP_ZONE, _BOT_ZONE),
            "bot")


class TestLeaguePhaseComplete(unittest.TestCase):
    """Completeness requires 36 participants, 8 matches each, 144 matches."""

    def test_complete_phase(self) -> None:
        self.assertTrue(
            service.is_league_phase_complete(_auto_result_document()))

    def test_incomplete_when_missing_teams(self) -> None:
        self.assertFalse(
            service.is_league_phase_complete(
                _auto_result_document(participant_count=35)))

    def test_incomplete_when_team_missing_matches(self) -> None:
        self.assertFalse(
            service.is_league_phase_complete(
                _auto_result_document(
                    min_matches=7, settled_matches=143)))


class TestGetAutoResult(unittest.TestCase):
    """Proposal is empty until the league phase is complete."""

    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_has_no_proposed_teams(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = _auto_result_document(
            min_matches=7, max_matches=8, settled_matches=140)
        document = service.get_auto_result(_MARKET_ID)
        self.assertFalse(document["is_complete"])
        self.assertTrue(document["is_proposal"])
        self.assertEqual(document["proposed_team_ids"], [])
        self.assertEqual(document["proposed_top_team_ids"], [])
        self.assertEqual(document["proposed_bot_team_ids"], [])
        self.assertEqual(document["proposed_teams"], [])
        self.assertEqual(document["result_team_ids"], [])
        mock_fetch.assert_called_once_with(_MARKET_ID)

    @patch(f"{_REPO}.fetch_auto_result")
    def test_complete_phase_proposes_full_table(
            self, mock_fetch: MagicMock) -> None:
        standings = [
            _standing_row(team_id, points=40 - team_id)
            for team_id in range(1, 37)]
        mock_fetch.return_value = _auto_result_document(standings=standings)
        document = service.get_auto_result(_MARKET_ID)
        self.assertTrue(document["is_complete"])
        self.assertTrue(document["is_proposal"])
        self.assertEqual(len(document["proposed_team_ids"]), 36)
        self.assertEqual(
            document["proposed_team_ids"], list(range(1, 37)))
        self.assertEqual(len(document["proposed_teams"]), 36)
        self.assertEqual(
            document["proposed_top_team_ids"], list(range(1, 9)))
        self.assertEqual(
            document["proposed_bot_team_ids"], list(range(29, 37)))
        self.assertEqual(document["top_zone_size"], _TOP_ZONE)
        self.assertEqual(document["bot_zone_size"], _BOT_ZONE)
        self.assertEqual(document["points_per_exact_position"], 2.0)

    @patch(f"{_REPO}.fetch_auto_result")
    def test_table_ties_keep_sql_order_for_eighth_place(
            self, mock_fetch: MagicMock) -> None:
        # remis punktów/GD rozstrzyga SQL (gole); serwis nie przestawia
        standings = [
            _standing_row(team_id, points=12)
            for team_id in range(1, 37)]
        mock_fetch.return_value = _auto_result_document(standings=standings)
        document = service.get_auto_result(_MARKET_ID)
        self.assertEqual(document["proposed_team_ids"][7], 8)
        self.assertEqual(document["proposed_team_ids"][8], 9)
        self.assertEqual(document["proposed_top_team_ids"][-1], 8)
        self.assertNotIn(9, document["proposed_top_team_ids"])


class TestSettleMarket(unittest.TestCase):
    """Settlement awards points only after a complete phase and admin write."""

    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_does_not_write(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_fetch.return_value = _auto_result_document(
            participant_count=36,
            min_matches=7,
            max_matches=8,
            settled_matches=140)
        with self.assertRaises(service.TyperConflictError):
            service.settle_market(_MARKET_ID, list(_TEAM_IDS), _ADMIN_ID)
        mock_settle.assert_not_called()

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_complete_phase_writes_admin_set(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock,
            _mock_user: MagicMock) -> None:
        mock_fetch.return_value = _auto_result_document()
        mock_settle.return_value = {
            "market_id": _MARKET_ID,
            "team_ids": list(_TEAM_IDS),
            "settled_by": _ADMIN_ID,
            "settled_at": _SETTLED_AT,
            "result_team_ids": list(_TEAM_IDS)
        }
        result = service.settle_market(
            _MARKET_ID, list(_TEAM_IDS), _ADMIN_ID)
        mock_settle.assert_called_once_with(
            _MARKET_ID, list(_TEAM_IDS), _ADMIN_ID)
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        self.assertEqual(result["settled_by_uuid"], _ADMIN_UUID)
        self.assertEqual(result["settled_by_display_name"], "Admin")
        self.assertNotIn("settled_by", result)

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_correction_after_settle_is_allowed(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock,
            _mock_user: MagicMock) -> None:
        corrected = [12, 45, 101, 200, 201, 202, 203, 205]
        mock_fetch.return_value = _auto_result_document(
            settled_at=_SETTLED_AT)
        mock_settle.return_value = {
            "market_id": _MARKET_ID,
            "team_ids": corrected,
            "settled_by": _ADMIN_ID,
            "settled_at": _SETTLED_AT,
            "result_team_ids": corrected
        }
        result = service.settle_market(
            _MARKET_ID, corrected, _ADMIN_ID)
        mock_settle.assert_called_once_with(
            _MARKET_ID, corrected, _ADMIN_ID)
        self.assertEqual(result["team_ids"], corrected)

    @patch(f"{_REPO}.fetch_auto_result")
    def test_repository_not_found_is_mapped(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.side_effect = repo.TyperNotFoundError(
            "Long-term market not found")
        with self.assertRaises(service.TyperNotFoundError):
            service.get_auto_result(_MARKET_ID)

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.fetch_auto_result")
    def test_auto_result_exposes_settler_uuid_not_id(
            self,
            mock_fetch: MagicMock,
            mock_user: MagicMock) -> None:
        mock_fetch.return_value = _auto_result_document(
            settled_at=_SETTLED_AT, settled_by=_ADMIN_ID)
        document = service.get_auto_result(_MARKET_ID)
        self.assertEqual(document["settled_by_uuid"], _ADMIN_UUID)
        self.assertEqual(document["settled_by_display_name"], "Admin")
        self.assertNotIn("settled_by", document)
        mock_user.assert_called_once_with(_ADMIN_ID)

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.fetch_auto_result")
    def test_auto_result_keeps_approved_ids_beside_proposal(
            self,
            mock_fetch: MagicMock,
            _mock_user: MagicMock) -> None:
        approved = [12, 45, 101, 200, 201, 202, 203, 205]
        mock_fetch.return_value = _auto_result_document(
            settled_at=_SETTLED_AT,
            settled_by=_ADMIN_ID,
            result_team_ids=approved)
        document = service.get_auto_result(_MARKET_ID)
        self.assertEqual(document["result_team_ids"], approved)
        self.assertNotEqual(
            document["proposed_team_ids"], approved)


class TestLongTermDashboardMapping(unittest.TestCase):
    """Dashboard DTO adds points after settle and hides the owner user_id."""

    def test_unsettled_market_has_null_points(self) -> None:
        with patch(f"{_REPO}.fetch_long_term_dashboard") as mock_fetch:
            mock_fetch.return_value = {
                "season_id": _SEASON_ID,
                "markets": [
                    _dashboard_market_row(picked_team_ids=list(_TEAM_IDS))],
                "changes": []
            }
            document = service.get_dashboard(4, _SEASON_ID)
        market = document["markets"][0]
        self.assertIsNone(market["points"])
        self.assertEqual(market["changes"], [])
        self.assertEqual(
            market["market_kind"], service.MARKET_KIND_RANKED_TEAM_TABLE)
        self.assertEqual(
            market["scoring_kind"], service.SCORING_KIND_ZONE_AND_POSITION)
        self.assertEqual(market["top_zone_size"], _TOP_ZONE)
        self.assertEqual(market["bot_zone_size"], _BOT_ZONE)
        self.assertEqual(market["points_per_exact_position"], _POINTS_EXACT)
        self.assertNotIn("user_id", market)
        self.assertNotIn("settled_by", market)

    def test_settled_market_scores_zone_and_position(self) -> None:
        picks = _table_with_team_at(_PICK_FILLERS, _BARCELONA_ID, 6)
        results = _table_with_team_at(_RESULT_FILLERS, _BARCELONA_ID, 6)
        with patch(f"{_REPO}.fetch_long_term_dashboard") as mock_fetch:
            mock_fetch.return_value = {
                "season_id": _SEASON_ID,
                "markets": [_dashboard_market_row(
                    picked_team_ids=picks,
                    result_team_ids=results,
                    settled_at=_SETTLED_AT,
                    settled_by=_ADMIN_ID,
                    is_locked=True)],
                "changes": [{
                    "id": 1,
                    "market_id": _MARKET_ID,
                    "user_uuid": "u-1",
                    "display_name": "Alice",
                    "previous_team_ids": None,
                    "new_team_ids": picks,
                    "changed_at": _SETTLED_AT
                }]
            }
            document = service.get_dashboard(4, _SEASON_ID)
        market = document["markets"][0]
        self.assertEqual(market["points"], _POINTS_ZONE + _POINTS_EXACT)
        self.assertEqual(len(market["changes"]), 1)
        self.assertEqual(market["picked_team_ids"], picks)
        self.assertEqual(market["result_team_ids"], results)
        self.assertEqual(
            market["market_kind"], service.MARKET_KIND_RANKED_TEAM_TABLE)
        self.assertNotIn("settled_by", market)
        self.assertNotIn("settled_by_uuid", market)

    def test_save_picks_omits_user_id(self) -> None:
        with patch(f"{_REPO}.save_long_term_picks") as mock_save:
            mock_save.return_value = {
                "market_id": _MARKET_ID,
                "user_id": 4,
                "team_ids": list(_TEAM_IDS),
                "previous_team_ids": None,
                "audit_written": True
            }
            result = service.save_picks(4, _MARKET_ID, list(_TEAM_IDS))
        self.assertNotIn("user_id", result)
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        mock_save.assert_called_once_with(4, _MARKET_ID, list(_TEAM_IDS))


if __name__ == "__main__":
    unittest.main()
