"""API tests for authentication gate and auth endpoints."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("OPENAPI_ENABLED", "false")

from backend.config import get_settings
from backend.services import auth_service

get_settings.cache_clear()

from api.main import create_app

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
_COMPLETE_BODY = {
    "username": "alice",
    "display_name": "Alice",
    "new_password": "newpass1",
    "new_password_confirm": "newpass1"
}


class TestAuthRouter(unittest.TestCase):
    """HTTP contract tests for login, /me, and auth kill switch."""

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

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_TEST_USER)
    def test_auth_status_requires_token(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        anonymous = self.client.get("/auth/status")
        self.assertEqual(anonymous.status_code, 401)
        response = self.client.get(
            "/auth/status",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["auth_enabled"], True)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_username",
        return_value=_TEST_USER)
    def test_login_returns_token_with_uuid_subject(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "alice", "password": "secret123"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["token_type"], "bearer")
        self.assertIn("access_token", payload)
        self.assertFalse(payload["first_login"])
        self.assertEqual(payload["username"], "alice")
        decoded = jwt.decode(
            payload["access_token"],
            get_settings().secret_key.get_secret_value(),
            algorithms=[get_settings().auth_algorithm])
        self.assertEqual(decoded["sub"], _TEST_USER["uuid"])
        self.assertNotIn("id", decoded)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_username",
        return_value=_TEST_USER)
    def test_login_rejects_bad_password(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "alice", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid username or password")

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_username",
        return_value={**_TEST_USER, "is_active": 0})
    def test_login_rejects_inactive_user(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "alice", "password": "secret123"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid username or password")

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_username",
        return_value=None)
    def test_login_does_not_reveal_missing_user(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "nobody", "password": "secret123"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid username or password")

    @patch(
        "api.routers.leagues.league_service.get_leagues",
        return_value=[])
    def test_protected_endpoint_requires_token(
        self,
        _mock_get_leagues: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues")
        self.assertEqual(response.status_code, 401)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_TEST_USER)
    @patch(
        "api.routers.leagues.league_service.get_leagues",
        return_value=[])
    def test_protected_endpoint_accepts_bearer_token(
        self,
        _mock_get_leagues: unittest.mock.MagicMock,
        _mock_fetch_uuid: unittest.mock.MagicMock) -> None:
        response = self.client.get(
            "/leagues",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_TEST_USER)
    def test_me_returns_public_user_without_id(
        self,
        _mock_fetch_uuid: unittest.mock.MagicMock) -> None:
        response = self.client.get(
            "/auth/me",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["uuid"], _TEST_USER["uuid"])
        self.assertEqual(payload["username"], "alice")
        self.assertFalse(payload["first_login"])
        self.assertNotIn("id", payload)

    def test_expired_token_is_rejected(self) -> None:
        settings = get_settings()
        expired = datetime.now(timezone.utc) - timedelta(minutes=5)
        token = jwt.encode(
            {"sub": _TEST_USER["uuid"], "exp": expired},
            settings.secret_key.get_secret_value(),
            algorithm=settings.auth_algorithm)
        response = self.client.get(
            "/leagues",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    @patch(
        "api.routers.leagues.league_service.get_leagues",
        return_value=[])
    def test_auth_disabled_allows_protected_get_without_token(
        self,
        _mock_get_leagues: unittest.mock.MagicMock) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get("/leagues")
        self.assertEqual(response.status_code, 200)
        status = client.get("/auth/status")
        self.assertEqual(status.json()["auth_enabled"], False)

    def test_openapi_disabled_by_default(self) -> None:
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/redoc").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_health_is_public_liveness_without_database(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertNotIn("database", payload)

    def test_ready_is_public_with_database_status(self) -> None:
        with patch("api.main.test_connection", return_value=True):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["database"], "healthy")

    def test_ready_returns_503_when_database_unhealthy(self) -> None:
        with patch("api.main.test_connection", return_value=False):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "unhealthy")
        self.assertEqual(payload["database"], "unhealthy")


class TestFirstLoginApi(unittest.TestCase):
    """HTTP contract for first-login flag, complete endpoint, and 403 gate."""

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

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_username",
        return_value=_FIRST_LOGIN_USER)
    def test_login_returns_first_login_true_and_username(
            self,
            _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "alice", "password": "secret123"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["first_login"])
        self.assertEqual(payload["username"], "alice")
        self.assertIn("access_token", payload)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_me_returns_first_login_true(
            self,
            _mock_fetch: unittest.mock.MagicMock) -> None:
        response = self.client.get(
            "/auth/me",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["first_login"])
        self.assertEqual(payload["username"], "alice")

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_id")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=False)
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_complete_first_login_happy_path(
            self,
            _mock_fetch_uuid: unittest.mock.MagicMock,
            mock_taken: unittest.mock.MagicMock,
            mock_update: unittest.mock.MagicMock,
            mock_fetch_id: unittest.mock.MagicMock) -> None:
        completed = {
            **_FIRST_LOGIN_USER,
            "first_login": 0,
            "username": "alice"
        }
        mock_fetch_id.return_value = completed
        response = self.client.post(
            "/auth/complete-first-login",
            json=_COMPLETE_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["user"]["first_login"])
        self.assertEqual(payload["user"]["username"], "alice")
        mock_taken.assert_called_once_with("alice", 1)
        mock_update.assert_called_once()
        _user_id, username, password_hash, display_name = (
            mock_update.call_args.args)
        self.assertEqual(_user_id, 1)
        self.assertEqual(username, "alice")
        self.assertEqual(display_name, "Alice")
        self.assertTrue(
            auth_service.verify_password("newpass1", password_hash))
        self.assertFalse(
            auth_service.verify_password("secret123", password_hash))

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_complete_first_login_requires_valid_token(
            self,
            mock_update: unittest.mock.MagicMock) -> None:
        anonymous = self.client.post(
            "/auth/complete-first-login",
            json=_COMPLETE_BODY)
        self.assertEqual(anonymous.status_code, 401)
        broken = self.client.post(
            "/auth/complete-first-login",
            json=_COMPLETE_BODY,
            headers={"Authorization": "Bearer not-a-jwt"})
        self.assertEqual(broken.status_code, 401)
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_complete_mismatch_passwords_returns_400(
            self,
            _mock_fetch: unittest.mock.MagicMock,
            mock_update: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/complete-first-login",
            json={
                "username": "alice",
                "display_name": "Alice",
                "new_password": "newpass1",
                "new_password_confirm": "otherpass"
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Passwords do not match")
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=True)
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_complete_taken_username_returns_409(
            self,
            _mock_fetch: unittest.mock.MagicMock,
            _mock_taken: unittest.mock.MagicMock,
            mock_update: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/complete-first-login",
            json={
                "username": "bob",
                "display_name": "Bob",
                "new_password": "newpass1",
                "new_password_confirm": "newpass1"
            },
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Username already taken")
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_TEST_USER)
    def test_complete_when_already_done_returns_400(
            self,
            _mock_fetch: unittest.mock.MagicMock,
            mock_update: unittest.mock.MagicMock) -> None:
        response = self.client.post(
            "/auth/complete-first-login",
            json=_COMPLETE_BODY,
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "First login already completed")
        mock_update.assert_not_called()

    @patch(
        "api.routers.leagues.league_service.get_leagues",
        return_value=[])
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_protected_endpoint_returns_403_when_first_login(
            self,
            _mock_fetch: unittest.mock.MagicMock,
            _mock_leagues: unittest.mock.MagicMock) -> None:
        response = self.client.get(
            "/leagues",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "first_login_required")

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_FIRST_LOGIN_USER)
    def test_me_and_status_allowed_when_first_login(
            self,
            _mock_fetch: unittest.mock.MagicMock) -> None:
        headers = self._auth_headers()
        me_response = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.json()["first_login"])
        status_response = self.client.get("/auth/status", headers=headers)
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()["auth_enabled"])


class TestSecurityMiddleware(unittest.TestCase):
    """Tests for TrustedHost middleware and OpenAPI exposure."""

    def tearDown(self) -> None:
        os.environ.pop("TRUSTED_HOSTS", None)
        os.environ.pop("OPENAPI_ENABLED", None)
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()

    def test_trusted_host_rejects_unknown_host(self) -> None:
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["TRUSTED_HOSTS"] = '["api.internal"]'
        get_settings.cache_clear()
        client = TestClient(create_app(), raise_server_exceptions=False)
        response = client.get(
            "/health",
            headers={"Host": "evil.example"})
        self.assertEqual(response.status_code, 400)

    def test_trusted_host_allows_configured_host(self) -> None:
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["TRUSTED_HOSTS"] = '["api.internal"]'
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get(
            "/health",
            headers={"Host": "api.internal"})
        self.assertEqual(response.status_code, 200)

    def test_openapi_enabled_exposes_schema(self) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ["OPENAPI_ENABLED"] = "true"
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.json())


if __name__ == "__main__":
    unittest.main()
