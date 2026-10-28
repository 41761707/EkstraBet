"""Stake advice from mocked reads and the repository SQL contract."""

from __future__ import annotations

import ast
import unittest
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import Error as MySQLError

from backend.database import DatabaseConnectionError
from backend.repositories import stake_advisor_repository as advisor_repo
from backend.services.stake_advisor_config import AdvisorWeights
from backend.services.stake_advisor_math import apply_caps
from backend.services.stake_advisor_math import blend_probability
from backend.services.stake_advisor_math import fractional_kelly
from backend.services.stake_advisor_math import joint_probability
from backend.services.stake_advisor_service import REASON_MODEL_NOT_READY
from backend.services.stake_advisor_service import REASON_NO_BET
from backend.services.stake_advisor_service import REASON_NO_PREDICTION
from backend.services.stake_advisor_service import REASON_OK
from backend.services.stake_advisor_service import advise
from backend.services.tipster_service import TipsterNotFoundError
from backend.services.tipster_service import TipsterUnprocessableError


_CFG = AdvisorWeights()
_FINGERPRINT = "a" * 64
_GET_CONN = (
    "backend.repositories.stake_advisor_repository.get_db_connection")
_VALIDATE = "backend.services.stake_advisor_service._validated_legs"
_BANKROLL = "backend.services.stake_advisor_service.get_my_bankroll"
_GATE = "backend.services.stake_advisor_service.current_fingerprint"
_PROBS = (
    "backend.services.stake_advisor_service."
    "fetch_published_probabilities")
_VERDICTS = "backend.services.stake_advisor_service.fetch_verdicts"
_LIKED = "backend.services.stake_advisor_service.agent_liked"
_USER = {"id": 1}


def _leg(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": 10,
        "event_ids": [3],
        "odds": 2.0,
        "bookmaker_id": 2,
        "source": "catalog"
    }
    row.update(overrides)
    return row


def _bankroll(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "currency": "PLN",
        "current_balance": 1000.0,
        "initial_capital": 1000.0,
        "unit_size": 10.0
    }
    row.update(overrides)
    return row


def _published(value: float, prediction_id: int = 8) -> dict[str, object]:
    return {"prediction_id": prediction_id, "value": value}


def _verdict(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "prediction_id": 8,
        "odds_id": 4,
        "decision": "bet",
        "calibrated_probability": 0.62,
        "match_id": 10,
        "event_id": 3,
        "bookmaker_id": 2,
        "odds": 2.0
    }
    row.update(overrides)
    return row


def _request(legs: list[dict[str, object]], confidence: int = 70) -> dict:
    return {"confidence": confidence, "legs": legs}


@contextmanager
def _patched(
        *,
        legs: list[dict[str, object]],
        bankroll: dict[str, object] | None = None,
        published: list[dict[str, object]] | None = None,
        published_effect: list[list[dict[str, object]]] | None = None,
        verdicts: list[dict[str, object]] | None = None,
        liked: bool = False,
        fingerprint: str | None = _FINGERPRINT
        ) -> Iterator[dict[str, MagicMock]]:
    """Patch every read advise performs."""
    mocks: dict[str, MagicMock] = {}
    with patch(_VALIDATE, return_value=legs) as validate, \
            patch(_BANKROLL, return_value=bankroll or _bankroll()) as money, \
            patch(_GATE, return_value=fingerprint) as gate, \
            patch(_LIKED, return_value=liked) as agent, \
            patch(_VERDICTS, return_value=verdicts or []) as scored:
        if published_effect is None:
            probs = patch(_PROBS, return_value=published or [])
        else:
            probs = patch(_PROBS, side_effect=published_effect)
        with probs as published_mock:
            mocks["validate"] = validate
            mocks["bankroll"] = money
            mocks["gate"] = gate
            mocks["agent"] = agent
            mocks["verdicts"] = scored
            mocks["published"] = published_mock
            yield mocks


def _money_stake(
        model_p: float | None,
        odds: float,
        confidence: int,
        bankroll: dict[str, object],
        liked: bool = False) -> float:
    """Stake the service should return for one leg."""
    implied = 1.0 / odds
    used = blend_probability(
        model_p, implied, confidence / 100.0, liked, _CFG)
    current = float(bankroll["current_balance"])
    initial = float(bankroll["initial_capital"])
    unit_size = float(bankroll["unit_size"])
    basis = max(current, initial, unit_size)
    share = fractional_kelly(used, odds, _CFG.kelly_fraction)
    stake, _limits = apply_caps(
        share * basis, max(current, initial), unit_size, _CFG)
    return stake


class TestAdviseStake(unittest.TestCase):
    """The service blends mocked inputs and does not write."""

    def test_catalog_leg_uses_published_percent(self) -> None:
        legs = [_leg()]
        bankroll = _bankroll()
        with _patched(
                legs=legs,
                bankroll=bankroll,
                published=[_published(55)]):
            payload = advise(_USER, _request(legs))
        advice = payload["advice"]
        leg = advice["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)
        self.assertEqual(leg["implied_probability"], 0.5)
        self.assertFalse(leg["agent_liked"])
        self.assertEqual(advice["reason"], REASON_OK)
        self.assertFalse(advice["no_bet"])
        self.assertEqual(
            advice["suggested_stake"],
            _money_stake(0.55, 2.0, 70, bankroll))
        self.assertEqual(payload["currency"], "PLN")

    def test_negative_balance_uses_initial_capital(self) -> None:
        legs = [_leg()]
        bankroll = _bankroll(current_balance=-80.0, initial_capital=1000.0)
        with _patched(
                legs=legs,
                bankroll=bankroll,
                published=[_published(55)]):
            advice = advise(_USER, _request(legs))["advice"]
        self.assertEqual(
            advice["suggested_stake"],
            _money_stake(0.55, 2.0, 70, bankroll))
        self.assertGreater(advice["suggested_stake"], 10.0)

    def test_calibrated_probability_stays_on_the_unit_scale(self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(40)],
                verdicts=[_verdict(calibrated_probability=0.62)]):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.62)
        self.assertNotAlmostEqual(leg["model_probability"], 0.0062)

    def test_no_bet_verdict_still_supplies_probability(self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(40)],
                verdicts=[_verdict(decision="no_bet")]):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.62)

    def test_custom_odds_ignore_the_verdict(self) -> None:
        legs = [_leg(source="custom_odds", bookmaker_id=None)]
        with _patched(
                legs=legs,
                published=[_published(55)],
                verdicts=[_verdict()]) as mocks:
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)
        mocks["verdicts"].assert_not_called()

    def test_other_bookmaker_keeps_the_published_percent(self) -> None:
        legs = [_leg(bookmaker_id=9)]
        with _patched(
                legs=legs,
                published=[_published(55)],
                verdicts=[_verdict(bookmaker_id=2)]):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)

    def test_same_bookmaker_with_another_price_keeps_the_percent(
            self) -> None:
        legs = [_leg(odds=2.0)]
        with _patched(
                legs=legs,
                published=[_published(55)],
                verdicts=[_verdict(odds=3.5, calibrated_probability=0.62)]):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)
        self.assertNotEqual(leg["model_probability"], 0.62)

    def test_verdict_outside_the_open_unit_interval_keeps_the_percent(
            self) -> None:
        legs = [_leg()]
        for calibrated in (0.0, 1.5):
            with _patched(
                    legs=legs,
                    published=[_published(55)],
                    verdicts=[_verdict(
                        calibrated_probability=calibrated)]):
                leg = advise(_USER, _request(legs))["advice"]["legs"][0]
            self.assertEqual(leg["model_probability"], 0.55)

    def test_read_errors_still_return_advice(self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(55)],
                verdicts=[_verdict()]) as mocks:
            mocks["published"].side_effect = MySQLError("predictions down")
            advice = advise(_USER, _request(legs))["advice"]
        self.assertIsNone(advice["legs"][0]["model_probability"])
        self.assertFalse(advice["legs"][0]["agent_liked"])
        self.assertIn("suggested_stake", advice)
        with _patched(
                legs=legs,
                published=[_published(55)],
                verdicts=[_verdict()]) as mocks:
            mocks["verdicts"].side_effect = DatabaseConnectionError(
                "verdicts down")
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)
        self.assertFalse(leg["agent_liked"])
        with _patched(
                legs=legs,
                published=[_published(55)],
                liked=True) as mocks:
            mocks["agent"].side_effect = OSError("agent down")
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.55)
        self.assertFalse(leg["agent_liked"])

    def test_published_endpoints_keep_the_model_weight(self) -> None:
        legs = [_leg()]
        for value, expected in ((0, 0.0), (100, 1.0)):
            with _patched(legs=legs, published=[_published(value)]):
                leg = advise(_USER, _request(legs))["advice"]["legs"][0]
            self.assertEqual(leg["model_probability"], expected)
            self.assertAlmostEqual(
                leg["p_used"],
                blend_probability(expected, 0.5, 0.70, False, _CFG))
        combined = [_leg(event_ids=[3, 4], odds=3.2)]
        effect = [[_published(100, 1)], [_published(50, 2)]]
        with _patched(legs=combined, published_effect=effect):
            leg = advise(_USER, _request(combined))["advice"]["legs"][0]
        self.assertAlmostEqual(leg["model_probability"], 0.5)

    def test_combined_leg_multiplies_published_percents(self) -> None:
        legs = [_leg(event_ids=[3, 4], odds=3.2)]
        effect = [[_published(50, 1)], [_published(80, 2)]]
        with _patched(
                legs=legs,
                published_effect=effect,
                verdicts=[_verdict(calibrated_probability=0.9)]) as mocks:
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertAlmostEqual(leg["model_probability"], 0.5 * 0.8)
        mocks["verdicts"].assert_not_called()

    def test_missing_artifact_keeps_predictions_and_reports_the_gate(
            self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(55)],
                fingerprint=None,
                verdicts=[_verdict()]) as mocks:
            advice = advise(_USER, _request(legs))["advice"]
        self.assertEqual(advice["legs"][0]["model_probability"], 0.55)
        self.assertEqual(advice["reason"], REASON_MODEL_NOT_READY)
        self.assertGreater(advice["suggested_stake"], 0.0)
        mocks["verdicts"].assert_not_called()

    def test_low_edge_beats_a_missing_artifact(self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(40)],
                fingerprint=None):
            advice = advise(_USER, _request(legs, confidence=0))["advice"]
        self.assertEqual(advice["reason"], REASON_NO_BET)
        self.assertTrue(advice["no_bet"])
        self.assertEqual(advice["suggested_stake"], 0.0)

    def test_no_published_prediction_still_prices_user_and_implied(
            self) -> None:
        legs = [_leg()]
        with _patched(legs=legs, published=[]):
            advice = advise(_USER, _request(legs))["advice"]
        self.assertIsNone(advice["legs"][0]["model_probability"])
        self.assertEqual(advice["reason"], REASON_NO_PREDICTION)
        self.assertEqual(
            advice["suggested_stake"],
            _money_stake(None, 2.0, 70, _bankroll()))

    def test_agent_like_raises_the_blend(self) -> None:
        legs = [_leg()]
        with _patched(
                legs=legs,
                published=[_published(55)],
                liked=True) as mocks:
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        plain = blend_probability(0.55, 0.5, 0.70, False, _CFG)
        liked = blend_probability(0.55, 0.5, 0.70, True, _CFG)
        self.assertTrue(leg["agent_liked"])
        self.assertAlmostEqual(leg["p_used"], liked)
        self.assertGreater(leg["p_used"], plain)
        mocks["agent"].assert_called_once_with(10, [3], 14)

    def test_two_models_average_a_matching_verdict_with_the_percent(
            self) -> None:
        legs = [_leg()]
        published = [_published(40, 1), _published(60, 2)]
        verdicts = [_verdict(prediction_id=1, calibrated_probability=0.62)]
        with _patched(legs=legs, published=published, verdicts=verdicts):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertAlmostEqual(leg["model_probability"], (0.62 + 0.60) / 2)

    def test_lowest_odds_id_wins_when_two_rows_match(self) -> None:
        legs = [_leg()]
        verdicts = [
            _verdict(odds_id=9, calibrated_probability=0.70),
            _verdict(odds_id=4, calibrated_probability=0.62)]
        with _patched(
                legs=legs,
                published=[_published(40)],
                verdicts=verdicts):
            leg = advise(_USER, _request(legs))["advice"]["legs"][0]
        self.assertEqual(leg["model_probability"], 0.62)

    def test_zero_legs_are_rejected_before_the_bankroll(self) -> None:
        with patch(_BANKROLL) as bankroll:
            with self.assertRaises(TipsterUnprocessableError):
                advise(_USER, _request([]))
        bankroll.assert_not_called()

    def test_confidence_above_100_is_rejected(self) -> None:
        with self.assertRaises(TipsterUnprocessableError):
            advise(_USER, _request([_leg()], confidence=101))

    def test_missing_bankroll_raises_not_found(self) -> None:
        with patch(_VALIDATE, return_value=[_leg()]), \
                patch(
                    _BANKROLL,
                    side_effect=TipsterNotFoundError(
                        "Bankroll not configured")):
            with self.assertRaises(TipsterNotFoundError):
                advise(_USER, _request([_leg()]))

    def test_accumulator_multiplies_leg_probabilities(self) -> None:
        legs = [_leg(match_id=10), _leg(match_id=11, event_ids=[5])]
        effect = [[_published(50)], [_published(80, 9)]]
        with _patched(legs=legs, published_effect=effect):
            advice = advise(_USER, _request(legs))["advice"]
        first = blend_probability(0.50, 0.5, 0.70, False, _CFG)
        second = blend_probability(0.80, 0.5, 0.70, False, _CFG)
        self.assertAlmostEqual(
            advice["p_blend"], joint_probability([first, second]))
        self.assertAlmostEqual(advice["combined_odds"], 4.0)


class TestStakeAdvisorRepository(unittest.TestCase):
    """SQL reads the coupon clock and does not filter decision = bet."""

    def test_empty_verdict_ids_do_not_open_a_connection(self) -> None:
        with patch(_GET_CONN) as connection:
            self.assertEqual(advisor_repo.fetch_verdicts([], _FINGERPRINT), [])
        connection.assert_not_called()

    def test_empty_event_ids_are_not_a_like(self) -> None:
        with patch(_GET_CONN) as connection:
            self.assertFalse(advisor_repo.agent_liked(10, []))
        connection.assert_not_called()

    @patch(_GET_CONN)
    def test_agent_query_keeps_open_coupons_and_the_created_at_window(
            self, mock_get_conn: MagicMock) -> None:
        _connection, cursor = _mock_connection(mock_get_conn, row={"1": 1})
        now = datetime(2026, 10, 28, 12, 0)
        self.assertTrue(advisor_repo.agent_liked(10, [3, 4], now=now))
        query, params = cursor.execute.call_args.args
        normalized = " ".join(query.split())
        self.assertIn("tipster_coupons c", normalized)
        self.assertIn("u.is_system = 1", normalized)
        self.assertIn("c.settled = 0 OR c.created_at >= %s", normalized)
        self.assertNotIn("tipster_coupon_legs l.created_at", normalized)
        self.assertEqual(params[0], 10)
        self.assertEqual(params[1], 3)
        self.assertEqual(params[2], 4)
        self.assertEqual(params[3], now - timedelta(days=14))
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_verdicts_keep_unit_probability_and_any_decision(
            self, mock_get_conn: MagicMock) -> None:
        row = {
            "prediction_id": 8,
            "odds_id": 4,
            "decision": "no_bet",
            "calibrated_probability": 0.62,
            "match_id": 10,
            "event_id": 3,
            "bookmaker_id": 2,
            "odds": 2.0
        }
        _connection, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[row]])
        found = advisor_repo.fetch_verdicts([8], _FINGERPRINT)
        query = " ".join(cursor.execute.call_args.args[0].split())
        self.assertEqual(found, [row])
        self.assertNotIn("decision =", query)
        self.assertIn("betting_recommendations br", query)
        self.assertIn("br.model_fingerprint = %s", query)

    @patch(_GET_CONN)
    def test_published_rows_come_from_final_predictions(
            self, mock_get_conn: MagicMock) -> None:
        row = {"prediction_id": 8, "value": 55}
        _connection, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[row]])
        found = advisor_repo.fetch_published_probabilities(10, 3)
        query = " ".join(cursor.execute.call_args.args[0].split())
        self.assertEqual(found, [row])
        self.assertIn("final_predictions fp", query)
        self.assertIn("p.id = fp.predictions_id", query)


class TestAdvisorModulesStayReadOnly(unittest.TestCase):
    """Advice must not place a coupon or load the meta-model file."""

    def test_sources_do_not_insert_or_open_the_model_file(self) -> None:
        root = Path(advisor_repo.__file__).resolve().parent
        service = root.parent / "services" / "stake_advisor_service.py"
        for path in (Path(advisor_repo.__file__), service):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("model.joblib", text)
            self.assertNotIn("create_coupon", text)
            self.assertNotIn("INSERT", text)
            tree = ast.parse(text)
            imported = _imported_modules(tree)
            self.assertNotIn("predictor", " ".join(imported))


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        row: dict[str, object] | None = None,
        fetchall_results: list[list[dict[str, object]]] | None = None
        ) -> tuple[MagicMock, MagicMock]:
    """Wire get_db_connection to one dictionary cursor."""
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    if fetchall_results is None:
        cursor.fetchall.return_value = []
    else:
        cursor.fetchall.side_effect = fetchall_results
    connection = MagicMock()
    connection.cursor.return_value = cursor
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    mock_get_conn.return_value = context
    return connection, cursor


def _imported_modules(tree: ast.AST) -> list[str]:
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


if __name__ == "__main__":
    unittest.main()
