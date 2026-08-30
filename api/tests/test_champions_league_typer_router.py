"""API tests for Champions League Typer endpoints."""

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
from backend.services.champions_league_typer_service import (
    TyperConflictError,
    TyperNotFoundError,
    TyperValidationError)

get_settings.cache_clear()

from api.main import create_app

_SERVICE = "api.routers.champions_league_typer.typer_service"
_FETCH_UUID = (
    "backend.services.auth_service.user_repository.fetch_user_by_uuid")
_GAME_DATE = datetime(2026, 9, 16, 21, 0)
_PUBLISHED_AT = datetime(2026, 9, 10, 12, 0)
_CHANGED_AT = datetime(2026, 9, 11, 18, 30)

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


def _team() -> dict[str, object]:
    return {"id": 1, "name": "Home", "shortcut": "HOM"}


def _away() -> dict[str, object]:
    return {"id": 2, "name": "Away", "shortcut": "AWY"}


def _dashboard_payload() -> dict[str, object]:
    return {
        "season_id": 13,
        "rounds": [{
            "round_number": 1,
            "round_label": "1",
            "matches": [{
                "match_id": 101,
                "season_id": 13,
                "round_number": 1,
                "game_date": _GAME_DATE,
                "published_at": _PUBLISHED_AT,
                "is_locked": False,
                "result": None,
                "home_team": _team(),
                "away_team": _away(),
                "odds_home": None,
                "odds_draw": None,
                "odds_away": 3.4,
                "outcome": "2",
                "points": None,
                "changes": [{
                    "match_id": 101,
                    "user_uuid": _TEST_USER["uuid"],
                    "display_name": "Alice",
                    "previous_outcome": None,
                    "new_outcome": "2",
                    "changed_at": _CHANGED_AT
                }]
            }]
        }]
    }


class TyperRouterTestCase(unittest.TestCase):
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


class TestTyperParticipantRouter(TyperRouterTestCase):
    """HTTP contract for participant dashboard, picks, history and ranking."""

    @patch(f"{_SERVICE}.get_dashboard")
    def test_dashboard_requires_token(
            self, mock_dashboard: MagicMock) -> None:
        response = self.client.get("/typer-lm/dashboard")
        self.assertEqual(response.status_code, 401)
        mock_dashboard.assert_not_called()

    @patch(
        f"{_SERVICE}.get_dashboard",
        return_value=_dashboard_payload())
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_dashboard_returns_private_contract(
            self,
            _mock_fetch: MagicMock,
            _mock_dashboard: MagicMock) -> None:
        response = self.client.get(
            "/typer-lm/dashboard?season_id=13",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        match = payload["rounds"][0]["matches"][0]
        self.assertEqual(payload["season_id"], 13)
        self.assertIsNone(match["odds_home"])
        self.assertEqual(match["odds_away"], 3.4)
        self.assertEqual(match["outcome"], "2")
        self.assertNotIn("user_id", match)
        self.assertNotIn("id", payload)

    @patch(f"{_SERVICE}.save_prediction")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_prediction_returns_saved_pick(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.return_value = {
            "match_id": 101,
            "outcome": "1",
            "previous_outcome": None,
            "audit_written": True,
            "created_at": _CHANGED_AT,
            "updated_at": _CHANGED_AT
        }
        response = self.client.put(
            "/typer-lm/predictions/101",
            json={"outcome": "1"},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "1")
        mock_save.assert_called_once_with(4, 101, "1")

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_invalid_outcome_returns_422(
            self, _mock_fetch: MagicMock) -> None:
        response = self.client.put(
            "/typer-lm/predictions/101",
            json={"outcome": "0"},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(f"{_SERVICE}.save_prediction")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_deadline_conflict_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperConflictError(
            "Prediction cannot be saved after kickoff")
        response = self.client.put(
            "/typer-lm/predictions/101",
            json={"outcome": "X"},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)

    @patch(f"{_SERVICE}.save_prediction")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_unknown_match_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_save: MagicMock) -> None:
        mock_save.side_effect = TyperNotFoundError(
            "Published match not found")
        response = self.client.put(
            "/typer-lm/predictions/999",
            json={"outcome": "1"},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)

    @patch(
        f"{_SERVICE}.get_own_prediction_history",
        return_value=[{
            "match_id": 101,
            "user_uuid": _TEST_USER["uuid"],
            "display_name": "Alice",
            "previous_outcome": None,
            "new_outcome": "1",
            "changed_at": _CHANGED_AT
        }])
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_own_history_contract(
            self,
            _mock_fetch: MagicMock,
            _mock_history: MagicMock) -> None:
        response = self.client.get(
            "/typer-lm/predictions/101/history",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["new_outcome"], "1")

    @patch(
        f"{_SERVICE}.get_leaderboard",
        return_value=[{
            "place": 1,
            "user_uuid": "u-1",
            "display_name": "Ada",
            "total_points": 5.5,
            "correct_predictions": 2,
            "settled_predictions": 3
        }])
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_leaderboard_hides_picks(
            self,
            _mock_fetch: MagicMock,
            _mock_board: MagicMock) -> None:
        response = self.client.get(
            "/typer-lm/leaderboard",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        row = response.json()[0]
        self.assertEqual(row["total_points"], 5.5)
        self.assertNotIn("outcome", row)
        self.assertNotIn("selected_event_id", row)


class TestTyperAdminRouter(TyperRouterTestCase):
    """Admin mutations and foreign audit require is_admin."""

    user = _ADMIN_USER

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_regular_user_cannot_read_foreign_audit(
            self, _mock_fetch: MagicMock) -> None:
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        response = self.client.get(
            "/typer-lm/admin/prediction-history",
            params={"user_uuid": _TEST_USER["uuid"]},
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_regular_user_cannot_publish(
            self, _mock_fetch: MagicMock) -> None:
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": list(range(101, 110))
            },
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    @patch(f"{_SERVICE}.publish_matches")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_publish_without_odds_returns_201(
            self,
            _mock_fetch: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_publish.return_value = [{
            "match_id": 101,
            "season_id": 13,
            "round_number": 1,
            "published_at": _PUBLISHED_AT
        }]
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": list(range(101, 110))
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["publications"][0]["match_id"], 101)
        mock_publish.assert_called_once_with(
            13, 1, list(range(101, 110)), 7)

    @patch(f"{_SERVICE}.publish_matches")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_wrong_group_count_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_publish.side_effect = TyperValidationError(
            "Group-stage round must have exactly 9 published matches")
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": [101, 102, 103, 104, 105]
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(f"{_SERVICE}.publish_matches")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_duplicate_match_ids_return_422(
            self,
            _mock_fetch: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_publish.side_effect = TyperValidationError(
            "Duplicate match ids in publication set")
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": [101, 101, *range(102, 110)]
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(f"{_SERVICE}.publish_matches")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_second_group_stage_batch_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_publish.side_effect = TyperValidationError(
            "Group-stage round must have exactly 9 published matches")
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": list(range(201, 210))
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)

    @patch(f"{_SERVICE}.publish_matches")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_republish_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_publish.side_effect = TyperConflictError(
            "One or more matches are already published")
        response = self.client.post(
            "/typer-lm/admin/publications",
            json={
                "season_id": 13,
                "round_number": 1,
                "match_ids": list(range(101, 110))
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)

    @patch(f"{_SERVICE}.get_admin_candidates")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_candidates_expose_odds_flag_without_requiring_odds(
            self,
            _mock_fetch: MagicMock,
            mock_candidates: MagicMock) -> None:
        mock_candidates.return_value = [{
            "match_id": 101,
            "season_id": 13,
            "round_number": 1,
            "game_date": _GAME_DATE,
            "home_team": _team(),
            "away_team": _away(),
            "is_published": False,
            "has_complete_superbet_odds": False
        }]
        response = self.client.get(
            "/typer-lm/admin/candidates",
            params={"season_id": 13, "round_number": 1},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        candidate = payload["candidates"][0]
        self.assertFalse(candidate["has_complete_superbet_odds"])
        self.assertFalse(candidate["is_published"])
        self.assertEqual(payload["group_match_count"], 9)

    @patch(f"{_SERVICE}.remove_publication")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_delete_publication_returns_204(
            self,
            _mock_fetch: MagicMock,
            mock_remove: MagicMock) -> None:
        mock_remove.return_value = None
        response = self.client.delete(
            "/typer-lm/admin/publications/101",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 204)
        mock_remove.assert_called_once_with(101, 7)

    @patch(f"{_SERVICE}.get_admin_prediction_history")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_admin_history_returns_audit(
            self,
            _mock_fetch: MagicMock,
            mock_history: MagicMock) -> None:
        mock_history.return_value = [{
            "match_id": 101,
            "user_uuid": _TEST_USER["uuid"],
            "display_name": "Alice",
            "previous_outcome": "1",
            "new_outcome": "X",
            "changed_at": _CHANGED_AT
        }]
        response = self.client.get(
            "/typer-lm/admin/prediction-history",
            params={
                "user_uuid": _TEST_USER["uuid"],
                "match_id": 101,
                "season_id": 13
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["new_outcome"], "X")
        mock_history.assert_called_once_with(
            _TEST_USER["uuid"], 101, 13)


if __name__ == "__main__":
    unittest.main()
