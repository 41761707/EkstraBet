"""API tests for administrative user and league endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("OPENAPI_ENABLED", "false")

from backend.config import get_settings
from backend.services import auth_service
from backend.services.admin_errors import AdminConflictError
from backend.services.admin_errors import AdminForbiddenError
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError

get_settings.cache_clear()

from api.main import create_app  # noqa: E402

_USER_SERVICE = "api.routers.admin.admin_user_service"
_LEAGUE_SERVICE = "api.routers.admin.admin_league_service"
_FETCH_UUID = (
    "backend.services.auth_service.user_repository.fetch_user_by_uuid")

_USER_UUID = "11111111-1111-1111-1111-111111111111"
_ADMIN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

_REGULAR_USER = {
    "id": 4,
    "uuid": _USER_UUID,
    "username": "alice",
    "password_hash": auth_service.hash_password("secret123"),
    "display_name": "Alice",
    "is_active": 1,
    "is_admin": 0,
    "first_login": 0,
    "created_at": None,
    "updated_at": None}

_ADMIN_USER = {
    **_REGULAR_USER,
    "id": 7,
    "uuid": _ADMIN_UUID,
    "username": "admin",
    "is_admin": 1}

_ADMIN_USER_DTO = {
    "uuid": _USER_UUID,
    "username": "alice",
    "display_name": "Alice",
    "is_active": True,
    "is_admin": False,
    "first_login": True,
    "created_at": None,
    "updated_at": None}

_ADMIN_LEAGUE_DTO = {
    "id": 48,
    "name": "Test League",
    "country_id": 1,
    "country_name": "Polska",
    "country_emoji": "🇵🇱",
    "sport_id": 1,
    "sport_name": "Piłka nożna",
    "active": True,
    "last_update": None,
    "current_season_id": 13,
    "tier": 1,
    "has_player_stats": False}

_CREATE_USER_BODY = {
    "username": "bob",
    "temporary_password": "secret1",
    "display_name": "Bob",
    "is_admin": False}

_CREATE_LEAGUE_BODY = {
    "name": "Test League",
    "country_id": 1,
    "sport_id": 1,
    "current_season_id": 13,
    "tier": 1,
    "has_player_stats": False}

_PROTECTED_CASES = [
    ("GET", "/admin/users", None),
    ("POST", "/admin/users", _CREATE_USER_BODY),
    ("PUT", f"/admin/users/{_USER_UUID}/active", {"is_active": False}),
    ("PUT", f"/admin/users/{_USER_UUID}/admin", {"is_admin": True}),
    ("GET", "/admin/leagues", None),
    ("POST", "/admin/leagues", _CREATE_LEAGUE_BODY),
    ("PUT", "/admin/leagues/48/active", {"active": False}),
    ("GET", "/admin/countries", None),
    ("GET", "/admin/sports", None),
    ("GET", "/admin/seasons", None)]

_SECRET_KEYS = ("id", "password_hash", "password", "temporary_password")


class AdminRouterTestCase(unittest.TestCase):
    """Authenticated TestClient shared by admin contract cases."""

    user: dict[str, object] = _ADMIN_USER

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

    def _assert_no_secrets(self, payload: dict[str, object]) -> None:
        for key in _SECRET_KEYS:
            self.assertNotIn(key, payload)


class TestAdminRouterAuth(AdminRouterTestCase):
    """401 without a token and 403 for a non-admin on every endpoint."""

    def test_all_endpoints_require_token(self) -> None:
        for method, path, body in _PROTECTED_CASES:
            with self.subTest(method=method, path=path):
                kwargs = {"json": body} if body is not None else {}
                response = self.client.request(method, path, **kwargs)
                self.assertEqual(response.status_code, 401)

    @patch(_FETCH_UUID, return_value=_REGULAR_USER)
    def test_regular_user_is_forbidden(
            self, _mock_fetch: MagicMock) -> None:
        self.user = _REGULAR_USER
        for method, path, body in _PROTECTED_CASES:
            with self.subTest(method=method, path=path):
                kwargs = {"json": body} if body is not None else {}
                response = self.client.request(
                    method,
                    path,
                    headers=self._auth_headers(),
                    **kwargs)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json()["detail"],
                    "Administrator role required")


class TestAdminUsersRouter(AdminRouterTestCase):
    """HTTP contract for user list, create and flag toggles."""

    @patch(f"{_USER_SERVICE}.list_users", return_value=[_ADMIN_USER_DTO])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_users_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/users",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["uuid"], _USER_UUID)
        self.assertTrue(payload[0]["first_login"])
        self._assert_no_secrets(payload[0])
        mock_list.assert_called_once_with()

    @patch(f"{_USER_SERVICE}.create_user", return_value=_ADMIN_USER_DTO)
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_create_user_returns_201_without_password(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        response = self.client.post(
            "/admin/users",
            json=_CREATE_USER_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["username"], "alice")
        self._assert_no_secrets(payload)
        mock_create.assert_called_once_with("bob", "secret1", "Bob", False)

    @patch(f"{_USER_SERVICE}.create_user")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_duplicate_username_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        mock_create.side_effect = AdminConflictError(
            "Username already taken")
        response = self.client.post(
            "/admin/users",
            json=_CREATE_USER_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Username already taken")

    @patch(f"{_USER_SERVICE}.create_user")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_invalid_user_payload_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        mock_create.side_effect = AdminValidationError(
            "Username must be between 1 and 50 characters")
        response = self.client.post(
            "/admin/users",
            json=_CREATE_USER_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        self.assertIn("Username", response.json()["detail"])

    @patch(f"{_USER_SERVICE}.set_user_active", return_value=_ADMIN_USER_DTO)
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_set_user_active_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        response = self.client.put(
            f"/admin/users/{_USER_UUID}/active",
            json={"is_active": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uuid"], _USER_UUID)
        mock_set.assert_called_once()
        actor, user_uuid, is_active = mock_set.call_args.args
        self.assertEqual(actor["uuid"], _ADMIN_UUID)
        self.assertEqual(user_uuid, _USER_UUID)
        self.assertFalse(is_active)

    @patch(f"{_USER_SERVICE}.set_user_active")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_missing_user_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        mock_set.side_effect = AdminNotFoundError("User not found")
        response = self.client.put(
            f"/admin/users/{_USER_UUID}/active",
            json={"is_active": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "User not found")

    @patch(f"{_USER_SERVICE}.set_user_active")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_self_deactivation_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        mock_set.side_effect = AdminForbiddenError(
            "Cannot deactivate your own account")
        response = self.client.put(
            f"/admin/users/{_ADMIN_UUID}/active",
            json={"is_active": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Cannot deactivate your own account")

    @patch(f"{_USER_SERVICE}.set_user_admin", return_value={
        **_ADMIN_USER_DTO,
        "is_admin": True})
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_set_user_admin_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        response = self.client.put(
            f"/admin/users/{_USER_UUID}/admin",
            json={"is_admin": True},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_admin"])
        mock_set.assert_called_once()
        actor, user_uuid, is_admin = mock_set.call_args.args
        self.assertEqual(actor["uuid"], _ADMIN_UUID)
        self.assertEqual(user_uuid, _USER_UUID)
        self.assertTrue(is_admin)

    @patch(f"{_USER_SERVICE}.set_user_admin")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_self_admin_revocation_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        mock_set.side_effect = AdminForbiddenError(
            "Cannot revoke your own admin role")
        response = self.client.put(
            f"/admin/users/{_ADMIN_UUID}/admin",
            json={"is_admin": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Cannot revoke your own admin role")


class TestAdminLeaguesRouter(AdminRouterTestCase):
    """HTTP contract for league list, create, toggle and dictionaries."""

    @patch(
        f"{_LEAGUE_SERVICE}.list_leagues",
        return_value=[_ADMIN_LEAGUE_DTO])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_leagues_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/leagues",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], 48)
        self.assertTrue(payload[0]["active"])
        self.assertFalse(payload[0]["has_player_stats"])
        mock_list.assert_called_once_with()

    @patch(
        f"{_LEAGUE_SERVICE}.create_league",
        return_value=_ADMIN_LEAGUE_DTO)
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_create_league_returns_201(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        response = self.client.post(
            "/admin/leagues",
            json=_CREATE_LEAGUE_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Test League")
        mock_create.assert_called_once_with(
            "Test League", 1, 1, 13, 1, False)

    @patch(f"{_LEAGUE_SERVICE}.create_league")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_unknown_country_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        mock_create.side_effect = AdminValidationError("Country not found")
        response = self.client.post(
            "/admin/leagues",
            json=_CREATE_LEAGUE_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Country not found")

    @patch(f"{_LEAGUE_SERVICE}.set_league_active")
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_missing_league_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        mock_set.side_effect = AdminNotFoundError("League not found")
        response = self.client.put(
            "/admin/leagues/48/active",
            json={"active": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "League not found")

    @patch(
        f"{_LEAGUE_SERVICE}.set_league_active",
        return_value={**_ADMIN_LEAGUE_DTO, "active": False})
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_set_league_active_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_set: MagicMock) -> None:
        response = self.client.put(
            "/admin/leagues/48/active",
            json={"active": False},
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["active"])
        mock_set.assert_called_once_with(48, False)

    @patch(
        f"{_LEAGUE_SERVICE}.list_countries",
        return_value=[{
            "id": 1,
            "name": "Polska",
            "short_name": "POL",
            "emoji": "🇵🇱"}])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_countries_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/countries",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["name"], "Polska")
        self.assertEqual(payload[0]["short_name"], "POL")
        mock_list.assert_called_once_with()

    @patch(
        f"{_LEAGUE_SERVICE}.list_countries",
        return_value=[{
            "id": 28,
            "name": None,
            "short_name": "",
            "emoji": ""}])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_countries_allows_null_name(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/countries",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()[0]["name"])

    @patch(
        f"{_LEAGUE_SERVICE}.list_leagues",
        return_value=[{
            **_ADMIN_LEAGUE_DTO,
            "last_update": date(2026, 8, 31)}])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_leagues_accepts_date_last_update(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/leagues",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["last_update"], "2026-08-31")

    @patch(
        f"{_LEAGUE_SERVICE}.list_sports",
        return_value=[{"id": 1, "name": "Piłka nożna"}])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_sports_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/sports",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Piłka nożna")
        mock_list.assert_called_once_with()

    @patch(
        f"{_LEAGUE_SERVICE}.list_seasons",
        return_value=[{"id": 13, "years": "2026/27"}])
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_list_seasons_returns_years_not_name(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/admin/seasons",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()[0]
        self.assertEqual(payload["years"], "2026/27")
        self.assertNotIn("name", payload)
        mock_list.assert_called_once_with()
