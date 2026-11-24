"""Market consensus and diagnostic betting scores.

Families are the 1X2, BTTS and Over/Under 2.5 events named in the
football model configs. Numeric event ids are not written here.
Nothing in this module opens a database connection.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from models.pipeline.betting.devig import fair_probability
from models.pipeline.core.config import load_model_config
from models.pipeline.core.model_lineup import DEFAULT_REGISTRY_PATH
from models.pipeline.core.model_lineup import load_model_registry
from models.pipeline.evaluation.metrics import binary_log_loss


_INPUT_COLUMNS = ("match_id", "bookmaker_id", "event_id", "odds")
_CONSENSUS_COLUMNS = ("match_id", "event_id", "fair_p", "best_odds")
_MIN_DECIMAL_ODDS = 1.0
_MARKET_EVENT_KEYS = (
    ("result_home", "result_draw", "result_away"),
    ("btts_yes", "btts_no"),
    ("over_25", "under_25"))
_KNOWN_EVENT_KEYS = frozenset(
    key for keys in _MARKET_EVENT_KEYS for key in keys)
_RESULT_CLASS_COUNT = 3
_RESULT_CLASS_NAMES = ("h", "d", "a")
_PROBABILITY_CLIP = 1e-12
_BOOTSTRAP_LOW = 2.5
_BOOTSTRAP_HIGH = 97.5
_BOOTSTRAP_ATTEMPT_FACTOR = 50
_LOGISTIC_MAX_ITER = 1000


def market_event_families(
        registry_path: Path = DEFAULT_REGISTRY_PATH
        ) -> tuple[tuple[int, ...], ...]:
    """Return 1X2, BTTS and totals event ids from model configs.

    The order is home/draw/away, yes/no, then over/under. A key
    that is missing, not an integer, or that disagrees between
    configs raises ValueError.
    """
    found: dict[str, int] = {}
    registry = load_model_registry(registry_path)
    for config_path in registry.values():
        events = load_model_config(config_path).events
        _collect_event_ids(events, found, config_path)
    return tuple(
        tuple(_required_event_id(key, found) for key in keys)
        for keys in _MARKET_EVENT_KEYS)


def consensus_fair_probabilities(odds: pd.DataFrame) -> pd.DataFrame:
    """Return the mean de-vigged price and the highest odds.

    A bookmaker enters the average only when every event of the
    family is priced above 1. 1X2 has three events. BTTS and
    Over/Under 2.5 have two. ``best_odds`` is the highest price of
    that event, including bookmakers left out of the average.
    Events outside the three families are ignored. Rows are ordered
    by match id, then event id.
    """
    prepared = _prepare_odds(odds)
    if prepared.empty:
        return _empty_consensus()
    return _consensus_rows(prepared, market_event_families())


def market_information_test(
        p_model: np.ndarray,
        p_market: np.ndarray,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, float]:
    """Return the logistic coefficient of the model given the market.

    Features are the logits of the two probabilities. ``model_coef``
    is the coefficient on the model logit. ``ci_low`` and ``ci_high``
    are the 2.5 and 97.5 percentiles of a match bootstrap.
    ``market_log_loss`` is the binary log loss of the market.
    A three-column matrix is 1X2, scored one-vs-rest for home, draw
    and away. Those keys use the prefixes ``h_``, ``d_`` and ``a_``.
    Each scored class must both occur and fail to occur.
    """
    _positive_int(samples, "samples")
    _require_int(seed, "seed")
    model = np.asarray(p_model, dtype=float)
    market = np.asarray(p_market, dtype=float)
    if model.shape != market.shape:
        raise ValueError(
            "p_model and p_market must have the same shape")
    if model.ndim == 1:
        return _binary_information(
            model, market, outcomes, samples, seed)
    if model.ndim == 2 and model.shape[1] == _RESULT_CLASS_COUNT:
        return _result_information(
            model, market, outcomes, samples, seed)
    raise ValueError(
        "probabilities must be a vector or a three-class matrix")


def flat_stake_roi(
        hit: np.ndarray,
        odds: np.ndarray,
        tax_rate: float) -> dict[str, float]:
    """Return unit-stake profit and ROI before and after tax.

    Profit before tax is ``hit * odds - 1``. Profit after tax is
    ``hit * odds * (1 - tax_rate) - 1``. ``roi`` is the mean
    profit and ``bets`` is the number of rows. Callers pass
    ``BETTING_TAX_RATE`` from ``backend.betting_tax``.
    """
    wins = _binary_hits(hit)
    prices = _prices(odds, len(wins))
    rate = _tax_rate(tax_rate)
    before = wins * prices - 1.0
    # Ten sam wzór co EV po podatku w serwisie zakładów.
    after = wins * prices * (1.0 - rate) - 1.0
    return {
        "bets": float(len(wins)),
        "profit": float(np.sum(before)),
        "profit_after_tax": float(np.sum(after)),
        "roi": float(np.mean(before)),
        "roi_after_tax": float(np.mean(after))}


def _collect_event_ids(
        events: dict[str, int | str],
        found: dict[str, int],
        config_path: Path) -> None:
    for key, reference in events.items():
        if key not in _KNOWN_EVENT_KEYS:
            continue
        event_id = _event_id(key, reference, config_path)
        previous = found.get(key)
        if previous is not None and previous != event_id:
            raise ValueError(
                f"Event {key} has ids {previous} and {event_id}")
        found[key] = event_id


def _event_id(
        key: str,
        reference: object,
        config_path: Path) -> int:
    if isinstance(reference, bool) or not isinstance(reference, int):
        raise ValueError(
            f"Event {key} in {config_path} must be an integer id")
    return reference


def _required_event_id(key: str, found: dict[str, int]) -> int:
    if key not in found:
        raise ValueError(
            f"Market event {key} is missing from model configs")
    return found[key]


def _prepare_odds(odds: pd.DataFrame) -> pd.DataFrame:
    _require_columns(odds)
    if odds.empty:
        return pd.DataFrame(columns=list(_INPUT_COLUMNS))
    frame = odds.loc[:, list(_INPUT_COLUMNS)].copy()
    frame["match_id"] = _id_series(frame["match_id"], "match_id")
    frame["bookmaker_id"] = _id_series(
        frame["bookmaker_id"], "bookmaker_id")
    frame["event_id"] = _id_series(frame["event_id"], "event_id")
    frame["odds"] = pd.to_numeric(frame["odds"], errors="coerce")
    numeric = frame["odds"].to_numpy(dtype=float)
    valid = np.isfinite(numeric) & (numeric > _MIN_DECIMAL_ODDS)
    frame = frame.loc[valid]
    if frame.empty:
        return frame
    return frame.groupby(
        ["match_id", "bookmaker_id", "event_id"],
        as_index=False)["odds"].max()


def _require_columns(odds: pd.DataFrame) -> None:
    if not isinstance(odds, pd.DataFrame):
        raise ValueError("odds must be a DataFrame")
    missing = [
        name for name in _INPUT_COLUMNS if name not in odds.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"odds are missing columns: {joined}")


def _id_series(values: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        raise ValueError(f"{name} must be integers")
    numeric = pd.to_numeric(values, errors="coerce")
    whole = numeric.notna() & np.isfinite(numeric)
    whole = whole & (numeric == numeric.round())
    if not bool(whole.all()):
        raise ValueError(f"{name} must be integers")
    return numeric.astype("int64")


def _consensus_rows(
        odds: pd.DataFrame,
        families: tuple[tuple[int, ...], ...]) -> pd.DataFrame:
    family_of = _family_index(families)
    priced = odds.loc[odds["event_id"].isin(family_of)].copy()
    if priced.empty:
        return _empty_consensus()
    priced["family"] = priced["event_id"].map(family_of)
    rows: list[dict[str, int | float]] = []
    grouped = priced.groupby(["match_id", "family"], sort=False)
    for (match_id, family_index), group in grouped:
        rows.extend(_family_rows(
            int(match_id),
            families[int(family_index)],
            group))
    return _consensus_frame(rows)


def _family_index(
        families: tuple[tuple[int, ...], ...]) -> dict[int, int]:
    index: dict[int, int] = {}
    for family_index, event_ids in enumerate(families):
        for event_id in event_ids:
            if event_id in index:
                raise ValueError(
                    f"Event {event_id} belongs to two market families")
            index[event_id] = family_index
    return index


def _family_rows(
        match_id: int,
        event_ids: tuple[int, ...],
        group: pd.DataFrame) -> list[dict[str, int | float]]:
    best_prices = group.groupby("event_id")["odds"].max()
    best = {
        int(event_id): float(price)
        for event_id, price in best_prices.items()}
    collected: dict[int, list[float]] = {
        event_id: [] for event_id in event_ids}
    for _bookmaker_id, book in group.groupby("bookmaker_id", sort=False):
        prices = {
            int(event_id): float(price)
            for event_id, price in zip(
                book["event_id"].tolist(),
                book["odds"].tolist())}
        shares = _fair_shares(prices, event_ids)
        if shares is None:
            continue
        for event_id, fair in shares.items():
            collected[event_id].append(fair)
    return _priced_rows(match_id, event_ids, collected, best)


def _fair_shares(
        prices: dict[int, float],
        event_ids: tuple[int, ...]) -> dict[int, float] | None:
    """Return de-vigged shares, or None when the board is partial."""
    implied = {
        event_id: 1.0 / prices[event_id]
        for event_id in event_ids
        if event_id in prices}
    implied_sum = float(sum(implied.values()))
    size = len(event_ids)
    shares: dict[int, float] = {}
    for event_id, share in implied.items():
        fair = fair_probability(share, implied_sum, len(implied), size)
        if math.isnan(fair):
            return None
        shares[event_id] = fair
    if len(shares) != size:
        return None
    return shares


def _priced_rows(
        match_id: int,
        event_ids: tuple[int, ...],
        collected: dict[int, list[float]],
        best: dict[int, float]) -> list[dict[str, int | float]]:
    rows: list[dict[str, int | float]] = []
    for event_id in event_ids:
        shares = collected[event_id]
        if not shares:
            continue
        rows.append({
            "match_id": match_id,
            "event_id": event_id,
            "fair_p": float(np.mean(shares)),
            "best_odds": best[event_id]})
    return rows


def _consensus_frame(
        rows: list[dict[str, int | float]]) -> pd.DataFrame:
    if not rows:
        return _empty_consensus()
    frame = pd.DataFrame(rows)
    ordered = frame.sort_values(
        ["match_id", "event_id"],
        kind="mergesort")
    return ordered.reset_index(drop=True).loc[:, list(_CONSENSUS_COLUMNS)]


def _empty_consensus() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_CONSENSUS_COLUMNS))


def _result_information(
        model: np.ndarray,
        market: np.ndarray,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, float]:
    labels = _class_indexes(outcomes, model.shape[0], _RESULT_CLASS_COUNT)
    merged: dict[str, float] = {}
    for class_index, name in enumerate(_RESULT_CLASS_NAMES):
        observed = (labels == class_index).astype(int)
        scored = _binary_information(
            model[:, class_index],
            market[:, class_index],
            observed,
            samples,
            seed)
        for key, value in scored.items():
            merged[f"{name}_{key}"] = value
    return merged


def _binary_information(
        model: np.ndarray,
        market: np.ndarray,
        outcomes: np.ndarray,
        samples: int,
        seed: int) -> dict[str, float]:
    model_p = _probability(model, "p_model")
    market_p = _probability(market, "p_market")
    labels = _class_indexes(outcomes, len(model_p), 2).astype(float)
    if not _both_classes(labels):
        raise ValueError("outcomes must contain both classes")
    observed = _model_coefficient(market_p, model_p, labels)
    coefficients = _bootstrap_coefficients(
        market_p, model_p, labels, samples, seed)
    low, high = np.percentile(
        coefficients, [_BOOTSTRAP_LOW, _BOOTSTRAP_HIGH])
    return {
        "model_coef": observed,
        "ci_low": float(low),
        "ci_high": float(high),
        "market_log_loss": binary_log_loss(market_p, labels)}


def _bootstrap_coefficients(
        market: np.ndarray,
        model: np.ndarray,
        labels: np.ndarray,
        samples: int,
        seed: int) -> np.ndarray:
    # Próba z jedną klasą nie ma współczynnika, więc losujemy inną.
    generator = np.random.default_rng(seed)
    coefficients = np.empty(samples, dtype=float)
    filled = 0
    attempts = 0
    limit = samples * _BOOTSTRAP_ATTEMPT_FACTOR
    count = len(labels)
    while filled < samples:
        if attempts >= limit:
            raise ValueError(
                "bootstrap samples must contain both classes")
        attempts += 1
        chosen = generator.integers(0, count, size=count)
        drawn = labels[chosen]
        if not _both_classes(drawn):
            continue
        coefficients[filled] = _model_coefficient(
            market[chosen], model[chosen], drawn)
        filled += 1
    return coefficients


def _model_coefficient(
        market: np.ndarray,
        model: np.ndarray,
        labels: np.ndarray) -> float:
    features = np.column_stack((_logit(market), _logit(model)))
    classifier = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=_LOGISTIC_MAX_ITER)
    with warnings.catch_warnings():
        # SciPy ostrzega w L-BFGS wołanym przez sklearn 1.7.
        warnings.filterwarnings(
            "ignore",
            message="scipy.optimize: The `disp` and `iprint` options",
            category=DeprecationWarning)
        classifier.fit(features, labels.astype(int))
    return float(classifier.coef_[0, 1])


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(
        probabilities,
        _PROBABILITY_CLIP,
        1.0 - _PROBABILITY_CLIP)
    return np.log(clipped / (1.0 - clipped))


def _both_classes(labels: np.ndarray) -> bool:
    return bool(np.any(labels == 0.0) and np.any(labels == 1.0))


def _probability(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must contain at least one value")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite")
    if np.any((array < 0.0) | (array > 1.0)):
        raise ValueError(f"{name} must lie in [0, 1]")
    return array


def _binary_hits(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or array.size == 0:
        raise ValueError("hit must contain at least one bet")
    if array.dtype == np.bool_:
        return array.astype(float)
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError("hit must be 0 or 1")
    if not np.isfinite(array.astype(float)).all():
        raise ValueError("hit must be 0 or 1")
    hits = array.astype(float)
    if not np.all((hits == 0.0) | (hits == 1.0)):
        raise ValueError("hit must be 0 or 1")
    return hits


def _prices(values: np.ndarray, count: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) != count:
        raise ValueError("odds must have one price per bet")
    finite = np.isfinite(array).all()
    if not finite or np.any(array <= _MIN_DECIMAL_ODDS):
        raise ValueError("odds must be finite and greater than 1")
    return array


def _tax_rate(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("tax_rate must be a number")
    if not math.isfinite(float(value)) or value < 0.0 or value >= 1.0:
        raise ValueError("tax_rate must lie in [0, 1)")
    return float(value)


def _class_indexes(
        labels: np.ndarray,
        count: int,
        class_count: int) -> np.ndarray:
    values = np.asarray(labels)
    if values.ndim != 1 or len(values) != count:
        raise ValueError("outcomes must have one class index per match")
    if count == 0:
        raise ValueError("outcomes must contain at least one match")
    if values.dtype == np.bool_ or not np.issubdtype(values.dtype, np.number):
        raise ValueError("outcomes must be class indexes")
    if not np.isfinite(values.astype(float)).all():
        raise ValueError("outcomes must be finite")
    indexes = values.astype(int)
    if not np.all(indexes == values):
        raise ValueError("outcomes must be class indexes")
    if np.any((indexes < 0) | (indexes >= class_count)):
        raise ValueError("outcomes must be class indexes")
    return indexes


def _positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _require_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
