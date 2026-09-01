"""API tests for Typer long-term market endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("OPENAPI_ENABLED", "false")

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
_TEAM_IDS = [12, 45, 101, 200, 201, 202, 203, 204]
_SEVEN_IDS = _TEAM_IDS[:7]

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
        "new_team_ids": list(_TEAM_IDS),
        "changed_at": _CHANGED_AT
    }


def _dashboard_payload() -> dict[str, object]:
    return {
        "season_id": 13,
        "markets": [{
            "market_id": _MARKET_ID,
            "league_id": 42,
            "season_id": 13,
            "market_key": "top8_direct_r16",
            "title": "TOP 8",
            "description": "Pick 8 teams",
            "selection_size": 8,
            "points_per_correct": 2.0,
            "settled_at": None,
            "deadline_at": _DEADLINE,
            "is_locked": False,
            "candidates": [_candidate(team_id) for team_id in _TEAM_IDS],
            "picked_team_ids": list(_TEAM_IDS),
            "result_team_ids": [],
            "points": None,
            "changes": [_change_row()]
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
    proposed = [_standing(team_id) for team_id in _TEAM_IDS]
    return {
        "market_id": _MARKET_ID,
        "league_id": 42,
        "season_id": 13,
        "market_key": "top8_direct_r16",
        "selection_size": 8,
        "points_per_correct": 2.0,
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
        "proposed_team_ids": list(_TEAM_IDS) if complete else [],
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
        self.assertEqual(market["picked_team_ids"], list(_TEAM_IDS))
        self.assertIsNone(market["points"])
        self.assertNotIn("user_id", market)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("settled_by", market)
        mock_dashboard.assert_called_once_with(4, 13)

    @patch(f"{_SERVICE}.save_picks")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_picks_returns_saved_set(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.return_value = {
            "market_id": _MARKET_ID,
            "team_ids": list(_TEAM_IDS),
            "previous_team_ids": None,
            "audit_written": True
        }
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": list(_TEAM_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team_ids"], list(_TEAM_IDS))
        self.assertTrue(payload["audit_written"])
        self.assertNotIn("user_id", payload)
        mock_save.assert_called_once_with(4, _MARKET_ID, list(_TEAM_IDS))

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
            "Long-term pick set must have exactly 8 teams")
        response = self.client.put(
            f"/typer-lm/long-term/markets/{_MARKET_ID}/picks",
            json={"team_ids": list(_SEVEN_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        mock_save.assert_called_once_with(4, _MARKET_ID, list(_SEVEN_IDS))

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
        self.assertEqual(response.json()[0]["new_team_ids"], list(_TEAM_IDS))
        mock_history.assert_called_once_with(4, _MARKET_ID)

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
        self.assertEqual(payload["proposed_team_ids"], list(_TEAM_IDS))
        self.assertEqual(payload["result_team_ids"], [])
        self.assertIsNone(payload["settled_by_uuid"])
        self.assertNotIn("settled_by", payload)
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
        self.assertEqual(payload["proposed_teams"], [])
        self.assertEqual(payload["result_team_ids"], [])

    @patch(
        f"{_SERVICE}.get_auto_result",
        return_value=_auto_result_payload(
            result_team_ids=[12, 45, 101, 200, 201, 202, 203, 205]))
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
        self.assertEqual(payload["proposed_team_ids"], list(_TEAM_IDS))
        self.assertEqual(
            payload["result_team_ids"],
            [12, 45, 101, 200, 201, 202, 203, 205])
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
            json={"team_ids": list(_TEAM_IDS)},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)
        mock_settle.assert_called_once_with(
            _MARKET_ID, list(_TEAM_IDS), 7)

    @patch(f"{_SERVICE}.settle_market")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_admin_correction_returns_settled_set(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        corrected = [12, 45, 101, 200, 201, 202, 203, 205]
        mock_settle.return_value = {
            "market_id": _MARKET_ID,
            "team_ids": corrected,
            "settled_by_uuid": _ADMIN_USER["uuid"],
            "settled_by_display_name": "Alice",
            "settled_at": _SETTLED_AT,
            "result_team_ids": corrected
        }
        response = self.client.post(
            f"/typer-lm/long-term/admin/markets/{_MARKET_ID}/settle",
            json={"team_ids": corrected},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team_ids"], corrected)
        self.assertEqual(payload["result_team_ids"], corrected)
        self.assertEqual(payload["settled_by_uuid"], _ADMIN_USER["uuid"])
        self.assertNotIn("settled_by", payload)
        mock_settle.assert_called_once_with(_MARKET_ID, corrected, 7)

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
