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
        result_team_ids: list[int] | None = None,
        market_kind: str = service.MARKET_KIND_RANKED_TEAM_TABLE,
        scoring_kind: str = service.SCORING_KIND_ZONE_AND_POSITION,
        market_key: str = "league_phase_table"
        ) -> dict[str, object]:
    rows = standings if standings is not None else [
        _standing_row(team_id) for team_id in range(1, 37)]
    return {
        "market_id": _MARKET_ID,
        "league_id": repo.CHAMPIONS_LEAGUE_ID,
        "season_id": _SEASON_ID,
        "market_key": market_key,
        "selection_size": _TABLE_SIZE,
        "points_per_correct": 2.0,
        "points_per_exact_position": 2.0,
        "market_kind": market_kind,
        "scoring_kind": scoring_kind,
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
        picked_subject_text: str | None = None,
        result_subject_texts: list[str] | None = None,
        picked_is_text_correct: bool | None = None,
        result_is_text_correct: bool | None = None,
        settled_at: datetime | None = None,
        settled_by: int | None = None,
        is_locked: bool = False,
        market_key: str = "league_phase_table",
        title: str = "Tabela fazy ligowej",
        selection_size: int = _TABLE_SIZE,
        points_per_correct: float = _POINTS_ZONE,
        points_per_exact_position: float = _POINTS_EXACT,
        market_kind: str = service.MARKET_KIND_RANKED_TEAM_TABLE,
        scoring_kind: str = service.SCORING_KIND_ZONE_AND_POSITION,
        top_zone_size: int = _TOP_ZONE,
        bot_zone_size: int = _BOT_ZONE,
        candidates: list[dict[str, object]] | None = None
        ) -> dict[str, object]:
    return {
        "market_id": _MARKET_ID,
        "league_id": repo.CHAMPIONS_LEAGUE_ID,
        "season_id": _SEASON_ID,
        "market_key": market_key,
        "title": title,
        "description": None,
        "selection_size": selection_size,
        "points_per_correct": points_per_correct,
        "points_per_exact_position": points_per_exact_position,
        "market_kind": market_kind,
        "scoring_kind": scoring_kind,
        "top_zone_size": top_zone_size,
        "bot_zone_size": bot_zone_size,
        "settled_at": settled_at,
        "settled_by": settled_by,
        "deadline_at": _SETTLED_AT,
        "is_locked": is_locked,
        "candidates": [] if candidates is None else list(candidates),
        "picked_team_ids": (
            [] if picked_team_ids is None else list(picked_team_ids)),
        "result_team_ids": (
            [] if result_team_ids is None else list(result_team_ids)),
        "picked_subject_text": picked_subject_text,
        "result_subject_texts": (
            [] if result_subject_texts is None
            else list(result_subject_texts)),
        "picked_is_text_correct": picked_is_text_correct,
        "result_is_text_correct": result_is_text_correct
    }


def _incomplete_auto_result(
        market_kind: str = service.MARKET_KIND_RANKED_TEAM_TABLE,
        scoring_kind: str = service.SCORING_KIND_ZONE_AND_POSITION,
        market_key: str = "league_phase_table") -> dict[str, object]:
    return _auto_result_document(
        participant_count=36,
        min_matches=7,
        max_matches=8,
        settled_matches=140,
        market_kind=market_kind,
        scoring_kind=scoring_kind,
        market_key=market_key)


def _settled_stored(
        *,
        team_ids: list[int] | None = None,
        subject_texts: list[str] | None = None,
        is_text_correct: bool | None = None) -> dict[str, object]:
    ids = [] if team_ids is None else list(team_ids)
    return {
        "market_id": _MARKET_ID,
        "team_ids": ids,
        "subject_texts": (
            [] if subject_texts is None else list(subject_texts)),
        "is_text_correct": is_text_correct,
        "settled_by": _ADMIN_ID,
        "settled_at": _SETTLED_AT,
        "result_team_ids": ids
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
                "not_a_real_kind",
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


_POINTS_EXACT_SUBJECT = 2.0


def _score_exact(
        market_kind: str,
        *,
        pick_team_ids: list[int] | None = None,
        result_team_ids: list[int] | None = None,
        pick_subject_texts: list[str] | None = None,
        result_subject_texts: list[str] | None = None,
        pick_is_text_correct: bool | None = None,
        result_is_text_correct: bool | None = None,
        points_per_correct: float = _POINTS_EXACT_SUBJECT) -> float:
    return service.score_long_term(
        service.SCORING_KIND_EXACT_SUBJECT,
        [] if pick_team_ids is None else pick_team_ids,
        [] if result_team_ids is None else result_team_ids,
        points_per_correct,
        0.0,
        -1,
        -1,
        market_kind=market_kind,
        pick_subject_texts=pick_subject_texts,
        result_subject_texts=result_subject_texts,
        pick_is_text_correct=pick_is_text_correct,
        result_is_text_correct=result_is_text_correct)


class TestNormalizeSubjectText(unittest.TestCase):
    """Trim, collapse spaces and Unicode casefold; no transliteration."""

    def test_uses_repository_normalize(self) -> None:
        self.assertIs(
            service.normalize_subject_text, repo.normalize_subject_text)

    def test_trim_and_collapse_whitespace(self) -> None:
        self.assertEqual(
            service.normalize_subject_text("  Robert   Lewandowski "),
            "robert lewandowski")

    def test_empty_after_whitespace_is_empty(self) -> None:
        self.assertEqual(service.normalize_subject_text("   "), "")

    def test_does_not_strip_diacritics(self) -> None:
        self.assertEqual(
            service.normalize_subject_text("Håland"),
            "håland")
        self.assertNotEqual(
            service.normalize_subject_text("Håland"),
            service.normalize_subject_text("Haaland"))


class TestScoreExactSubject(unittest.TestCase):
    """Set intersection times points_per_correct; one pick, result may tie."""

    def test_text_hit_is_two(self) -> None:
        self.assertEqual(
            service.score_exact_subject(
                ["robert lewandowski"],
                ["robert lewandowski"],
                _POINTS_EXACT_SUBJECT),
            _POINTS_EXACT_SUBJECT)

    def test_text_miss_is_zero(self) -> None:
        self.assertEqual(
            service.score_exact_subject(
                ["erling haaland"],
                ["robert lewandowski"],
                _POINTS_EXACT_SUBJECT),
            0.0)

    def test_text_tie_hits_when_pick_in_result_set(self) -> None:
        self.assertEqual(
            service.score_exact_subject(
                ["robert lewandowski"],
                ["erling haaland", "robert lewandowski"],
                _POINTS_EXACT_SUBJECT),
            _POINTS_EXACT_SUBJECT)

    def test_team_tie_hits_when_pick_in_result_set(self) -> None:
        self.assertEqual(
            service.score_exact_subject(
                [12],
                [12, 45],
                _POINTS_EXACT_SUBJECT),
            _POINTS_EXACT_SUBJECT)

    def test_yes_misses_no(self) -> None:
        self.assertEqual(
            service.score_exact_subject(
                [True],
                [False],
                _POINTS_EXACT_SUBJECT),
            0.0)

    def test_normalized_full_name_hits(self) -> None:
        pick = service.normalize_subject_text("  Robert   Lewandowski ")
        result = service.normalize_subject_text("robert lewandowski")
        self.assertEqual(
            service.score_exact_subject(
                [pick], [result], _POINTS_EXACT_SUBJECT),
            _POINTS_EXACT_SUBJECT)

    def test_last_name_only_misses_full_name(self) -> None:
        pick = service.normalize_subject_text("Lewandowski")
        result = service.normalize_subject_text("Robert Lewandowski")
        self.assertEqual(
            service.score_exact_subject(
                [pick], [result], _POINTS_EXACT_SUBJECT),
            0.0)

    def test_dispatch_free_text_hit(self) -> None:
        self.assertEqual(
            _score_exact(
                service.MARKET_KIND_FREE_TEXT,
                pick_subject_texts=["robert lewandowski"],
                result_subject_texts=["robert lewandowski"]),
            _POINTS_EXACT_SUBJECT)

    def test_dispatch_single_team_tie(self) -> None:
        self.assertEqual(
            _score_exact(
                service.MARKET_KIND_SINGLE_TEAM,
                pick_team_ids=[12],
                result_team_ids=[12, 45]),
            _POINTS_EXACT_SUBJECT)

    def test_dispatch_yes_no_miss(self) -> None:
        self.assertEqual(
            _score_exact(
                service.MARKET_KIND_YES_NO,
                pick_is_text_correct=True,
                result_is_text_correct=False),
            0.0)

    def test_dispatch_yes_no_hit(self) -> None:
        self.assertEqual(
            _score_exact(
                service.MARKET_KIND_YES_NO,
                pick_is_text_correct=False,
                result_is_text_correct=False),
            _POINTS_EXACT_SUBJECT)

    def test_unknown_market_kind_is_zero(self) -> None:
        self.assertEqual(
            _score_exact(
                "not_a_real_kind",
                pick_subject_texts=["robert lewandowski"],
                result_subject_texts=["robert lewandowski"]),
            0.0)


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

    @patch(f"{_REPO}.fetch_auto_result")
    def test_non_table_has_empty_proposed_even_when_complete(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = _auto_result_document(
            market_kind=service.MARKET_KIND_FREE_TEXT,
            scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
            market_key="top_scorer")
        document = service.get_auto_result(_MARKET_ID)
        self.assertTrue(document["is_complete"])
        self.assertEqual(document["proposed_team_ids"], [])
        self.assertEqual(document["proposed_top_team_ids"], [])
        self.assertEqual(document["proposed_bot_team_ids"], [])
        self.assertEqual(document["proposed_teams"], [])
        self.assertEqual(len(document["standings"]), 36)


class TestSettleMarket(unittest.TestCase):
    """Ranked settle needs a complete phase; exact_subject does not."""

    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_does_not_write(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_fetch.return_value = _incomplete_auto_result()
        with self.assertRaises(service.TyperConflictError):
            service.settle_market(_MARKET_ID, list(_TEAM_IDS), _ADMIN_ID)
        mock_settle.assert_not_called()

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_allows_free_text_settle(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock,
            _mock_user: MagicMock) -> None:
        mock_fetch.return_value = _incomplete_auto_result(
            market_kind=service.MARKET_KIND_FREE_TEXT,
            scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
            market_key="top_scorer")
        texts = ["Robert Lewandowski"]
        mock_settle.return_value = _settled_stored(subject_texts=texts)
        result = service.settle_market(
            _MARKET_ID,
            subject_texts=texts,
            admin_id=_ADMIN_ID)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=None,
            admin_id=_ADMIN_ID,
            subject_texts=texts,
            is_text_correct=None)
        self.assertEqual(result["subject_texts"], texts)
        self.assertEqual(result["team_ids"], [])

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_allows_yes_no_settle(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock,
            _mock_user: MagicMock) -> None:
        mock_fetch.return_value = _incomplete_auto_result(
            market_kind=service.MARKET_KIND_YES_NO,
            scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
            market_key="any_team_win_all")
        mock_settle.return_value = _settled_stored(is_text_correct=True)
        result = service.settle_market(
            _MARKET_ID,
            is_text_correct=True,
            admin_id=_ADMIN_ID)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=None,
            admin_id=_ADMIN_ID,
            subject_texts=None,
            is_text_correct=True)
        self.assertTrue(result["is_text_correct"])

    @patch(f"{_FETCH_USER}", return_value=_ADMIN_USER)
    @patch(f"{_REPO}.settle_market")
    @patch(f"{_REPO}.fetch_auto_result")
    def test_incomplete_phase_allows_single_team_settle(
            self,
            mock_fetch: MagicMock,
            mock_settle: MagicMock,
            _mock_user: MagicMock) -> None:
        mock_fetch.return_value = _incomplete_auto_result(
            market_kind=service.MARKET_KIND_SINGLE_TEAM,
            scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
            market_key="most_goals_scored")
        mock_settle.return_value = _settled_stored(team_ids=[12, 45])
        result = service.settle_market(
            _MARKET_ID,
            team_ids=[12, 45],
            admin_id=_ADMIN_ID)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=[12, 45],
            admin_id=_ADMIN_ID,
            subject_texts=None,
            is_text_correct=None)
        self.assertEqual(result["team_ids"], [12, 45])

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
            _MARKET_ID,
            team_ids=list(_TEAM_IDS),
            admin_id=_ADMIN_ID,
            subject_texts=None,
            is_text_correct=None)
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        self.assertEqual(result["settled_by_uuid"], _ADMIN_UUID)
        self.assertEqual(result["settled_by_display_name"], "Admin")
        self.assertNotIn("settled_by", result)
        self.assertEqual(result["subject_texts"], [])
        self.assertIsNone(result["is_text_correct"])

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
            _MARKET_ID,
            team_ids=corrected,
            admin_id=_ADMIN_ID,
            subject_texts=None,
            is_text_correct=None)
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
        self.assertIsNone(market["picked_subject_text"])
        self.assertEqual(market["result_subject_texts"], [])
        self.assertIsNone(market["picked_is_text_correct"])
        self.assertIsNone(market["result_is_text_correct"])

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
        self.assertIsNone(market["picked_subject_text"])

    def test_settled_free_text_scores_normalized_hit(self) -> None:
        with patch(f"{_REPO}.fetch_long_term_dashboard") as mock_fetch:
            mock_fetch.return_value = {
                "season_id": _SEASON_ID,
                "markets": [_dashboard_market_row(
                    market_key="top_scorer",
                    title="Najlepszy strzelec",
                    selection_size=1,
                    points_per_correct=_POINTS_EXACT_SUBJECT,
                    points_per_exact_position=0.0,
                    market_kind=service.MARKET_KIND_FREE_TEXT,
                    scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
                    top_zone_size=-1,
                    bot_zone_size=-1,
                    picked_subject_text="  Robert   Lewandowski ",
                    result_subject_texts=["robert lewandowski"],
                    settled_at=_SETTLED_AT,
                    is_locked=True)],
                "changes": []
            }
            document = service.get_dashboard(4, _SEASON_ID)
        market = document["markets"][0]
        self.assertEqual(market["points"], _POINTS_EXACT_SUBJECT)
        self.assertEqual(
            market["picked_subject_text"], "  Robert   Lewandowski ")
        self.assertEqual(
            market["result_subject_texts"], ["robert lewandowski"])
        self.assertEqual(market["picked_team_ids"], [])
        self.assertEqual(market["result_team_ids"], [])

    def test_settled_yes_no_scores_hit(self) -> None:
        with patch(f"{_REPO}.fetch_long_term_dashboard") as mock_fetch:
            mock_fetch.return_value = {
                "season_id": _SEASON_ID,
                "markets": [_dashboard_market_row(
                    market_key="any_team_win_all",
                    title="Czy jakakolwiek drużyna wygra wszystkie mecze?",
                    selection_size=1,
                    points_per_correct=_POINTS_EXACT_SUBJECT,
                    points_per_exact_position=0.0,
                    market_kind=service.MARKET_KIND_YES_NO,
                    scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
                    top_zone_size=-1,
                    bot_zone_size=-1,
                    picked_is_text_correct=False,
                    result_is_text_correct=False,
                    settled_at=_SETTLED_AT,
                    is_locked=True)],
                "changes": []
            }
            document = service.get_dashboard(4, _SEASON_ID)
        market = document["markets"][0]
        self.assertEqual(market["points"], _POINTS_EXACT_SUBJECT)
        self.assertFalse(market["picked_is_text_correct"])
        self.assertFalse(market["result_is_text_correct"])
        self.assertIsNone(market["picked_subject_text"])

    def test_settled_single_team_tie_scores_hit(self) -> None:
        with patch(f"{_REPO}.fetch_long_term_dashboard") as mock_fetch:
            mock_fetch.return_value = {
                "season_id": _SEASON_ID,
                "markets": [_dashboard_market_row(
                    market_key="most_goals_scored",
                    title="Która drużyna strzeli najwięcej bramek",
                    selection_size=1,
                    points_per_correct=_POINTS_EXACT_SUBJECT,
                    points_per_exact_position=0.0,
                    market_kind=service.MARKET_KIND_SINGLE_TEAM,
                    scoring_kind=service.SCORING_KIND_EXACT_SUBJECT,
                    top_zone_size=-1,
                    bot_zone_size=-1,
                    picked_team_ids=[12],
                    result_team_ids=[12, 45],
                    settled_at=_SETTLED_AT,
                    is_locked=True,
                    candidates=[{
                        "team_id": 12,
                        "team_name": "Team 12",
                        "team_shortcut": "T12"
                    }])],
                "changes": []
            }
            document = service.get_dashboard(4, _SEASON_ID)
        market = document["markets"][0]
        self.assertEqual(market["points"], _POINTS_EXACT_SUBJECT)
        self.assertEqual(market["picked_team_ids"], [12])
        self.assertEqual(market["result_team_ids"], [12, 45])
        self.assertIsNone(market["picked_subject_text"])
        self.assertEqual(len(market["candidates"]), 1)

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
        self.assertEqual(result["subject_texts"], [])
        self.assertIsNone(result["is_text_correct"])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=list(_TEAM_IDS),
            subject_texts=None,
            is_text_correct=None)

    def test_save_picks_forwards_subject_texts(self) -> None:
        with patch(f"{_REPO}.save_long_term_picks") as mock_save:
            mock_save.return_value = {
                "market_id": _MARKET_ID,
                "user_id": 4,
                "team_ids": [],
                "previous_team_ids": None,
                "subject_texts": ["Robert Lewandowski"],
                "previous_subject_text": None,
                "is_text_correct": None,
                "previous_is_text_correct": None,
                "audit_written": True
            }
            result = service.save_picks(
                4,
                _MARKET_ID,
                subject_texts=["Robert Lewandowski"])
        self.assertNotIn("user_id", result)
        self.assertEqual(result["subject_texts"], ["Robert Lewandowski"])
        self.assertEqual(result["team_ids"], [])
        self.assertTrue(result["audit_written"])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=None,
            subject_texts=["Robert Lewandowski"],
            is_text_correct=None)

    def test_save_picks_forwards_is_text_correct(self) -> None:
        with patch(f"{_REPO}.save_long_term_picks") as mock_save:
            mock_save.return_value = {
                "market_id": _MARKET_ID,
                "user_id": 4,
                "team_ids": [],
                "previous_team_ids": None,
                "subject_texts": [],
                "previous_subject_text": None,
                "is_text_correct": True,
                "previous_is_text_correct": None,
                "audit_written": True
            }
            result = service.save_picks(
                4, _MARKET_ID, is_text_correct=True)
        self.assertTrue(result["is_text_correct"])
        self.assertIsNone(result["previous_is_text_correct"])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=None,
            subject_texts=None,
            is_text_correct=True)


if __name__ == "__main__":
    unittest.main()
