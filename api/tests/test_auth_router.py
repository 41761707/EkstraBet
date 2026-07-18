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
    "created_at": None,
    "updated_at": None,
}


class TestAuthRouter(unittest.TestCase):
    """HTTP contract tests for login, /me, and auth kill switch."""

    def setUp(self) -> None:
        os.environ["AUTH_ENABLED"] = "true"
        get_settings.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()

    def test_auth_status_reports_enabled(self) -> None:
        response = self.client.get("/auth/status")
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
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        response = self.client.get(
            "/leagues",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_uuid",
        return_value=_TEST_USER)
    def test_me_returns_public_user_without_id(
        self,
        _mock_fetch_uuid: unittest.mock.MagicMock) -> None:
        token, _ = auth_service.create_access_token(_TEST_USER["uuid"])
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["uuid"], _TEST_USER["uuid"])
        self.assertEqual(payload["username"], "alice")
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


if __name__ == "__main__":
    unittest.main()
