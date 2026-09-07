"""API tests for Typer long-term market endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("OPENAPI_ENABLED", "false")

from api.schemas.champions_league_typer_long_term import (
    LongTermAutoResultResponse,
    LongTermMarketCard,
    LongTermPicksRequest,
    SaveLongTermPicksResponse,
    SettleLongTermResponse)
from backend.config import get_settings
from backend.services import auth_service
from backend.services.champions_league_typer_long_term_service import (
    TyperConflictError,
    TyperNotFoundError,
    TyperValidationError)

get_settings.cache_clear()

from api.main import create_app

_SERVICE = "api.routers.champions_league_typer_long_term.long_term_service"
_FETCH_UUID = (
    "backend.services.auth_service.user_repository.fetch_user_by_uuid")
_DEADLINE = datetime(2026, 9, 16, 21, 0)
_CHANGED_AT = datetime(2026, 8, 20, 12, 0)
_SETTLED_AT = datetime(2026, 12, 1, 23, 0)
_MARKET_ID = 20
_TABLE_SIZE = 36
_TOP_ZONE = 8
_BOT_ZONE = 8
_EIGHT_IDS = [12, 45, 101, 200, 201, 202, 203, 204]
_TABLE_IDS = list(range(1, _TABLE_SIZE + 1))
_TABLE_PERMUTATION = [3, 1, 2, *range(4, _TABLE_SIZE + 1)]
_TEAM_IDS = _EIGHT_IDS

_TEST_USER = {
    "id": 4,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice",
    "password_hash": auth_service.hash_password("secret123"),
    "display_name": "Alice",
    "is_active": 1,
    "is_admin": 0,
    "first_login": 0,
    "created_at": None,
    "updated_at": None
}
_ADMIN_USER = {
    **_TEST_USER,
    "id": 7,
    "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "username": "admin",
    "is_admin": 1
}


def _candidate(team_id: int) -> dict[str, object]:
    return {
        "team_id": team_id,
        "team_name": f"Team {team_id}",
        "team_shortcut": f"T{team_id}"
    }


def _change_row() -> dict[str, object]:
    return {
        "id": 9,
        "market_id": _MARKET_ID,
        "user_uuid": _TEST_USER["uuid"],
        "display_name": "Alice",
        "previous_team_ids": None,
        "new_team_ids": list(_TABLE_PERMUTATION),
        "previous_subject_text": None,
        "new_subject_text": None,
        "previous_is_text_correct": None,
        "new_is_text_correct": None,
        "changed_at": _CHANGED_AT
    }


def _saved_picks(
        *,
        team_ids: list[int] | None = None,
        subject_texts: list[str] | None = None,
        is_text_correct: bool | None = None,
        previous_team_ids: list[int] | None = None,
        previous_subject_text: str | None = None,
        previous_is_text_correct: bool | None = None,
        audit_written: bool = True) -> dict[str, object]:
    return {
        "market_id": _MARKET_ID,
        "team_ids": [] if team_ids is None else list(team_ids),
        "previous_team_ids": previous_team_ids,
        "subject_texts": (
            [] if subject_texts is None else list(subject_texts)),
        "previous_subject_text": previous_subject_text,
        "is_text_correct": is_text_correct,
        "previous_is_text_correct": previous_is_text_correct,
        "audit_written": audit_written
    }


def _settled_payload(
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
        "settled_by_uuid": _ADMIN_USER["uuid"],
        "settled_by_display_name": "Alice",
        "settled_at": _SETTLED_AT,
        "result_team_ids": ids
    }


def _dashboard_payload() -> dict[str, object]:
    return {
        "season_id": 13,
        "markets": [{
            "market_id": _MARKET_ID,
            "league_id": 42,
            "season_id": 13,
            "market_key": "league_phase_table",
            "title": "Tabela fazy ligowej",
            "description": "Z 36 drużyn wybierz te, które zajmą miejsca 1–8 oraz 29–36 w fazie ligowej",
            "selection_size": _TABLE_SIZE,
            "points_per_correct": 2.0,
            "points_per_exact_position": 2.0,
            "market_kind": "ranked_team_table",
            "scoring_kind": "zone_and_position",
            "top_zone_size": _TOP_ZONE,
            "bot_zone_size": _BOT_ZONE,
            "settled_at": None,
            "deadline_at": _DEADLINE,
            "is_locked": False,
            "candidates": [
                _candidate(team_id) for team_id in _TABLE_IDS],
            "picked_team_ids": list(_TABLE_PERMUTATION),
            "result_team_ids": [],
            "picked_subject_text": None,
            "result_subject_texts": [],
            "picked_is_text_correct": None,
            "result_is_text_correct": None,
            "points": None,
            "changes": [_change_row()]
        }]
    }


def _free_text_dashboard_payload() -> dict[str, object]:
    return {
        "season_id": 13,
        "markets": [{
            "market_id": _MARKET_ID,
            "league_id": 42,
            "season_id": 13,
            "market_key": "top_scorer",
            "title": "Najlepszy strzelec",
            "description": None,
            "selection_size": 1,
            "points_per_correct": 2.0,
            "points_per_exact_position": 0.0,
            "market_kind": "free_text",
            "scoring_kind": "exact_subject",
            "top_zone_size": -1,
            "bot_zone_size": -1,
            "settled_at": None,
            "deadline_at": _DEADLINE,
            "is_locked": False,
            "candidates": [],
            "picked_team_ids": [],
            "result_team_ids": [],
            "picked_subject_text": "  Robert   Lewandowski ",
            "result_subject_texts": ["Robert Lewandowski"],
            "picked_is_text_correct": None,
            "result_is_text_correct": None,
            "points": 2.0,
            "changes": []
        }]
    }


def _standing(team_id: int) -> dict[str, object]:
    return {
        **_candidate(team_id),
        "played": 8,
        "points": 12,
        "goal_difference": team_id,
        "goals_for": team_id * 2
    }


def _auto_result_payload(
        *,
        complete: bool = True,
        result_team_ids: list[int] | None = None
        ) -> dict[str, object]:
    proposed = [_standing(team_id) for team_id in _TABLE_IDS]
    proposed_ids = list(_TABLE_IDS) if complete else []
    return {
        "market_id": _MARKET_ID,
        "league_id": 42,
        "season_id": 13,
        "market_key": "league_phase_table",
        "selection_size": _TABLE_SIZE,
        "points_per_correct": 2.0,
        "points_per_exact_position": 2.0,
        "top_zone_size": _TOP_ZONE,
        "bot_zone_size": _BOT_ZONE,
        "settled_at": None,
        "settled_by_uuid": None,
        "settled_by_display_name": None,
        "is_complete": complete,
        "is_proposal": True,
        "participant_count": 36 if complete else 35,
        "settled_match_count": 144 if complete else 140,
        "min_matches_per_team": 8 if complete else 7,
        "max_matches_per_team": 8,
        "required_participant_count": 36,
        "required_matches_per_team": 8,
        "required_settled_match_count": 144,
        "proposed_team_ids": proposed_ids,
        "proposed_top_team_ids": proposed_ids[:_TOP_ZONE],
        "proposed_bot_team_ids": (
            proposed_ids[-_BOT_ZONE:] if complete else []),
        "proposed_teams": proposed if complete else [],
        "result_team_ids": (
            [] if result_team_ids is None else list(result_team_ids)),
        "standings": proposed
    }


class LongTermRouterTestCase(unittest.TestCase):
    """Authenticated TestClient shared by participant and admin cases."""

    user: dict[str, object] = _TEST_USER

    def setUp(self) -> None:
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["OPENAPI_ENABLED"] = "false"
        get_settings.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ["OPENAPI_ENABLED"] = "false"
        get_settings.cache_clear()

    def _auth_headers(self) -> dict[str, str]:
        token, _ = auth_service.create_access_token(str(self.user["uuid"]))
        return {"Authorization": f"Bearer {token}"}


class TestLongTermParticipantRouter(LongTermRouterTestCase):
    """HTTP contract for participant dashboard, picks and own audit."""

    def test_participant_endpoints_require_token(self) -> None:
        cases = [
            ("GET", "/typer-lm/long-term", None),
            (
                "PUT",
                f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
                {"team_ids": list(_TEAM_IDS)}),
            (
                "GET",
                f"/typer-lm/long-term/markets/{_MARKET_ID}/history",
                None)]
        for method, path, body in cases:
            with self.subTest(method=method, path=path):
                kwargs = {"json": body} if body is not None else {}
                response = self.client.request(method, path, **kwargs)
                self.assertEqual(response.status_code, 401)

    @patch(
        f"{_SERVICE}.get_dashboard",
        return_value=_dashboard_payload())
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_dashboard_returns_private_contract(
            self,
            _mock_fetch: MagicMock,
            mock_dashboard: MagicMock) -> None:
        response = self.client.get(
            "/typer-lm/long-term?season_id=13",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        market = payload["markets"][0]
        self.assertEqual(payload["season_id"], 13)
        self.assertEqual(market["market_key"], "league_phase_table")
        self.assertEqual(market["market_kind"], "ranked_team_table")
        self.assertEqual(market["scoring_kind"], "zone_and_position")
        self.assertEqual(market["top_zone_size"], _TOP_ZONE)
        self.assertEqual(market["bot_zone_size"], _BOT_ZONE)
        self.assertEqual(market["points_per_exact_position"], 2.0)
        self.assertEqual(market["picked_team_ids"], list(_TABLE_PERMUTATION))
        self.assertNotEqual(
            market["picked_team_ids"], sorted(market["picked_team_ids"]))
        self.assertIsNone(market["picked_subject_text"])
        self.assertEqual(market["result_subject_texts"], [])
        self.assertIsNone(market["picked_is_text_correct"])
        self.assertIsNone(market["result_is_text_correct"])
        self.assertIsNone(market["points"])
        self.assertNotIn("user_id", market)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("settled_by", market)
        self.assertNotIn("player_ids", market)
        mock_dashboard.assert_called_once_with(4, 13)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_picks_returns_saved_set(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        ordered = list(_TABLE_PERMUTATION)
        mock_save.return_value = _saved_picks(team_ids=ordered)
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": ordered},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team_ids"], ordered)
        self.assertNotEqual(payload["team_ids"], sorted(ordered))
        self.assertEqual(payload["subject_texts"], [])
        self.assertIsNone(payload["is_text_correct"])
        self.assertIsNone(payload["previous_subject_text"])
        self.assertTrue(payload["audit_written"])
        self.assertNotIn("user_id", payload)
        self.assertNotIn("player_ids", payload)
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=ordered,
            subject_texts=None,
            is_text_correct=None)

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_duplicate_team_ids_return_422(
            self, _mock_fetch: MagicMock) -> None:
        duplicated = list(_TEAM_IDS)
        duplicated[1] = duplicated[0]
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": duplicated},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_non_positive_team_ids_return_422(
            self, _mock_fetch: MagicMock) -> None:
        invalid = [0, *list(_TEAM_IDS[1:])]
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": invalid},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_wrong_selection_size_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperValidationError(
            "Long-term pick set must contain exactly 36 teams")
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": list(_EIGHT_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=list(_EIGHT_IDS),
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_deadline_conflict_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperConflictError(
            "Picks cannot be saved after kickoff")
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": list(_TEAM_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_unknown_market_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperNotFoundError(
            "Long-term market not found")
        response = self.client.put(
            "/typer-lm/long-term/markets/999/picks",
            json={"team_ids": list(_TEAM_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)

    @patch(
        f"{_SERVICE}.get_own_history",
        return_value=[_change_row()])
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_own_history_contract(
            self,
            _mock_fetch: MagicMock,
            mock_history: MagicMock) -> None:
        response = self.client.get(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/history",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()[0]["new_team_ids"], list(_TABLE_PERMUTATION))
        self.assertIsNone(response.json()[0]["previous_subject_text"])
        self.assertIsNone(response.json()[0]["new_subject_text"])
        self.assertIsNone(response.json()[0]["previous_is_text_correct"])
        self.assertIsNone(response.json()[0]["new_is_text_correct"])
        mock_history.assert_called_once_with(4, _MARKET_ID)

    @patch(f"{_SERVICE}.get_own_history")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_own_history_serializes_text_audit(
            self,
            _mock_fetch: MagicMock,
            mock_history: MagicMock) -> None:
        mock_history.return_value = [{
            "id": 11,
            "market_id": _MARKET_ID,
            "user_uuid": _TEST_USER["uuid"],
            "display_name": "Alice",
            "previous_team_ids": None,
            "new_team_ids": [],
            "previous_subject_text": "Robert Lewandowski",
            "new_subject_text": "Kylian Mbappe",
            "previous_is_text_correct": None,
            "new_is_text_correct": None,
            "changed_at": _CHANGED_AT
        }]
        response = self.client.get(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/history",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        row = response.json()[0]
        self.assertEqual(row["previous_subject_text"], "Robert Lewandowski")
        self.assertEqual(row["new_subject_text"], "Kylian Mbappe")
        self.assertEqual(row["new_team_ids"], [])
        self.assertIsNone(row["previous_is_text_correct"])

    @patch(f"{_SERVICE}.get_own_history")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_own_history_unknown_market_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_history: MagicMock) -> None:
        mock_history.side_effect = TyperNotFoundError(
            "Long-term market not found")
        response = self.client.get(
            "/typer-lm/long-term/markets/999/history",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_subject_texts_forwards_free_text_branch(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        texts = ["Robert Lewandowski"]
        mock_save.return_value = _saved_picks(subject_texts=texts)
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"subject_texts": texts},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["subject_texts"], texts)
        self.assertEqual(payload["team_ids"], [])
        self.assertIsNone(payload["is_text_correct"])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=None,
            subject_texts=texts,
            is_text_correct=None)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_is_text_correct_forwards_yes_no_branch(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.return_value = _saved_picks(is_text_correct=True)
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"is_text_correct": True},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["is_text_correct"])
        self.assertEqual(payload["subject_texts"], [])
        self.assertEqual(payload["team_ids"], [])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=None,
            subject_texts=None,
            is_text_correct=True)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_single_team_forwards_one_id(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.return_value = _saved_picks(team_ids=[12])
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": [12]},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["team_ids"], [12])
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=[12],
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_wrong_kind_payload_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperValidationError(
            "Subject text is not valid for this market kind")
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"subject_texts": ["x"]},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Subject text is not valid for this market kind")
        mock_save.assert_called_once_with(
            4,
            _MARKET_ID,
            team_ids=None,
            subject_texts=["x"],
            is_text_correct=None)

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_blank_subject_texts_return_422_before_service(
            self, _mock_fetch: MagicMock) -> None:
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"subject_texts": ["   "]},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], list)

    @patch(
        f"{_SERVICE}.get_dashboard",
        return_value=_free_text_dashboard_payload())
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_dashboard_serializes_free_text_card(
            self,
            _mock_fetch: MagicMock,
            _mock_dashboard: MagicMock) -> None:
        response = self.client.get(
            "/typer-lm/long-term",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        market = response.json()["markets"][0]
        self.assertEqual(market["market_kind"], "free_text")
        self.assertEqual(
            market["picked_subject_text"], "  Robert   Lewandowski ")
        self.assertEqual(
            market["result_subject_texts"], ["Robert Lewandowski"])
        self.assertEqual(market["candidates"], [])
        self.assertEqual(market["picked_team_ids"], [])


class TestLongTermSchemaContract(unittest.TestCase):
    """HTTP schema treats table order as significant and has no player_ids."""

    def test_team_ids_field_does_not_ignore_order(self) -> None:
        field = LongTermPicksRequest.model_fields["team_ids"]
        description = field.description or ""
        self.assertNotEqual(description, "")
        self.assertNotIn("order is ignored", description.lower())
        self.assertIn("table order", description.lower())

    def test_ranked_table_schemas_have_no_player_ids(self) -> None:
        models = (
            LongTermMarketCard,
            LongTermAutoResultResponse,
            LongTermPicksRequest,
            SaveLongTermPicksResponse,
            SettleLongTermResponse)
        for model in models:
            with self.subTest(model=model.__name__):
                self.assertNotIn("player_ids", model.model_fields)
                self.assertNotIn("player_id", model.model_fields)

    def test_ranked_table_request_omits_text_branches(self) -> None:
        body = LongTermPicksRequest(team_ids=list(_TABLE_PERMUTATION))
        self.assertEqual(body.team_ids, list(_TABLE_PERMUTATION))
        self.assertIsNone(body.subject_texts)
        self.assertIsNone(body.is_text_correct)

    def test_schema_does_not_require_xor(self) -> None:
        body = LongTermPicksRequest(
            team_ids=[12],
            subject_texts=["Lewandowski"],
            is_text_correct=True)
        self.assertEqual(body.team_ids, [12])
        self.assertEqual(body.subject_texts, ["Lewandowski"])
        self.assertTrue(body.is_text_correct)

    def test_subject_texts_are_stripped_without_sorting(self) -> None:
        body = LongTermPicksRequest(
            subject_texts=["  Mbappe ", "  Lewandowski "])
        self.assertEqual(body.subject_texts, ["Mbappe", "Lewandowski"])

    def test_blank_subject_texts_are_rejected_by_schema(self) -> None:
        with self.assertRaises(ValidationError):
            LongTermPicksRequest(subject_texts=["   "])


class TestLongTermAdminRouter(LongTermRouterTestCase):
    """Admin mutations and foreign audit require is_admin."""

    user = _ADMIN_USER

    def test_admin_endpoints_require_token(self) -> None:
        cases = [
            (
                "GET",
                f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/auto-result",
                None),
            (
                "POST",
                f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
                {"team_ids": list(_TEAM_IDS)}),
            (
                "GET",
                "/typer-lm/long-term/admin/prediction-history?user_uuid=u-1",
                None)]
        for method, path, body in cases:
            with self.subTest(method=method, path=path):
                kwargs = {"json": body} if body is not None else {}
                response = self.client.request(method, path, **kwargs)
                self.assertEqual(response.status_code, 401)

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_regular_user_cannot_use_admin_endpoints(
            self, _mock_fetch: MagicMock) -> None:
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        headers = {"Authorization": f"Bearer {token}"}
        auto_result = self.client.get(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/auto-result",
            headers=headers)
        self.assertEqual(auto_result.status_code, 403)
        settle = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": list(_TEAM_IDS)},
            headers=headers)
        self.assertEqual(settle.status_code, 403)
        history = self.client.get(
            "/typer-lm/long-term/admin/prediction-history",
            params={"user_uuid": _TEST_USER["uuid"]},
            headers=headers)
        self.assertEqual(history.status_code, 403)

    @patch(
        f"{_SERVICE}.get_auto_result",
        return_value=_auto_result_payload())
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_auto_result_returns_proposal(
            self,
            _mock_fetch: MagicMock,
            mock_auto: MagicMock) -> None:
        response = self.client.get(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/auto-result",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["is_complete"])
        self.assertTrue(payload["is_proposal"])
        self.assertEqual(len(payload["proposed_team_ids"]), _TABLE_SIZE)
        self.assertEqual(payload["proposed_team_ids"], list(_TABLE_IDS))
        self.assertEqual(
            payload["proposed_top_team_ids"], list(_TABLE_IDS[:_TOP_ZONE]))
        self.assertEqual(
            payload["proposed_bot_team_ids"], list(_TABLE_IDS[-_BOT_ZONE:]))
        self.assertEqual(payload["top_zone_size"], _TOP_ZONE)
        self.assertEqual(payload["bot_zone_size"], _BOT_ZONE)
        self.assertEqual(payload["points_per_exact_position"], 2.0)
        self.assertEqual(payload["result_team_ids"], [])
        self.assertIsNone(payload["settled_by_uuid"])
        self.assertNotIn("settled_by", payload)
        self.assertNotIn("player_ids", payload)
        mock_auto.assert_called_once_with(_MARKET_ID)

    @patch(
        f"{_SERVICE}.get_auto_result",
        return_value=_auto_result_payload(complete=False))
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_incomplete_auto_result_has_empty_proposal(
            self,
            _mock_fetch: MagicMock,
            mock_auto: MagicMock) -> None:
        response = self.client.get(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/auto-result",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_complete"])
        self.assertEqual(payload["proposed_team_ids"], [])
        self.assertEqual(payload["proposed_top_team_ids"], [])
        self.assertEqual(payload["proposed_bot_team_ids"], [])
        self.assertEqual(payload["proposed_teams"], [])
        self.assertEqual(payload["result_team_ids"], [])

    @patch(
        f"{_SERVICE}.get_auto_result",
        return_value=_auto_result_payload(
            result_team_ids=list(_TABLE_PERMUTATION)))
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_auto_result_includes_approved_set_for_correction(
            self,
            _mock_fetch: MagicMock,
            _mock_auto: MagicMock) -> None:
        response = self.client.get(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/auto-result",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["proposed_team_ids"], list(_TABLE_IDS))
        self.assertEqual(
            payload["result_team_ids"], list(_TABLE_PERMUTATION))
        self.assertNotEqual(
            payload["proposed_team_ids"], payload["result_team_ids"])

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_incomplete_phase_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_settle.side_effect = TyperConflictError(
            "League phase is not complete")
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": list(_TABLE_PERMUTATION)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=list(_TABLE_PERMUTATION),
            admin_id=7,
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_admin_correction_returns_settled_set(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        corrected = list(_TABLE_PERMUTATION)
        mock_settle.return_value = _settled_payload(team_ids=corrected)
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": corrected},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team_ids"], corrected)
        self.assertNotEqual(payload["team_ids"], sorted(corrected))
        self.assertEqual(payload["result_team_ids"], corrected)
        self.assertEqual(payload["subject_texts"], [])
        self.assertIsNone(payload["is_text_correct"])
        self.assertEqual(payload["settled_by_uuid"], _ADMIN_USER["uuid"])
        self.assertNotIn("settled_by", payload)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=corrected,
            admin_id=7,
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_unknown_market_settle_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_settle.side_effect = TyperNotFoundError(
            "Long-term market not found")
        response = self.client.post(
            "/typer-lm/long-term/admin/markets/999/settle",
            json={"team_ids": list(_TEAM_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_settle_subject_texts_forwards_free_text_branch(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        texts = ["Robert Lewandowski", "Kylian Mbappe"]
        mock_settle.return_value = _settled_payload(subject_texts=texts)
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"subject_texts": texts},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["subject_texts"], texts)
        self.assertEqual(payload["team_ids"], [])
        self.assertIsNone(payload["is_text_correct"])
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=None,
            admin_id=7,
            subject_texts=texts,
            is_text_correct=None)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_settle_is_text_correct_forwards_yes_no_branch(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_settle.return_value = _settled_payload(is_text_correct=False)
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"is_text_correct": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_text_correct"])
        self.assertEqual(payload["subject_texts"], [])
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=None,
            admin_id=7,
            subject_texts=None,
            is_text_correct=False)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_settle_single_team_forwards_ids(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_settle.return_value = _settled_payload(team_ids=[12, 45])
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": [12, 45]},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["team_ids"], [12, 45])
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=[12, 45],
            admin_id=7,
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_settle_wrong_kind_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_settle.side_effect = TyperValidationError(
            "Team ids are not valid for this market kind")
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": [12]},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        mock_settle.assert_called_once_with(
            _MARKET_ID,
            team_ids=[12],
            admin_id=7,
            subject_texts=None,
            is_text_correct=None)

    @patch(f"{_SERVICE}.get_admin_history")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_admin_history_returns_foreign_audit(
            self,
            _mock_fetch: MagicMock,
            mock_history: MagicMock) -> None:
        mock_history.return_value = [_change_row()]
        response = self.client.get(
            "/typer-lm/long-term/admin/prediction-history",
            params={
                "user_uuid": _TEST_USER["uuid"],
                "market_id": _MARKET_ID,
                "season_id": 13
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()[0]["user_uuid"], _TEST_USER["uuid"])
        mock_history.assert_called_once_with(
            _TEST_USER["uuid"], _MARKET_ID, 13)


if __name__ == "__main__":
    unittest.main()
