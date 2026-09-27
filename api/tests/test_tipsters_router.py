"""API tests for tipster bankroll, coupon and ranking endpoints."""

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
from backend.services.tipster_service import TipsterConflictError
from backend.services.tipster_service import TipsterForbiddenError
from backend.services.tipster_service import TipsterNotFoundError
from backend.services.tipster_service import TipsterUnprocessableError
from backend.services.tipster_service import TipsterValidationError

get_settings.cache_clear()

from api.main import create_app  # noqa: E402


_SERVICE = "api.routers.tipsters.tipster_service"
_SETTLE = (
    "api.routers.tipsters.tipster_settlement_service.settle_open_coupons")
_FETCH_UUID = (
    "backend.services.auth_service.user_repository.fetch_user_by_uuid")

_USER_UUID = "11111111-2222-3333-4444-555555555555"
_ADMIN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_SYSTEM_UUID = "99999999-9999-9999-9999-999999999999"

_TEST_USER = {
    "id": 7,
    "uuid": _USER_UUID,
    "username": "alice",
    "password_hash": auth_service.hash_password("secret123"),
    "display_name": "Alice",
    "is_active": 1,
    "is_admin": 0,
    "is_system": 0,
    "first_login": 0,
    "created_at": None,
    "updated_at": None}

_ADMIN_USER = {
    **_TEST_USER,
    "id": 1,
    "uuid": _ADMIN_UUID,
    "username": "admin",
    "is_admin": 1}

_SYSTEM_USER = {
    **_TEST_USER,
    "id": 9,
    "uuid": _SYSTEM_UUID,
    "username": "agent",
    "is_system": 1}

_BANKROLL = {
    "user_id": 7,
    "currency": "PLN",
    "initial_capital": 100.0,
    "unit_size": 5.0,
    "current_balance": 50.0,
    "open_stake": 10.0,
    "realized_pnl": -50.0}

_OTHER_FAMILY_BUCKET = {
    "event_family_id": None,
    "event_family_name": "OTHER",
    "count": 2,
    "won": 1,
    "accuracy": 50.0,
    "stake_total": 20.0,
    "profit_total": -5.0,
    "avg_profit": -2.5,
    "avg_odds": 1.9,
    "roi_pct": -25.0}

_PERFORMANCE = {
    "by_event_family": [_OTHER_FAMILY_BUCKET],
    "by_league": [],
    "by_country": [],
    "best_event_family": _OTHER_FAMILY_BUCKET,
    "worst_event_family": _OTHER_FAMILY_BUCKET,
    "best_league": None,
    "worst_league": None,
    "best_country": None,
    "worst_country": None}

_COUPON = {
    "id": 15,
    "user_id": 7,
    "stake_amount": 10.0,
    "stake_units": 2.0,
    "stake_input_mode": "units",
    "combined_odds": 1.85,
    "settled": 0,
    "outcome": None,
    "profit": None,
    "created_at": datetime(2026, 9, 20, 12, 0, 0),
    "legs": [{
        "id": 21,
        "match_id": 100,
        "event_ids": [1],
        "odds": 1.85,
        "bookmaker_id": 4,
        "source": "catalog",
        "outcome": None}]}

_CREATE_COUPON_BODY = {
    "stake_input_mode": "units",
    "stake_units": 2.0,
    "legs": [{
        "match_id": 100,
        "event_ids": [1],
        "odds": 1.85,
        "source": "catalog",
        "bookmaker_id": 4}]}


class TipstersRouterTestCase(unittest.TestCase):
    """Authenticated TestClient shared by tipster contract cases."""

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


class TestTipstersMeAuth(TipstersRouterTestCase):
    """/me requires a user; AUTH_ENABLED=false hides the resource."""

    def test_me_endpoints_require_token(self) -> None:
        get_bankroll = self.client.get("/tipsters/me/bankroll")
        get_coupons = self.client.get("/tipsters/me/coupons")
        post_coupon = self.client.post(
            "/tipsters/me/coupons",
            json=_CREATE_COUPON_BODY)
        self.assertEqual(get_bankroll.status_code, 401)
        self.assertEqual(get_coupons.status_code, 401)
        self.assertEqual(post_coupon.status_code, 401)

    @patch(f"{_SERVICE}.get_my_bankroll")
    def test_auth_disabled_hides_me_endpoints(
            self,
            mock_get_bankroll: MagicMock) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        get_settings.cache_clear()
        client = TestClient(create_app())
        response = client.get("/tipsters/me/bankroll")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Authentication is disabled")
        mock_get_bankroll.assert_not_called()


class TestTipstersBankrollRouter(TipstersRouterTestCase):
    """GET/PUT bankroll and top-up HTTP mapping."""

    @patch(
        f"{_SERVICE}.get_my_bankroll",
        side_effect=TipsterNotFoundError("Bankroll not configured"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_missing_bankroll_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/me/bankroll",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Bankroll not configured")
        mock_get.assert_called_once()

    @patch(f"{_SERVICE}.get_my_bankroll", return_value=_BANKROLL)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_get_bankroll_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/me/bankroll",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["currency"], "PLN")
        self.assertEqual(payload["unit_size"], 5.0)
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.args[0]["id"], 7)

    @patch(
        f"{_SERVICE}.configure_bankroll",
        side_effect=TipsterForbiddenError(
            "System accounts cannot use /me mutations"))
    @patch(_FETCH_UUID, return_value=_SYSTEM_USER)
    def test_system_user_put_bankroll_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_put: MagicMock) -> None:
        self.user = _SYSTEM_USER
        response = self.client.put(
            "/tipsters/me/bankroll",
            headers=self._auth_headers(),
            json={
                "currency": "PLN",
                "initial_capital": 1000,
                "unit_size": 10})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "System accounts cannot use /me mutations")
        mock_put.assert_called_once()

    @patch(
        f"{_SERVICE}.top_up",
        side_effect=TipsterForbiddenError(
            "System accounts cannot use /me mutations"))
    @patch(_FETCH_UUID, return_value=_SYSTEM_USER)
    def test_system_user_top_up_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_top_up: MagicMock) -> None:
        self.user = _SYSTEM_USER
        response = self.client.post(
            "/tipsters/me/top-up",
            headers=self._auth_headers(),
            json={"amount": 100})
        self.assertEqual(response.status_code, 403)
        mock_top_up.assert_called_once()

    @patch(
        f"{_SERVICE}.configure_bankroll",
        side_effect=TipsterConflictError(
            "Initial capital cannot be changed after onboarding"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_put_capital_after_onboarding_returns_409(
            self,
            _mock_fetch: MagicMock,
            mock_put: MagicMock) -> None:
        response = self.client.put(
            "/tipsters/me/bankroll",
            headers=self._auth_headers(),
            json={
                "currency": "PLN",
                "initial_capital": 200,
                "unit_size": 5})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Initial capital cannot be changed after onboarding")
        mock_put.assert_called_once()


class TestTipstersCouponsRouter(TipstersRouterTestCase):
    """Coupon create and list contracts."""

    @patch(f"{_SERVICE}.create_coupon", return_value=_COUPON)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_create_coupon_returns_201(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        response = self.client.post(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            json=_CREATE_COUPON_BODY)
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["id"], 15)
        self.assertEqual(payload["combined_odds"], 1.85)
        self.assertEqual(len(payload["legs"]), 1)
        mock_create.assert_called_once()
        passed_user, request = mock_create.call_args.args
        self.assertEqual(passed_user["id"], 7)
        self.assertEqual(request["stake_input_mode"], "units")
        self.assertEqual(request["legs"][0]["event_ids"], [1])

    @patch(
        f"{_SERVICE}.create_coupon",
        side_effect=TipsterForbiddenError(
            "System accounts cannot use /me mutations"))
    @patch(_FETCH_UUID, return_value=_SYSTEM_USER)
    def test_system_user_create_coupon_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        self.user = _SYSTEM_USER
        response = self.client.post(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            json=_CREATE_COUPON_BODY)
        self.assertEqual(response.status_code, 403)
        mock_create.assert_called_once()

    @patch(
        f"{_SERVICE}.create_coupon",
        side_effect=TipsterValidationError("Bankroll not configured"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_create_coupon_without_bankroll_returns_400(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        response = self.client.post(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            json=_CREATE_COUPON_BODY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Bankroll not configured")
        mock_create.assert_called_once()

    @patch(f"{_SERVICE}.create_coupon")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_nine_legs_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        body = {
            **_CREATE_COUPON_BODY,
            "legs": [
                {**_CREATE_COUPON_BODY["legs"][0], "match_id": 100 + index}
                for index in range(9)]}
        response = self.client.post(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            json=body)
        self.assertEqual(response.status_code, 422)
        mock_create.assert_not_called()

    @patch(
        f"{_SERVICE}.create_coupon",
        side_effect=TipsterUnprocessableError("Duplicate match on coupon"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_unprocessable_coupon_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_create: MagicMock) -> None:
        response = self.client.post(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            json=_CREATE_COUPON_BODY)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Duplicate match on coupon")
        mock_create.assert_called_once()

    @patch(f"{_SERVICE}.get_my_coupons", return_value={
        "items": [_COUPON],
        "total": 1,
        "page": 1,
        "page_size": 20})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_list_coupons_returns_pager(
            self,
            _mock_fetch: MagicMock,
            mock_list: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/me/coupons",
            headers=self._auth_headers(),
            params={"settled": 0})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 20)
        mock_list.assert_called_once()
        _user, settled, page, page_size = mock_list.call_args.args
        self.assertEqual(settled, 0)
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 20)
        self.assertFalse(mock_list.call_args.kwargs["apply_tax"])


class TestTipstersPerformanceRouter(TipstersRouterTestCase):
    """GET /me/performance exposes dimension labels including OTHER."""

    @patch(f"{_SERVICE}.get_my_performance", return_value=_PERFORMANCE)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_performance_exposes_other_family_label(
            self,
            _mock_fetch: MagicMock,
            mock_perf: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/me/performance",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        bucket = payload["by_event_family"][0]
        self.assertIsNone(bucket["event_family_id"])
        self.assertEqual(bucket["event_family_name"], "OTHER")
        self.assertIsNone(bucket["league_id"])
        self.assertEqual(
            payload["best_event_family"]["event_family_name"],
            "OTHER")
        mock_perf.assert_called_once()
        self.assertEqual(mock_perf.call_args.args[0]["id"], 7)


class TestTipstersPublicRouter(TipstersRouterTestCase):
    """Leaderboard, profile and catalog require auth when enabled."""

    def test_public_endpoints_require_token(self) -> None:
        leaderboard = self.client.get("/tipsters/leaderboard")
        profile = self.client.get("/tipsters/profile/alice")
        catalog = self.client.get("/tipsters/catalog/matches")
        suggested = self.client.get(
            "/tipsters/catalog/suggested-odds",
            params={"match_id": 124426, "event_id": 1})
        self.assertEqual(leaderboard.status_code, 401)
        self.assertEqual(profile.status_code, 401)
        self.assertEqual(catalog.status_code, 401)
        self.assertEqual(suggested.status_code, 401)

    @patch(f"{_SERVICE}.get_leaderboard", return_value={
        "items": [{
            "user_id": 7,
            "username": "alice",
            "display_name": "Alice",
            "is_system": 0,
            "currency": "PLN",
            "bets_count": 0,
            "won_count": 0,
            "accuracy_pct": None,
            "stake_total": 0.0,
            "profit_total": 0.0,
            "avg_profit": None,
            "avg_odds": None,
            "roi_pct": None,
            "current_balance": 100.0}],
        "total": 1})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_leaderboard_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_board: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/leaderboard",
            headers=self._auth_headers(),
            params={"is_system": 0, "event_family": "OTHER"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertFalse(payload["items"][0]["is_system"])
        self.assertEqual(payload["items"][0]["currency"], "PLN")
        self.assertNotIn("coupons", payload["items"][0])
        filters = mock_board.call_args.args[0]
        self.assertEqual(filters["is_system"], 0)
        self.assertEqual(filters["event_family"], "OTHER")
        self.assertIsNone(filters["event_ids"])
        self.assertFalse(filters["apply_tax"])

    @patch(f"{_SERVICE}.get_leaderboard", return_value={
        "items": [],
        "total": 0})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_apply_tax_is_forwarded(
            self,
            _mock_fetch: MagicMock,
            mock_board: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/leaderboard",
            headers=self._auth_headers(),
            params={"apply_tax": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_board.call_args.args[0]["apply_tax"])

    @patch(f"{_SERVICE}.get_leaderboard", return_value={
        "items": [],
        "total": 0})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_event_ids_are_forwarded(
            self,
            _mock_fetch: MagicMock,
            mock_board: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/leaderboard",
            headers=self._auth_headers(),
            params={"event_ids": "6,12"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_board.call_args.args[0]["event_ids"], [6, 12])

    @patch(f"{_SERVICE}.get_public_profile", return_value={
        "user_id": 8,
        "username": "bob",
        "display_name": "Bob",
        "is_system": 0,
        "bankroll": {"currency": "PLN", "current_balance": 50.0},
        "coupons": None,
        "performance": None})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_stranger_profile_hides_coupons(
            self,
            _mock_fetch: MagicMock,
            mock_profile: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/profile/bob",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["coupons"])
        self.assertEqual(
            payload["bankroll"],
            {"currency": "PLN", "current_balance": 50.0})
        self.assertNotIn("unit_size", payload["bankroll"])
        mock_profile.assert_called_once()
        username, viewer, page, page_size = mock_profile.call_args.args
        self.assertEqual(username, "bob")
        self.assertEqual(viewer["id"], 7)
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 20)

    @patch(
        f"{_SERVICE}.get_public_profile",
        side_effect=TipsterNotFoundError("User not found"))
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_missing_profile_returns_404(
            self,
            _mock_fetch: MagicMock,
            mock_profile: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/profile/nobody",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "User not found")
        mock_profile.assert_called_once()

    @patch(f"{_SERVICE}.get_catalog_matches", return_value={
        "matches": [],
        "events": [{"id": 1, "name": "Zwycięstwo gospodarza"}]})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_catalog_returns_separate_lists(
            self,
            _mock_fetch: MagicMock,
            mock_catalog: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/catalog/matches",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matches"], [])
        self.assertEqual(payload["events"][0]["id"], 1)
        mock_catalog.assert_called_once_with(None, None, None)

    @patch(
        f"{_SERVICE}.get_suggested_catalog_odds",
        return_value={"odds": 2.2})
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_suggested_odds_returns_stored_price(
            self,
            _mock_fetch: MagicMock,
            mock_suggest: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/catalog/suggested-odds",
            headers=self._auth_headers(),
            params={"match_id": 124426, "event_id": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"odds": 2.2})
        mock_suggest.assert_called_once_with(124426, 1)

    @patch(f"{_SERVICE}.get_leaderboard")
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_invalid_event_family_returns_422(
            self,
            _mock_fetch: MagicMock,
            mock_board: MagicMock) -> None:
        response = self.client.get(
            "/tipsters/leaderboard",
            headers=self._auth_headers(),
            params={"event_family": "abc"})
        self.assertEqual(response.status_code, 422)
        mock_board.assert_not_called()


class TestTipstersSettleRouter(TipstersRouterTestCase):
    """Settlement is admin-only."""

    def test_settle_without_token_returns_401(self) -> None:
        response = self.client.post("/tipsters/parlays/settle")
        self.assertEqual(response.status_code, 401)

    @patch(_SETTLE)
    @patch(_FETCH_UUID, return_value=_TEST_USER)
    def test_settle_without_admin_returns_403(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        response = self.client.post(
            "/tipsters/parlays/settle",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Administrator role required")
        mock_settle.assert_not_called()

    @patch(_SETTLE, return_value={
        "legs_settled": 2,
        "coupons_settled": 1,
        "legs_skipped": 0})
    @patch(_FETCH_UUID, return_value=_ADMIN_USER)
    def test_admin_settle_returns_200(
            self,
            _mock_fetch: MagicMock,
            mock_settle: MagicMock) -> None:
        self.user = _ADMIN_USER
        response = self.client.post(
            "/tipsters/parlays/settle",
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["coupons_settled"], 1)
        mock_settle.assert_called_once_with()


class TestTipstersOpenApi(unittest.TestCase):
    """OpenAPI describes the /tipsters module when docs are enabled."""

    def setUp(self) -> None:
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["OPENAPI_ENABLED"] = "true"
        get_settings.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ["OPENAPI_ENABLED"] = "false"
        get_settings.cache_clear()

    def test_openapi_lists_tipsters_paths(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        expected = [
            "/tipsters/me/bankroll",
            "/tipsters/me/top-up",
            "/tipsters/me/coupons",
            "/tipsters/me/performance",
            "/tipsters/leaderboard",
            "/tipsters/profile/{username}",
            "/tipsters/catalog/matches",
            "/tipsters/catalog/suggested-odds",
            "/tipsters/parlays/settle"]
        for path in expected:
            with self.subTest(path=path):
                self.assertIn(path, paths)
        taxed = [
            "/tipsters/me/bankroll",
            "/tipsters/me/coupons",
            "/tipsters/me/performance",
            "/tipsters/leaderboard",
            "/tipsters/profile/{username}"]
        for path in taxed:
            names = [
                item["name"]
                for item in paths[path]["get"]["parameters"]]
            with self.subTest(path=path):
                self.assertIn("apply_tax", names)


if __name__ == "__main__":
    unittest.main()
