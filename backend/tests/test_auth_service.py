"""Unit tests for password hashing and first-login completion."""

from __future__ import annotations

import unicodedata
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.services.auth_service import (
    AuthError,
    UsernameTakenError,
    complete_first_login,
    hash_password,
    to_public_user,
    verify_password)

_FIRST_LOGIN_USER = {
    "id": 7,
    "uuid": "11111111-2222-3333-4444-555555555555",
    "username": "alice",
    "password_hash": "old-hash",
    "display_name": "Alice",
    "is_active": 1,
    "first_login": 1
}


class TestAuthPasswordUnicode(unittest.TestCase):
    """Passwords with Polish diacritics must hash and verify reliably."""

    def test_polish_password_roundtrip(self) -> None:
        plain = "zażółć gęślą jaźń"
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("zazólc gesla jazn", hashed))

    def test_polish_password_longer_than_bcrypt_byte_limit(self) -> None:
        # 40 x 'ą' = 80 bajtów UTF-8 — samo bcrypt by odrzuciło ten sekret
        plain = "ą" * 40
        self.assertGreater(len(plain.encode("utf-8")), 72)
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))

    def test_nfc_and_nfd_forms_verify_the_same_hash(self) -> None:
        plain_nfc = unicodedata.normalize("NFC", "zażółć")
        plain_nfd = unicodedata.normalize("NFD", "zażółć")
        self.assertNotEqual(plain_nfc, plain_nfd)
        hashed = hash_password(plain_nfc)
        self.assertTrue(verify_password(plain_nfd, hashed))


class TestToPublicUser(unittest.TestCase):
    """Public user payload must expose first_login as a boolean."""

    def test_maps_tinyint_one_to_true(self) -> None:
        public = to_public_user(_FIRST_LOGIN_USER)
        self.assertEqual(public["uuid"], _FIRST_LOGIN_USER["uuid"])
        self.assertEqual(public["username"], "alice")
        self.assertEqual(public["display_name"], "Alice")
        self.assertTrue(public["first_login"])
        self.assertNotIn("id", public)
        self.assertNotIn("password_hash", public)

    def test_maps_tinyint_zero_and_missing_to_false(self) -> None:
        completed = {**_FIRST_LOGIN_USER, "first_login": 0}
        self.assertFalse(to_public_user(completed)["first_login"])
        missing = {
            "uuid": _FIRST_LOGIN_USER["uuid"],
            "username": "alice",
            "display_name": None
        }
        self.assertFalse(to_public_user(missing)["first_login"])


class TestCompleteFirstLogin(unittest.TestCase):
    """First-login completion validates input and persists credentials."""

    def _completed_user(self, username: str = "alice") -> dict[str, object]:
        return {
            **_FIRST_LOGIN_USER,
            "username": username,
            "first_login": 0,
            "password_hash": "new-hash"
        }

    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_id")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=False)
    def test_happy_path_hashes_with_existing_pipeline_and_updates(
            self,
            mock_taken: MagicMock,
            mock_update: MagicMock,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._completed_user("alice")
        result = complete_first_login(
            _FIRST_LOGIN_USER,
            "  alice  ",
            "newpass1",
            "newpass1",
            "  Alice  ")
        mock_taken.assert_called_once_with("alice", 7)
        mock_update.assert_called_once()
        user_id, username, password_hash, display_name = (
            mock_update.call_args.args)
        self.assertEqual(user_id, 7)
        self.assertEqual(username, "alice")
        self.assertEqual(display_name, "Alice")
        self.assertTrue(verify_password("newpass1", password_hash))
        mock_fetch.assert_called_once_with(7)
        self.assertEqual(result, mock_fetch.return_value)

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_mismatch_passwords_does_not_write(
            self, mock_update: MagicMock) -> None:
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER,
                "alice",
                "newpass1",
                "otherpass",
                "Alice")
        self.assertEqual(str(ctx.exception), "Passwords do not match")
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_short_password_does_not_write(
            self, mock_update: MagicMock) -> None:
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER, "alice", "ab", "ab", "Alice")
        self.assertIn("between", str(ctx.exception))
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=True)
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_taken_username_does_not_write(
            self,
            mock_update: MagicMock,
            _mock_taken: MagicMock) -> None:
        with self.assertRaises(UsernameTakenError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER,
                "bob",
                "newpass1",
                "newpass1",
                "Bob")
        self.assertEqual(str(ctx.exception), "Username already taken")
        mock_update.assert_not_called()

    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_already_completed_does_not_write(
            self, mock_update: MagicMock) -> None:
        completed = {**_FIRST_LOGIN_USER, "first_login": 0}
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                completed, "alice", "newpass1", "newpass1", "Alice")
        self.assertEqual(str(ctx.exception), "First login already completed")
        mock_update.assert_not_called()

    @patch("backend.services.auth_service.hash_password", return_value="h")
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_id")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=False)
    def test_integrity_error_becomes_username_taken(
            self,
            _mock_taken: MagicMock,
            mock_update: MagicMock,
            mock_fetch: MagicMock,
            _mock_hash: MagicMock) -> None:
        mock_update.side_effect = IntegrityError(
            "Duplicate entry 'bob' for key 'username_UNIQUE'",
            1062)
        with self.assertRaises(UsernameTakenError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER,
                "bob",
                "newpass1",
                "newpass1",
                "Bob")
        self.assertEqual(str(ctx.exception), "Username already taken")
        mock_fetch.assert_not_called()

    @patch("backend.services.auth_service.hash_password", return_value="h")
    @patch(
        "backend.services.auth_service.user_repository.fetch_user_by_id")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    @patch(
        "backend.services.auth_service.user_repository.is_username_taken",
        return_value=False)
    def test_update_value_error_means_already_completed(
            self,
            _mock_taken: MagicMock,
            mock_update: MagicMock,
            mock_fetch: MagicMock,
            _mock_hash: MagicMock) -> None:
        mock_update.side_effect = ValueError(
            "First login already completed or user not found")
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER,
                "alice",
                "newpass1",
                "newpass1",
                "Alice")
        self.assertEqual(str(ctx.exception), "First login already completed")
        mock_fetch.assert_not_called()

    @patch(
        "backend.services.auth_service.hash_password")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_empty_username_does_not_write(
            self,
            mock_update: MagicMock,
            mock_hash: MagicMock) -> None:
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER, "   ", "newpass1", "newpass1", "Alice")
        self.assertIn("Username", str(ctx.exception))
        mock_update.assert_not_called()
        mock_hash.assert_not_called()

    @patch(
        "backend.services.auth_service.hash_password")
    @patch(
        "backend.services.auth_service.user_repository"
        ".update_user_credentials_after_first_login")
    def test_empty_display_name_does_not_write(
            self,
            mock_update: MagicMock,
            mock_hash: MagicMock) -> None:
        with self.assertRaises(AuthError) as ctx:
            complete_first_login(
                _FIRST_LOGIN_USER, "alice", "newpass1", "newpass1", "   ")
        self.assertIn("Display name", str(ctx.exception))
        mock_update.assert_not_called()
        mock_hash.assert_not_called()


if __name__ == "__main__":
    unittest.main()
