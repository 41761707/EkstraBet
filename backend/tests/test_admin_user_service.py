"""Unit tests for administrative user domain rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID

from mysql.connector.errors import IntegrityError

from backend.services import admin_user_service as service
from backend.services.admin_errors import AdminConflictError
from backend.services.admin_errors import AdminForbiddenError
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError


_ACTOR_UUID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_TARGET_UUID = "11111111-1111-1111-1111-111111111111"
_TEMP_PASSWORD = "secret1"
_ACTOR = {
    "id": 1,
    "uuid": _ACTOR_UUID,
    "username": "admin",
    "is_admin": 1}

_REPO_USER_ROW = {
    "id": 8,
    "uuid": _TARGET_UUID,
    "username": "alice",
    "password_hash": "should-not-leak",
    "display_name": "Alice",
    "is_active": 1,
    "is_admin": 0,
    "first_login": 1,
    "created_at": None,
    "updated_at": None}

_FETCH_ALL = (
    "backend.services.admin_user_service.user_repository.fetch_all_users")
_CREATE = (
    "backend.services.admin_user_service.user_repository.create_user")
_SET_ACTIVE = (
    "backend.services.admin_user_service.user_repository.set_user_active")
_SET_ADMIN = (
    "backend.services.admin_user_service.user_repository.set_user_admin")
_USERNAME_TAKEN = (
    "backend.services.admin_user_service.user_repository.is_username_taken")
_HASH = "backend.services.admin_user_service.auth_service.hash_password"
_UUID4 = "backend.services.admin_user_service.uuid.uuid4"

_MISSING_UUID = "99999999-9999-9999-9999-999999999999"


def _dto_keys() -> set[str]:
    return {"uuid",
        "username",
        "display_name",
        "is_active",
        "is_admin",
        "first_login",
        "created_at",
        "updated_at"}


class TestListUsers(unittest.TestCase):
    """List maps TINYINT flags and never exposes id or password hash."""

    @patch(_FETCH_ALL, return_value=[_REPO_USER_ROW])
    def test_maps_tinyint_and_omits_secrets(
            self,
            mock_fetch: MagicMock) -> None:
        users = service.list_users()
        self.assertEqual(len(users), 1)
        user = users[0]
        self.assertEqual(set(user), _dto_keys())
        self.assertEqual(user["uuid"], _TARGET_UUID)
        self.assertEqual(user["username"], "alice")
        self.assertEqual(user["display_name"], "Alice")
        self.assertTrue(user["is_active"])
        self.assertFalse(user["is_admin"])
        self.assertTrue(user["first_login"])
        self.assertNotIn("id", user)
        self.assertNotIn("password_hash", user)
        mock_fetch.assert_called_once_with()

    @patch(_FETCH_ALL, return_value=[])
    def test_empty_list(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(service.list_users(), [])
        mock_fetch.assert_called_once_with()

    @patch(
        _FETCH_ALL,
        return_value=[{
            "uuid": _TARGET_UUID,
            "username": "bob",
            "display_name": None,
            "is_active": 0,
            "is_admin": 1,
            "first_login": 0,
            "created_at": None,
            "updated_at": None}])
    def test_maps_zero_flags_and_admin_true(
            self,
            _mock_fetch: MagicMock) -> None:
        user = service.list_users()[0]
        self.assertFalse(user["is_active"])
        self.assertTrue(user["is_admin"])
        self.assertFalse(user["first_login"])
        self.assertIsNone(user["display_name"])


class TestCreateUser(unittest.TestCase):
    """Create hashes the admin-supplied password and forces first_login."""

    def _created_row(self) -> dict[str, object]:
        return dict(_REPO_USER_ROW)

    @patch(_CREATE)
    @patch(_USERNAME_TAKEN, return_value=False)
    @patch(_HASH, return_value="hashed-secret")
    @patch(_UUID4)
    def test_happy_path_hashes_supplied_password_and_first_login(
            self,
            mock_uuid4: MagicMock,
            mock_hash: MagicMock,
            mock_taken: MagicMock,
            mock_create: MagicMock) -> None:
        mock_uuid4.return_value = UUID(_TARGET_UUID)
        mock_create.return_value = self._created_row()
        created = service.create_user(
            "  alice  ",
            _TEMP_PASSWORD,
            "  Alice  ",
            is_admin=False)
        mock_taken.assert_called_once_with("alice", 0)
        mock_hash.assert_called_once_with(_TEMP_PASSWORD)
        mock_create.assert_called_once_with(
            _TARGET_UUID,
            "alice",
            "hashed-secret",
            "Alice",
            is_admin=False,
            is_active=True,
            first_login=True)
        self.assertTrue(created["first_login"])
        self.assertTrue(created["is_active"])
        self.assertEqual(created["uuid"], _TARGET_UUID)
        self.assertNotIn("password_hash", created)
        self.assertNotIn("id", created)
        self.assertNotIn(_TEMP_PASSWORD, str(created))
        self.assertNotIn("hashed-secret", str(created))

    @patch(_CREATE)
    @patch(_USERNAME_TAKEN, return_value=False)
    @patch(_HASH, return_value="hashed-secret")
    @patch(_UUID4)
    def test_blank_display_name_is_stored_as_none(
            self,
            mock_uuid4: MagicMock,
            _mock_hash: MagicMock,
            _mock_taken: MagicMock,
            mock_create: MagicMock) -> None:
        mock_uuid4.return_value = UUID(_TARGET_UUID)
        mock_create.return_value = self._created_row()
        service.create_user(
            "alice", _TEMP_PASSWORD, "   ", is_admin=True)
        self.assertEqual(
            mock_create.call_args.kwargs["is_admin"], True)
        self.assertEqual(mock_create.call_args.args[3], None)

    @patch(_CREATE)
    @patch(_USERNAME_TAKEN, return_value=True)
    @patch(_HASH)
    def test_duplicate_username_does_not_write(
            self,
            mock_hash: MagicMock,
            mock_taken: MagicMock,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminConflictError) as ctx:
            service.create_user("alice", _TEMP_PASSWORD, "Alice")
        self.assertEqual(str(ctx.exception), "Username already taken")
        mock_taken.assert_called_once_with("alice", 0)
        mock_hash.assert_not_called()
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_USERNAME_TAKEN, return_value=False)
    @patch(_HASH, return_value="hashed-secret")
    @patch(_UUID4)
    def test_integrity_error_becomes_username_taken(
            self,
            mock_uuid4: MagicMock,
            _mock_hash: MagicMock,
            _mock_taken: MagicMock,
            mock_create: MagicMock) -> None:
        mock_uuid4.return_value = UUID(_TARGET_UUID)
        mock_create.side_effect = IntegrityError(
            "Duplicate entry 'alice' for key 'username_UNIQUE'",
            1062)
        with self.assertRaises(AdminConflictError) as ctx:
            service.create_user("alice", _TEMP_PASSWORD, "Alice")
        self.assertEqual(str(ctx.exception), "Username already taken")

    @patch(_CREATE)
    @patch(_USERNAME_TAKEN, return_value=False)
    @patch(_HASH, return_value="hashed-secret")
    @patch(_UUID4)
    def test_uuid_unique_integrity_error_is_generic_conflict(
            self,
            mock_uuid4: MagicMock,
            _mock_hash: MagicMock,
            _mock_taken: MagicMock,
            mock_create: MagicMock) -> None:
        mock_uuid4.return_value = UUID(_TARGET_UUID)
        mock_create.side_effect = IntegrityError(
            "Duplicate entry for key 'uuid_UNIQUE'",
            1062)
        with self.assertRaises(AdminConflictError) as ctx:
            service.create_user("alice", _TEMP_PASSWORD, "Alice")
        self.assertEqual(str(ctx.exception), "User already exists")

    @patch(_CREATE)
    @patch(_HASH)
    def test_empty_username_does_not_write(
            self,
            mock_hash: MagicMock,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_user("   ", _TEMP_PASSWORD, "Alice")
        self.assertIn("Username", str(ctx.exception))
        mock_hash.assert_not_called()
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_HASH)
    def test_short_password_does_not_write(
            self,
            mock_hash: MagicMock,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_user("alice", "ab", "Alice")
        self.assertIn("Password", str(ctx.exception))
        mock_hash.assert_not_called()
        mock_create.assert_not_called()

    @patch(_CREATE)
    @patch(_HASH)
    def test_display_name_too_long_does_not_write(
            self,
            mock_hash: MagicMock,
            mock_create: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.create_user("alice", _TEMP_PASSWORD, "A" * 51)
        self.assertIn("Display name", str(ctx.exception))
        mock_hash.assert_not_called()
        mock_create.assert_not_called()


class TestSetUserActive(unittest.TestCase):
    """Toggle is_active maps the row and protects the actor."""

    @patch(_SET_ACTIVE, return_value=_REPO_USER_ROW)
    def test_happy_path_maps_dto(
            self,
            mock_set: MagicMock) -> None:
        updated = service.set_user_active(_ACTOR, _TARGET_UUID, False)
        mock_set.assert_called_once_with(_TARGET_UUID, False)
        self.assertFalse(updated["is_admin"])
        self.assertNotIn("password_hash", updated)
        self.assertNotIn("id", updated)

    @patch(_SET_ACTIVE, return_value=None)
    def test_missing_user_raises_not_found(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminNotFoundError) as ctx:
            service.set_user_active(_ACTOR, _MISSING_UUID, False)
        self.assertEqual(str(ctx.exception), "User not found")
        mock_set.assert_called_once_with(_MISSING_UUID, False)

    @patch(_SET_ACTIVE)
    def test_self_deactivation_is_forbidden(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminForbiddenError) as ctx:
            service.set_user_active(_ACTOR, _ACTOR_UUID, False)
        self.assertEqual(
            str(ctx.exception),
            "Cannot deactivate your own account")
        mock_set.assert_not_called()

    @patch(_SET_ACTIVE)
    def test_uppercase_self_uuid_is_forbidden(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminForbiddenError) as ctx:
            service.set_user_active(_ACTOR, _ACTOR_UUID.upper(), False)
        self.assertEqual(
            str(ctx.exception),
            "Cannot deactivate your own account")
        mock_set.assert_not_called()

    @patch(_SET_ACTIVE)
    def test_malformed_uuid_is_validation_error(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminValidationError) as ctx:
            service.set_user_active(_ACTOR, "missing-uuid", False)
        self.assertEqual(str(ctx.exception), "Invalid user uuid")
        mock_set.assert_not_called()

    @patch(_SET_ACTIVE, return_value=_REPO_USER_ROW)
    def test_uppercase_other_user_uuid_is_canonicalized(
            self,
            mock_set: MagicMock) -> None:
        service.set_user_active(_ACTOR, _TARGET_UUID.upper(), False)
        mock_set.assert_called_once_with(_TARGET_UUID, False)

    @patch(_SET_ACTIVE, return_value=_REPO_USER_ROW)
    def test_self_activation_is_allowed(
            self,
            mock_set: MagicMock) -> None:
        service.set_user_active(_ACTOR, _ACTOR_UUID, True)
        mock_set.assert_called_once_with(_ACTOR_UUID, True)


class TestSetUserAdmin(unittest.TestCase):
    """Toggle is_admin maps the row and protects the actor."""

    @patch(_SET_ADMIN, return_value=_REPO_USER_ROW)
    def test_happy_path_maps_dto(
            self,
            mock_set: MagicMock) -> None:
        updated = service.set_user_admin(_ACTOR, _TARGET_UUID, True)
        mock_set.assert_called_once_with(_TARGET_UUID, True)
        self.assertEqual(updated["uuid"], _TARGET_UUID)
        self.assertNotIn("password_hash", updated)

    @patch(_SET_ADMIN, return_value=None)
    def test_missing_user_raises_not_found(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminNotFoundError) as ctx:
            service.set_user_admin(_ACTOR, _MISSING_UUID, True)
        self.assertEqual(str(ctx.exception), "User not found")
        mock_set.assert_called_once_with(_MISSING_UUID, True)

    @patch(_SET_ADMIN)
    def test_self_revocation_is_forbidden(
            self,
            mock_set: MagicMock) -> None:
        with self.assertRaises(AdminForbiddenError) as ctx:
            service.set_user_admin(_ACTOR, _ACTOR_UUID, False)
        self.assertEqual(
            str(ctx.exception),
            "Cannot revoke your own admin role")
        mock_set.assert_not_called()

    @patch(_SET_ADMIN, return_value=_REPO_USER_ROW)
    def test_granting_self_admin_is_allowed(
            self,
            mock_set: MagicMock) -> None:
        service.set_user_admin(_ACTOR, _ACTOR_UUID, True)
        mock_set.assert_called_once_with(_ACTOR_UUID, True)


if __name__ == "__main__":
    unittest.main()
