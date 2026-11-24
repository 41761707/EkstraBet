"""Tests for market consensus, information and flat-stake ROI."""

from __future__ import annotations

import json
import warnings
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from backend.betting_tax import BETTING_TAX_RATE
from backend.config import REPO_ROOT
from models.pipeline.core.model_lineup import DEFAULT_REGISTRY_PATH
from models.pipeline.data.evaluation_repository import fetch_match_odds
from models.pipeline.evaluation.market import consensus_fair_probabilities
from models.pipeline.evaluation.market import flat_stake_roi
from models.pipeline.evaluation.market import market_event_families
from models.pipeline.evaluation.market import market_information_test
from models.pipeline.evaluation.metrics import binary_log_loss


_REPOSITORY = "models.pipeline.data.evaluation_repository"
_FAMILY_KEYS = (
    "result_home",
    "result_draw",
    "result_away",
    "btts_yes",
    "btts_no",
    "over_25",
    "under_25")
_CONSENSUS_COLUMNS = ["match_id", "event_id", "fair_p", "best_odds"]
_ODDS_COLUMNS = ["match_id", "bookmaker_id", "event_id", "odds"]
_LOGISTIC_MAX_ITER = 1000


def test_market_families_come_from_config_events() -> None:
    configured = _configured_event_ids()
    assert market_event_families() == (
        (
            configured["result_home"],
            configured["result_draw"],
            configured["result_away"]),
        (configured["btts_yes"], configured["btts_no"]),
        (configured["over_25"], configured["under_25"]))


def test_consensus_uses_complete_markets_and_keeps_best_odds() -> None:
    home, draw, away = market_event_families()[0]
    first = _devig([2.0, 3.0, 6.0])
    second = _devig([4.0, 4.0, 2.0])
    expected = [(left + right) / 2.0 for left, right in zip(first, second)]
    frame = pd.DataFrame(
        _board(1, 1, (home, draw, away), [2.0, 3.0, 6.0])
        + _board(1, 2, (home, draw, away), [4.0, 4.0, 2.0])
        + _board(1, 3, (home, draw), [10.0, 10.0])
        + [_quote(1, 3, away, 0.9), _quote(1, 4, 999_999, 50.0)]
        + _board(2, 1, (home,), [1.5]))
    rows = consensus_fair_probabilities(frame)
    assert list(rows.columns) == _CONSENSUS_COLUMNS
    assert set(rows["match_id"]) == {1}
    assert list(rows["event_id"]) == sorted(rows["event_id"])
    by_event = {int(row.event_id): row for row in rows.itertuples()}
    assert by_event[home].fair_p == pytest.approx(expected[0])
    assert by_event[draw].fair_p == pytest.approx(expected[1])
    assert by_event[away].fair_p == pytest.approx(expected[2])
    assert by_event[home].best_odds == pytest.approx(10.0)
    assert by_event[draw].best_odds == pytest.approx(10.0)
    assert by_event[away].best_odds == pytest.approx(6.0)
    assert 999_999 not in by_event


def test_consensus_requires_both_btts_prices() -> None:
    yes_id, no_id = market_event_families()[1]
    frame = pd.DataFrame(
        _board(1, 1, (yes_id, no_id), [1.8, 2.2])
        + [_quote(1, 2, yes_id, 3.0)])
    rows = consensus_fair_probabilities(frame)
    yes = rows.loc[rows["event_id"] == yes_id].iloc[0]
    fair_yes = _devig([1.8, 2.2])[0]
    assert yes["fair_p"] == pytest.approx(fair_yes)
    assert yes["best_odds"] == pytest.approx(3.0)
    assert set(rows["event_id"]) == {yes_id, no_id}


def test_consensus_collapses_duplicate_prices_to_the_maximum() -> None:
    home, draw, away = market_event_families()[0]
    # Niższy kurs jest drugi. Zostawienie ostatniego wiersza dałoby 0.5.
    frame = pd.DataFrame([
        _quote(1, 1, home, 4.0),
        _quote(1, 1, home, 2.0),
        _quote(1, 1, draw, 4.0),
        _quote(1, 1, away, 4.0)])
    home_row = consensus_fair_probabilities(frame)
    home_row = home_row.loc[home_row["event_id"] == home].iloc[0]
    assert home_row["fair_p"] == pytest.approx(1.0 / 3.0)
    assert home_row["best_odds"] == pytest.approx(4.0)


def test_consensus_ignores_a_price_at_or_below_one() -> None:
    home, draw, away = market_event_families()[0]
    frame = pd.DataFrame(
        _board(1, 1, (home, draw, away), [2.0, 3.0, 1.0]))
    result = consensus_fair_probabilities(frame)
    assert result.empty
    assert list(result.columns) == _CONSENSUS_COLUMNS


def test_consensus_rejects_missing_columns() -> None:
    frame = pd.DataFrame({"match_id": [1]})
    with pytest.raises(ValueError, match="missing columns"):
        consensus_fair_probabilities(frame)


def test_consensus_rejects_a_non_integer_id() -> None:
    frame = pd.DataFrame([_quote(1, 1, 1, 2.0)])
    frame["match_id"] = 1.5
    with pytest.raises(ValueError, match="match_id"):
        consensus_fair_probabilities(frame)


def test_flat_stake_roi_before_and_after_tax() -> None:
    hit = np.array([1, 0, 1])
    odds = np.array([2.0, 3.5, 1.5])
    taxed = flat_stake_roi(hit, odds, BETTING_TAX_RATE)
    untaxed = flat_stake_roi(hit, odds, 0.0)
    before = hit * odds - 1.0
    after = hit * odds * (1.0 - BETTING_TAX_RATE) - 1.0
    assert taxed["bets"] == 3.0
    assert taxed["profit"] == pytest.approx(float(np.sum(before)))
    assert taxed["profit_after_tax"] == pytest.approx(float(np.sum(after)))
    assert taxed["roi"] == pytest.approx(float(np.mean(before)))
    assert taxed["roi_after_tax"] == pytest.approx(float(np.mean(after)))
    assert taxed["profit_after_tax"] != pytest.approx(taxed["profit"])
    assert untaxed["roi_after_tax"] == pytest.approx(untaxed["roi"])


def test_flat_stake_roi_rejects_a_short_price_and_a_full_tax() -> None:
    with pytest.raises(ValueError, match="greater than 1"):
        flat_stake_roi(np.array([1]), np.array([1.0]), 0.0)
    with pytest.raises(ValueError, match="tax_rate"):
        flat_stake_roi(np.array([1]), np.array([2.0]), 1.0)
    with pytest.raises(ValueError, match="one price per bet"):
        flat_stake_roi(np.array([1, 0]), np.array([2.0]), 0.0)


def test_information_coefficient_is_the_model_logit() -> None:
    market = np.array([0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.35, 0.65])
    model = np.array([0.1, 0.9, 0.25, 0.85, 0.45, 0.7, 0.3, 0.8])
    outcomes = np.array([0, 1, 0, 1, 0, 1, 0, 1])
    result = market_information_test(
        model, market, outcomes, samples=40, seed=7)
    again = market_information_test(
        model, market, outcomes, samples=40, seed=7)
    other = market_information_test(
        model, market, outcomes, samples=40, seed=8)
    coefficient = _logistic_coefficient(market, model, outcomes)
    assert result["model_coef"] == pytest.approx(coefficient)
    assert result["market_log_loss"] == pytest.approx(
        binary_log_loss(market, outcomes))
    assert result["ci_low"] <= result["ci_high"]
    for key in result:
        assert again[key] == pytest.approx(result[key])
    assert other["model_coef"] == pytest.approx(result["model_coef"])
    assert other["ci_low"] != pytest.approx(result["ci_low"])


def test_market_information_scores_result_one_vs_rest() -> None:
    market = np.array([
        [0.5, 0.3, 0.2],
        [0.2, 0.5, 0.3],
        [0.2, 0.2, 0.6],
        [0.6, 0.2, 0.2],
        [0.25, 0.5, 0.25],
        [0.3, 0.2, 0.5]])
    model = np.array([
        [0.7, 0.2, 0.1],
        [0.15, 0.7, 0.15],
        [0.1, 0.2, 0.7],
        [0.65, 0.2, 0.15],
        [0.2, 0.6, 0.2],
        [0.2, 0.15, 0.65]])
    outcomes = np.array([0, 1, 2, 0, 1, 2])
    result = market_information_test(
        model, market, outcomes, samples=30, seed=3)
    home = (outcomes == 0).astype(int)
    coefficient = _logistic_coefficient(
        market[:, 0], model[:, 0], home)
    assert result["h_model_coef"] == pytest.approx(coefficient)
    assert result["h_market_log_loss"] == pytest.approx(
        binary_log_loss(market[:, 0], home))
    assert "d_model_coef" in result
    assert "a_ci_high" in result
    assert "model_coef" not in result


def test_market_information_clips_extremes_and_rejects_shapes() -> None:
    scored = market_information_test(
        np.array([0.0, 1.0, 0.2, 0.8]),
        np.array([0.1, 0.9, 0.4, 0.6]),
        np.array([0, 1, 0, 1]),
        samples=20,
        seed=1)
    assert np.isfinite(scored["model_coef"])
    with pytest.raises(ValueError, match="same shape"):
        market_information_test(
            np.array([0.2, 0.8]),
            np.array([0.4]),
            np.array([0, 1]),
            10,
            1)
    with pytest.raises(ValueError, match="both classes"):
        market_information_test(
            np.array([0.2, 0.8]),
            np.array([0.3, 0.7]),
            np.array([1, 1]),
            10,
            1)
    with pytest.raises(ValueError, match="lie in"):
        market_information_test(
            np.array([1.2, 0.2]),
            np.array([0.4, 0.6]),
            np.array([1, 0]),
            10,
            1)


def test_fetch_match_odds_reads_batches_of_500() -> None:
    captured: list[tuple[str, tuple[object, ...]]] = []
    frames = [
        pd.DataFrame({
            "match_id": [1],
            "bookmaker_id": [4],
            "event_id": [9],
            "odds": [1.9]}),
        pd.DataFrame({
            "match_id": [501],
            "bookmaker_id": [4],
            "event_id": [9],
            "odds": [2.1]})]

    def _read_sql(
            query: str,
            _connection: object,
            params: tuple[object, ...] = ()) -> pd.DataFrame:
        captured.append((query, params))
        return frames[len(captured) - 1]

    with patch(
            f"{_REPOSITORY}.get_db_connection",
            return_value=_db_context()) as connect, patch(
            f"{_REPOSITORY}.pd.read_sql",
            side_effect=_read_sql):
        loaded = fetch_match_odds(list(range(1, 502)), [9, 9])
    first_query, first_params = captured[0]
    assert connect.call_count == 1
    assert len(captured) == 2
    assert "FROM odds" in first_query
    assert "odds > 1" in first_query
    assert "bookmaker AS bookmaker_id" in first_query
    assert "event AS event_id" in first_query
    assert first_params[:500] == tuple(range(1, 501))
    assert first_params[500:] == (9,)
    assert captured[1][1] == (501, 9)
    assert list(loaded["match_id"]) == [1, 501]
    assert list(loaded.columns) == _ODDS_COLUMNS


def test_fetch_match_odds_skips_the_database_when_empty() -> None:
    with patch(f"{_REPOSITORY}.get_db_connection") as connect:
        empty_matches = fetch_match_odds([], [9])
        empty_events = fetch_match_odds([1], [])
    connect.assert_not_called()
    assert empty_matches.empty
    assert empty_events.empty
    assert list(empty_matches.columns) == _ODDS_COLUMNS


def test_fetch_match_odds_rejects_a_non_integer_id() -> None:
    with pytest.raises(ValueError, match="integers"):
        fetch_match_odds([1.5], [9])


def _configured_event_ids() -> dict[str, int]:
    registry = json.loads(
        DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    found: dict[str, int] = {}
    for relative in registry["models"].values():
        path = REPO_ROOT / relative
        events = json.loads(path.read_text(encoding="utf-8"))["events"]
        for key, value in events.items():
            if key in _FAMILY_KEYS:
                found[key] = int(value)
    return found


def _devig(prices: list[float]) -> list[float]:
    implied = [1.0 / price for price in prices]
    total = sum(implied)
    return [share / total for share in implied]


def _board(
        match_id: int,
        bookmaker_id: int,
        event_ids: tuple[int, ...],
        prices: list[float]) -> list[dict[str, int | float]]:
    return [
        _quote(match_id, bookmaker_id, event_id, price)
        for event_id, price in zip(event_ids, prices)]


def _quote(
        match_id: int,
        bookmaker_id: int,
        event_id: int,
        price: float) -> dict[str, int | float]:
    return {
        "match_id": match_id,
        "bookmaker_id": bookmaker_id,
        "event_id": event_id,
        "odds": price}


def _logistic_coefficient(
        market: np.ndarray,
        model: np.ndarray,
        outcomes: np.ndarray) -> float:
    logits = np.log(market / (1.0 - market))
    model_logits = np.log(model / (1.0 - model))
    features = np.column_stack((logits, model_logits))
    classifier = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=_LOGISTIC_MAX_ITER)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="scipy.optimize: The `disp` and `iprint` options",
            category=DeprecationWarning)
        classifier.fit(features, np.asarray(outcomes, dtype=int))
    return float(classifier.coef_[0, 1])


def _db_context() -> MagicMock:
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return context
