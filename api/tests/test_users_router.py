"""API tests for the current-user favorite leagues contract."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("OPENAPI_ENABLED", "false")

from backend.config import get_settings
from backend.services import auth_service
from backend.services.favorite_league_service import LeagueNotAvailableError
from backend.services.user_preferences_service import InvalidThemeError

get_settings.cache_clear()

from api.main import create_app

_FAVORITES_PATH = "/users/me/favorite-leagues"
_PREFERENCES_PATH = "/users/me/preferences"
_GET_IDS = (
    "api.routers.users.favorite_league_service.get_favorite_league_ids")
_ADD = "api.routers.users.favorite_league_service.add_favorite_league"
_REMOVE = (
    "api.routers.users.favorite_league_service.remove_favorite_league")
_GET_PREFS = (
    "api.routers.users.user_preferences_service.get_preferences")
_UPDATE_THEME = (
    "api.routers.users.user_preferences_service.update_theme")
_FETCH_UUID = (
    "backend.services.auth_service.user_repository.fetch_user_by_uuid")

_TEST_USER = {
    "id": 1,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice",
    "password_hash": auth_service.hash_password("secret123"),
    "display_name": "Alice",
    "is_active": 1,
    "first_login": 0,
    "created_at": None,
    "updated_at": None
}
_FIRST_LOGIN_USER = {
    **_TEST_USER,
    "first_login": 1
}


class TestUsersFavoriteLeaguesRouter(unittest.TestCase):
    """HTTP contract for GET/PUT/DELETE favorite leagues."""

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
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        return {"Authorization": f"Bearer {token}"}

    def _assert_no_internal_user_id(self, payload: dict[str, object]) -> None:
        self.assertNotIn("id", payload)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("uuid", payload)

    @patch(_GET_IDS, return_value=[1, 4])
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_get_returns_sorted_league_ids_without_user_id(
            self,
            _mock_fetch: MagicMock,
            mock_get_ids: MagicMock) -> None:
        response = self.client.get(
            _FAVORITES_PATH,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, {"league_ids": [1, 4]})
        self._assert_no_internal_user_id(payload)
        mock_get_ids.assert_called_once()
        passed_user = mock_get_ids.call_args.args[0]
        self.assertEqual(passed_user["id"], 1)
        self.assertEqual(passed_user["username"], "alice")

    @patch(_GET_IDS, return_value=[])
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_get_returns_empty_list(
            self,
            _mock_fetch: MagicMock,
            _mock_get_ids: MagicMock) -> None:
        response = self.client.get(
            _FAVORITES_PATH,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"league_ids": []})

    @patch(_ADD)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_returns_favorite_true(
            self,
            _mock_fetch: MagicMock,
            mock_add: MagicMock) -> None:
        response = self.client.put(
            f"{_FAVORITES_PATH}/1",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload,
            {"league_id": 1, "is_favorite": True})
        self._assert_no_internal_user_id(payload)
        mock_add.assert_called_once()
        passed_user, league_id = mock_add.call_args.args
        self.assertEqual(passed_user["id"], 1)
        self.assertEqual(league_id, 1)

    @patch(_ADD)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_is_idempotent(
            self,
            _mock_fetch: MagicMock,
            mock_add: MagicMock) -> None:
        headers = self._auth_headers()
        first = self.client.put(f"{_FAVORITES_PATH}/1", headers=headers)
        second = self.client.put(f"{_FAVORITES_PATH}/1", headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["is_favorite"], True)
        self.assertEqual(second.json()["is_favorite"], True)
        self.assertEqual(mock_add.call_count, 2)

    @patch(
        _ADD,
        side_effect=LeagueNotAvailableError("League not available"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_unavailable_league_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_add: MagicMock) -> None:
        response = self.client.put(
            f"{_FAVORITES_PATH}/999",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "League not available")
        mock_add.assert_called_once()

    @patch(_REMOVE)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_delete_returns_favorite_false(
            self,
            _mock_fetch: MagicMock,
            mock_remove: MagicMock) -> None:
        response = self.client.delete(
            f"{_FAVORITES_PATH}/1",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload,
            {"league_id": 1, "is_favorite": False})
        self._assert_no_internal_user_id(payload)
        mock_remove.assert_called_once()
        passed_user, league_id = mock_remove.call_args.args
        self.assertEqual(passed_user["id"], 1)
        self.assertEqual(league_id, 1)

    @patch(_REMOVE)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_delete_is_idempotent_when_relation_missing(
            self,
            _mock_fetch: MagicMock,
            mock_remove: MagicMock) -> None:
        headers = self._auth_headers()
        first = self.client.delete(f"{_FAVORITES_PATH}/8", headers=headers)
        second = self.client.delete(f"{_FAVORITES_PATH}/8", headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["is_favorite"], False)
        self.assertEqual(second.json()["is_favorite"], False)
        self.assertEqual(mock_remove.call_count, 2)

    def test_endpoints_require_token(self) -> None:
        get_response = self.client.get(_FAVORITES_PATH)
        put_response = self.client.put(f"{_FAVORITES_PATH}/1")
        delete_response = self.client.delete(f"{_FAVORITES_PATH}/1")
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.status_code, 401)
        self.assertEqual(delete_response.status_code, 401)

    @patch(_GET_IDS)
    @patch(_ADD)
    @patch(_REMOVE)
    def test_invalid_token_is_rejected(
            self,
            mock_remove: MagicMock,
            mock_add: MagicMock,
            mock_get_ids: MagicMock) -> None:
        headers = {"Authorization": "Bearer not-a-jwt"}
        get_response = self.client.get(_FAVORITES_PATH, headers=headers)
        put_response = self.client.put(
            f"{_FAVORITES_PATH}/1",
            headers=headers)
        delete_response = self.client.delete(
            f"{_FAVORITES_PATH}/1",
            headers=headers)
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.status_code, 401)
        self.assertEqual(delete_response.status_code, 401)
        mock_get_ids.assert_not_called()
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    @patch(_GET_IDS)
    @patch(_ADD)
    @patch(_REMOVE)
    @patch(_FETCH_UUID, return_value=_FIRST_LOGIN_USER)
    def test_first_login_is_blocked(
            self,
            _mock_fetch: MagicMock,
            mock_remove: MagicMock,
            mock_add: MagicMock,
            mock_get_ids: MagicMock) -> None:
        headers = self._auth_headers()
        get_response = self.client.get(_FAVORITES_PATH, headers=headers)
        put_response = self.client.put(
            f"{_FAVORITES_PATH}/1",
            headers=headers)
        delete_response = self.client.delete(
            f"{_FAVORITES_PATH}/1",
            headers=headers)
        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(get_response.json()["detail"], "first_login_required")
        self.assertEqual(put_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        mock_get_ids.assert_not_called()
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    @patch(_ADD)
    @patch(_REMOVE)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_league_id_below_one_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_remove: MagicMock,
            mock_add: MagicMock) -> None:
        headers = self._auth_headers()
        for league_id in (0, -1):
            put_response = self.client.put(
                f"{_FAVORITES_PATH}/{league_id}",
                headers=headers)
            delete_response = self.client.delete(
                f"{_FAVORITES_PATH}/{league_id}",
                headers=headers)
            self.assertEqual(put_response.status_code, 422)
            self.assertEqual(delete_response.status_code, 422)
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    @patch(_GET_IDS)
    def test_auth_disabled_hides_endpoints(
            self,
            mock_get_ids: MagicMock) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get(_FAVORITES_PATH)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Authentication is disabled")
        mock_get_ids.assert_not_called()


class TestUsersPreferencesRouter(unittest.TestCase):
    """HTTP contract for GET/PUT /users/me/preferences."""

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
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        return {"Authorization": f"Bearer {token}"}

    def _assert_no_internal_user_id(self, payload: dict[str, object]) -> None:
        self.assertNotIn("id", payload)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("uuid", payload)

    @patch(_GET_PREFS, return_value={"theme": "light"})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_get_returns_theme_without_user_id(
            self,
            _mock_fetch: MagicMock,
            mock_get_prefs: MagicMock) -> None:
        response = self.client.get(
            _PREFERENCES_PATH,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, {"theme": "light"})
        self._assert_no_internal_user_id(payload)
        mock_get_prefs.assert_called_once()
        passed_user = mock_get_prefs.call_args.args[0]
        self.assertEqual(passed_user["id"], 1)

    @patch(_GET_PREFS, return_value=None)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_get_missing_row_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_get_prefs: MagicMock) -> None:
        response = self.client.get(
            _PREFERENCES_PATH,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Preferences not found")
        mock_get_prefs.assert_called_once()

    @patch(_UPDATE_THEME, return_value={"theme": "light"})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_light_then_returns_light(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock) -> None:
        response = self.client.put(
            _PREFERENCES_PATH,
            headers=self._auth_headers(),
            json={"theme": "light"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, {"theme": "light"})
        self._assert_no_internal_user_id(payload)
        mock_update.assert_called_once()
        passed_user, theme = mock_update.call_args.args
        self.assertEqual(passed_user["id"], 1)
        self.assertEqual(theme, "light")

    @patch(_GET_PREFS, return_value={"theme": "light"})
    @patch(_UPDATE_THEME, return_value={"theme": "light"})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_light_then_get_returns_light(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock,
            mock_get_prefs: MagicMock) -> None:
        headers = self._auth_headers()
        put_response = self.client.put(
            _PREFERENCES_PATH,
            headers=headers,
            json={"theme": "light"})
        get_response = self.client.get(
            _PREFERENCES_PATH,
            headers=headers)
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json(), {"theme": "light"})
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json(), {"theme": "light"})
        mock_update.assert_called_once()
        mock_get_prefs.assert_called_once()

    @patch(_UPDATE_THEME)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_sepia_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock) -> None:
        response = self.client.put(
            _PREFERENCES_PATH,
            headers=self._auth_headers(),
            json={"theme": "sepia"})
        self.assertEqual(response.status_code, 422)
        mock_update.assert_not_called()

    @patch(_UPDATE_THEME)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_empty_body_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock) -> None:
        response = self.client.put(
            _PREFERENCES_PATH,
            headers=self._auth_headers(),
            json={})
        self.assertEqual(response.status_code, 422)
        mock_update.assert_not_called()

    @patch(
        _UPDATE_THEME,
        side_effect=InvalidThemeError("Invalid theme"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_service_reject_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock) -> None:
        response = self.client.put(
            _PREFERENCES_PATH,
            headers=self._auth_headers(),
            json={"theme": "dark"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Invalid theme")
        mock_update.assert_called_once()

    def test_endpoints_require_token(self) -> None:
        get_response = self.client.get(_PREFERENCES_PATH)
        put_response = self.client.put(
            _PREFERENCES_PATH,
            json={"theme": "light"})
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.status_code, 401)

    @patch(_GET_PREFS)
    @patch(_UPDATE_THEME)
    def test_invalid_token_is_rejected(
            self,
            mock_update: MagicMock,
            mock_get_prefs: MagicMock) -> None:
        headers = {"Authorization": "Bearer not-a-jwt"}
        get_response = self.client.get(_PREFERENCES_PATH, headers=headers)
        put_response = self.client.put(
            _PREFERENCES_PATH,
            headers=headers,
            json={"theme": "light"})
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.status_code, 401)
        mock_get_prefs.assert_not_called()
        mock_update.assert_not_called()

    @patch(_GET_PREFS)
    @patch(_UPDATE_THEME)
    @patch(_FETCH_UUID, return_value=_FIRST_LOGIN_USER)
    def test_first_login_is_blocked(
            self,
            _mock_fetch: MagicMock,
            mock_update: MagicMock,
            mock_get_prefs: MagicMock) -> None:
        headers = self._auth_headers()
        get_response = self.client.get(_PREFERENCES_PATH, headers=headers)
        put_response = self.client.put(
            _PREFERENCES_PATH,
            headers=headers,
            json={"theme": "light"})
        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(get_response.json()["detail"], "first_login_required")
        self.assertEqual(put_response.status_code, 403)
        mock_get_prefs.assert_not_called()
        mock_update.assert_not_called()

    @patch(_GET_PREFS)
    def test_auth_disabled_hides_endpoints(
            self,
            mock_get_prefs: MagicMock) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get(_PREFERENCES_PATH)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Authentication is disabled")
        mock_get_prefs.assert_not_called()


if __name__ == "__main__":
    unittest.main()
