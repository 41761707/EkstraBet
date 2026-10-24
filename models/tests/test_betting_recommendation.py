"""Insert verdicts for future pairs without training or updating."""

from __future__ import annotations

import hashlib
import inspect
import json
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pandas as pd
import pytest
from mysql.connector import IntegrityError

from models.pipeline.betting import recommendation
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.domain import BettingRecommendation
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import NUMERIC_FEATURE_COLUMNS
from models.pipeline.betting.recommendation import PredictReport
from models.pipeline.betting.recommendation import fetch_unscored_candidates
from models.pipeline.betting.recommendation import model_file_fingerprint
from models.pipeline.betting.recommendation import run_betting_predict
from models.pipeline.betting.recommendation import write_recommendations
from models.pipeline.betting.trainer import train_meta_model
from models.pipeline.data.betting_candidate_repository import (
    BETTING_CANDIDATE_COLUMNS)


_AS_OF = datetime(2026, 8, 1, 12, 0)
_FUTURE = _AS_OF + timedelta(hours=3)
_PAST = _AS_OF - timedelta(days=1)
_ARTIFACT_FILES = (
    "model.joblib",
    "feature_columns.json",
    "metrics.json",
    "meta.json")
_WRITE_WORDS = ("UPDATE", "DELETE", "REPLACE", "ON DUPLICATE")


class _Store:
    """In-memory unique key for betting_recommendations."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.inserted: list[tuple[object, ...]] = []
        self.keys: set[tuple[int, int, str]] = set()
        self.commits = 0


class _Cursor:
    """SELECT and INSERT against one store. Duplicates raise 1062."""

    def __init__(self, store: _Store) -> None:
        self.store = store
        self._rows: list[tuple[int, int]] = []

    def execute(
            self,
            query: str,
            params: tuple[object, ...] | None = None) -> None:
        text = " ".join(query.split())
        self.store.queries.append(text)
        upper = text.upper()
        for word in _WRITE_WORDS:
            if word in upper:
                raise AssertionError(text)
        if upper.startswith("SELECT"):
            self._select(params)
            return
        if upper.startswith("INSERT"):
            self._insert(params)
            return
        raise AssertionError(text)

    def fetchall(self) -> list[tuple[int, int]]:
        return list(self._rows)

    def close(self) -> None:
        return None

    def _select(self, params: tuple[object, ...] | None) -> None:
        if params is None:
            raise AssertionError("select without a fingerprint")
        fingerprint = str(params[0])
        self._rows = [
            (prediction_id, odds_id)
            for prediction_id, odds_id, stored in self.store.keys
            if stored == fingerprint]

    def _insert(self, params: tuple[object, ...] | None) -> None:
        if params is None or len(params) != 5:
            raise AssertionError("insert must carry five fields")
        key = (int(params[0]), int(params[1]), str(params[4]))
        if key in self.store.keys:
            raise IntegrityError(msg="Duplicate entry", errno=1062)
        self.store.keys.add(key)
        self.store.inserted.append(params)


class _Connection:
    def __init__(self, store: _Store) -> None:
        self.store = store

    def cursor(self) -> _Cursor:
        return _Cursor(self.store)

    def commit(self) -> None:
        self.store.commits += 1


class _FailingCursor:
    """Raise a foreign-key error instead of inserting."""

    def execute(self, query: str, params: object = None) -> None:
        raise IntegrityError(msg=f"foreign key: {query}", errno=1452)

    def close(self) -> None:
        return None


class _FailingConnection:
    def cursor(self) -> _FailingCursor:
        return _FailingCursor()

    def commit(self) -> None:
        raise AssertionError("commit after a failed insert")


def _connect(store: _Store) -> object:
    @contextmanager
    def _open() -> Iterator[_Connection]:
        yield _Connection(store)

    return _open


def _training_config(random_state: int) -> BettingTrainingConfig:
    return BettingTrainingConfig(
        model_name="FOOTBALL_BETTING_META_V1",
        algorithm="LogisticRegression",
        class_weight="balanced",
        calibration_methods=("sigmoid",),
        random_state=random_state,
        train_fraction=0.6,
        calibration_fraction=0.2,
        test_fraction=0.2)


def _train_strategy() -> BettingStrategyConfig:
    return BettingStrategyConfig(
        probability_threshold=0.5,
        football_sport_name="Piłka nożna",
        excluded_model_names=(
            "FOOTBALL_PLAYED_BETTER_V1",
            "FOOTBALL_PLAYED_BETTER_NOXG_V1"),
        max_brier=0.24,
        max_reliability_error=0.05,
        min_roi=0.0)


def _write_passing_metrics(directory: Path) -> None:
    payload = {"brier": 0.2, "reliability": 0.01, "roi": 0.1}
    (directory / "metrics.json").write_text(
        json.dumps(payload),
        encoding="utf-8")


def _train(directory: Path, random_state: int) -> Path:
    train_meta_model(
        _dataset(),
        _training_config(random_state),
        directory,
        strategy=_train_strategy())
    _write_passing_metrics(directory)
    return directory


def _default_label(match_id: int) -> int:
    return match_id % 2


def _default_league(match_id: int) -> object:
    if match_id == 1:
        return None
    return str((match_id % 3) + 1)


def _default_market(match_id: int) -> str:
    if match_id % 2 == 0:
        return "BTTS"
    return "REZULTAT"


def _dataset(count: int = 15) -> BettingDataset:
    """Return a finished dataset with one row per match."""
    rows: list[dict[str, object]] = []
    labels: list[int] = []
    for match_id in range(1, count + 1):
        label = _default_label(match_id)
        probability = 0.8 if label == 1 else 0.25
        rows.append({
            "model_probability": probability,
            "implied_probability": 0.5,
            "devig_probability": float("nan"),
            "edge": probability - 0.5,
            "ev": probability * 2.0 - 1.0,
            "kickoff_weekday_sin": 0.0,
            "kickoff_weekday_cos": 1.0,
            "kickoff_hour_sin": 0.0,
            "kickoff_hour_cos": 1.0,
            "model_id": "8",
            "market_family": _default_market(match_id),
            "league_id": _default_league(match_id)})
        labels.append(label)
    features = pd.DataFrame(rows).loc[:, list(FEATURE_COLUMNS)]
    for name in NUMERIC_FEATURE_COLUMNS:
        features[name] = features[name].astype("float64")
    index = features.index
    return BettingDataset(
        features=features,
        labels=pd.Series(labels, index=index, dtype="int64", name="label"),
        prediction_id=_ids(count, 1, index, "prediction_id"),
        odds_id=_ids(count, 1000, index, "odds_id"),
        match_id=_ids(count, 1, index, "match_id"),
        kickoff=_kickoffs(count, index),
        odds=pd.Series(
            [2.0] * count,
            index=index,
            dtype="float64",
            name="odds"))


def _ids(
        count: int,
        start: int,
        index: pd.Index,
        name: str) -> pd.Series:
    values = [start + offset for offset in range(count)]
    return pd.Series(values, index=index, dtype="int64", name=name)


def _kickoffs(count: int, index: pd.Index) -> pd.Series:
    values = [
        datetime(2026, 1, match_id, 18, 0)
        for match_id in range(1, count + 1)]
    return pd.Series(values, index=index, dtype="object", name="kickoff")


def _candidate_row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": _FUTURE,
        "value_pct": 62.0,
        "odds": 1.91,
        "devig_probability": 0.5}
    payload.update(overrides)
    return payload


def _frame(*rows: dict[str, object]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=list(BETTING_CANDIDATE_COLUMNS))
    return pd.DataFrame(list(rows))


def _recommendation(**overrides: object) -> BettingRecommendation:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "decision": "bet",
        "calibrated_probability": 0.62,
        "model_fingerprint": "ab" * 32}
    payload.update(overrides)
    return BettingRecommendation(**payload)


def _copy_artifact(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in _ARTIFACT_FILES:
        (destination / name).write_bytes((source / name).read_bytes())


def _predict(
        artifact: Path,
        frame: pd.DataFrame,
        store: _Store,
        as_of: datetime = _AS_OF) -> tuple[PredictReport, object]:
    with (
            patch.object(
                recommendation,
                "fetch_candidates",
                return_value=frame) as fetch,
            patch.object(
                recommendation,
                "get_db_connection",
                _connect(store))):
        report = run_betting_predict(artifact, as_of)
    return report, fetch


def _sql(query: str) -> str:
    return " ".join(query.split()).upper()


@pytest.fixture(scope="module")
def ready_artifact(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _train(tmp_path_factory.mktemp("ready-betting"), 42)


@pytest.fixture(scope="module")
def other_artifact(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _train(tmp_path_factory.mktemp("other-betting"), 7)


def test_model_file_fingerprint_hashes_raw_bytes(tmp_path: Path) -> None:
    path = tmp_path / "model.joblib"
    path.write_bytes(b"abc")
    first = model_file_fingerprint(path)
    assert first == hashlib.sha256(b"abc").hexdigest()
    assert len(first) == 64
    path.write_bytes(b"abcd")
    assert model_file_fingerprint(path) != first


def test_write_statement_is_insert_only() -> None:
    text = _sql(recommendation._INSERT_SQL)
    assert text.startswith("INSERT INTO BETTING_RECOMMENDATIONS (")
    columns = text.split("(", 1)[1].split(")", 1)[0]
    names = [part.strip() for part in columns.split(",")]
    assert names == [
        "PREDICTION_ID",
        "ODDS_ID",
        "DECISION",
        "CALIBRATED_PROBABILITY",
        "MODEL_FINGERPRINT"]
    for word in _WRITE_WORDS:
        assert word not in text
    scored = _sql(recommendation._SCORED_PAIRS_SQL)
    assert scored.startswith("SELECT PREDICTION_ID, ODDS_ID")
    assert "FROM BETTING_RECOMMENDATIONS" in scored
    source = inspect.getsource(recommendation)
    assert "train_meta_model" not in source
    assert ".fit(" not in source


def test_missing_candidate_is_inserted(ready_artifact: Path) -> None:
    store = _Store()
    report, fetch = _predict(
        ready_artifact,
        _frame(_candidate_row()),
        store)
    assert report.inserted_count == 1
    assert report.skipped_existing_count == 0
    assert report.rejected_count == 0
    assert len(store.inserted) == 1
    params = store.inserted[0]
    assert params[0] == 10
    assert params[1] == 20
    assert params[2] in ("bet", "no_bet")
    assert 0.0 <= float(params[3]) <= 1.0
    assert params[4] == model_file_fingerprint(
        ready_artifact / "model.joblib")
    assert 1.91 not in params
    assert 62.0 not in params
    assert fetch.call_args.args[0] == _AS_OF
    assert fetch.call_args.args[1] == recommendation._OPEN_HORIZON
    assert fetch.call_args.args[2].football_sport_name == "Piłka nożna"
    assert store.commits == 1


def test_existing_pair_is_skipped(ready_artifact: Path) -> None:
    store = _Store()
    digest = model_file_fingerprint(ready_artifact / "model.joblib")
    store.keys.add((10, 20, digest))
    report, _fetch = _predict(
        ready_artifact,
        _frame(_candidate_row()),
        store)
    assert report == PredictReport(
        inserted_count=0,
        skipped_existing_count=1,
        rejected_count=0)
    assert store.inserted == []


def test_second_call_inserts_nothing(ready_artifact: Path) -> None:
    store = _Store()
    frame = _frame(_candidate_row())
    first, _fetch = _predict(ready_artifact, frame, store)
    saved = list(store.inserted)
    second, _fetch_again = _predict(ready_artifact, frame, store)
    assert first.inserted_count == 1
    assert second.inserted_count == 0
    assert second.skipped_existing_count == 1
    assert store.inserted == saved
    assert len(store.keys) == 1


def test_second_fingerprint_inserts_a_new_row(
        ready_artifact: Path,
        other_artifact: Path) -> None:
    first = model_file_fingerprint(ready_artifact / "model.joblib")
    second = model_file_fingerprint(other_artifact / "model.joblib")
    assert first != second
    store = _Store()
    frame = _frame(_candidate_row())
    ready_report, _fetch = _predict(ready_artifact, frame, store)
    other_report, _other_fetch = _predict(other_artifact, frame, store)
    assert ready_report.inserted_count == 1
    assert other_report.inserted_count == 1
    assert len(store.inserted) == 2
    assert store.inserted[0][0] == store.inserted[1][0] == 10
    assert store.inserted[0][1] == store.inserted[1][1] == 20
    assert {store.inserted[0][4], store.inserted[1][4]} == {first, second}


def test_past_kickoff_is_skipped(ready_artifact: Path) -> None:
    store = _Store()
    frame = _frame(
        _candidate_row(
            prediction_id=1,
            odds_id=11,
            kickoff=_PAST),
        _candidate_row(
            prediction_id=2,
            odds_id=12,
            kickoff=_AS_OF),
        _candidate_row(
            prediction_id=3,
            odds_id=13,
            kickoff=_FUTURE))
    report, _fetch = _predict(ready_artifact, frame, store)
    assert report.inserted_count == 1
    assert report.skipped_existing_count == 0
    assert [params[0] for params in store.inserted] == [3]


def test_invalid_pair_is_rejected(ready_artifact: Path) -> None:
    store = _Store()
    frame = _frame(
        _candidate_row(prediction_id=4, odds_id=14, odds=1.0),
        _candidate_row(prediction_id=5, odds_id=15, value_pct=140.0),
        _candidate_row(prediction_id=6, odds_id=16))
    report, _fetch = _predict(ready_artifact, frame, store)
    assert report.inserted_count == 1
    assert report.rejected_count == 2
    assert [params[0] for params in store.inserted] == [6]
    assert 140.0 not in store.inserted[0]


def test_unready_model_writes_nothing(tmp_path: Path) -> None:
    with (
            patch.object(recommendation, "fetch_candidates") as fetch,
            patch.object(recommendation, "get_db_connection") as connect):
        report = run_betting_predict(tmp_path, _AS_OF)
    assert report == PredictReport(0, 0, 0)
    assert fetch.call_count == 0
    assert connect.call_count == 0


def test_fingerprint_mismatch_writes_nothing(
        ready_artifact: Path,
        tmp_path: Path) -> None:
    _copy_artifact(ready_artifact, tmp_path)
    _write_passing_metrics(tmp_path)
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(model_path.read_bytes() + b"x")
    store = _Store()
    with pytest.raises(ValueError, match="model file fingerprint"):
        _predict(tmp_path, _frame(_candidate_row()), store)
    assert store.queries == []
    assert store.inserted == []


def test_duplicate_key_does_not_update() -> None:
    store = _Store()
    row = _recommendation()
    with patch.object(recommendation, "get_db_connection", _connect(store)):
        first = write_recommendations((row,))
        second = write_recommendations((row, row))
    assert first == 1
    assert second == 0
    assert len(store.keys) == 1
    assert store.inserted == [(
        10,
        20,
        "bet",
        0.62,
        "ab" * 32)]
    for query in store.queries:
        upper = query.upper()
        assert upper.startswith("INSERT INTO BETTING_RECOMMENDATIONS")
        for word in _WRITE_WORDS:
            assert word not in upper


def test_foreign_key_error_is_not_swallowed() -> None:
    @contextmanager
    def _open() -> Iterator[_FailingConnection]:
        yield _FailingConnection()

    with patch.object(recommendation, "get_db_connection", _open):
        with pytest.raises(IntegrityError):
            write_recommendations((_recommendation(),))


def test_empty_write_does_not_open_a_connection() -> None:
    def _open() -> object:
        raise AssertionError("database opened")

    with patch.object(recommendation, "get_db_connection", _open):
        assert write_recommendations(()) == 0


def test_fetch_unscored_drops_past_and_stored_pairs() -> None:
    store = _Store()
    digest = "cd" * 32
    store.keys.add((6, 16, digest))
    frame = _frame(
        _candidate_row(prediction_id=1, odds_id=11, kickoff=_PAST),
        _candidate_row(prediction_id=6, odds_id=16, kickoff=_FUTURE),
        _candidate_row(prediction_id=7, odds_id=17, kickoff=_FUTURE))
    with (
            patch.object(
                recommendation,
                "fetch_candidates",
                return_value=frame),
            patch.object(
                recommendation,
                "get_db_connection",
                _connect(store))):
        unscored = fetch_unscored_candidates(digest, _AS_OF)
    assert unscored["prediction_id"].tolist() == [7]
    assert "odds" in unscored.columns
    assert "value_pct" in unscored.columns


def test_fetch_unscored_rejects_a_short_fingerprint() -> None:
    with pytest.raises(ValueError, match="model_fingerprint"):
        fetch_unscored_candidates("abc", _AS_OF)


def test_run_rejects_an_aware_clock() -> None:
    aware = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="as_of"):
        run_betting_predict(Path("missing"), aware)
