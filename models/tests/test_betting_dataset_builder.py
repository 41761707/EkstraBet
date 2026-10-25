"""Walk-forward dataset: labels, disjoint matches, and no outcome in X."""

from __future__ import annotations

import inspect
from datetime import datetime
from datetime import timezone

import pandas as pd
import pytest

from backend.sports.football.outcome_evaluator import SettlementCandidate
from backend.sports.football.outcome_evaluator import (
    evaluate_football_outcome)
from models.pipeline.betting import dataset_builder as dataset_module
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.dataset_builder import DatasetManifest
from models.pipeline.betting.dataset_builder import TemporalSplit
from models.pipeline.betting.dataset_builder import build_betting_dataset
from models.pipeline.betting.dataset_builder import build_dataset_manifest
from models.pipeline.betting.dataset_builder import build_walk_forward_splits
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import POST_MATCH_DENYLIST
from models.pipeline.betting.features import feature_schema_fingerprint


_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "to_sql",
    "get_db_connection")


def _config(**overrides: object) -> BettingTrainingConfig:
    payload: dict[str, object] = {
        "model_name": "FOOTBALL_BETTING_META_V1",
        "algorithm": "LogisticRegression",
        "class_weight": "balanced",
        "calibration_methods": ("sigmoid", "isotonic"),
        "random_state": 42,
        "train_fraction": 0.6,
        "calibration_fraction": 0.2,
        "test_fraction": 0.2}
    payload.update(overrides)
    return BettingTrainingConfig(**payload)


def _row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": datetime(2026, 1, 1, 18, 0),
        "value_pct": 55.0,
        "odds": 2.0,
        "devig_probability": None,
        "result": "1",
        "home_team_goals": 2,
        "away_team_goals": 1,
        "event_name": "1"}
    payload.update(overrides)
    return payload


def _history() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    next_id = 1
    for match_id in range(1, 11):
        kickoff = datetime(2026, 1, match_id, 18, 0)
        events = (1, 2, 8) if match_id == 6 else (1,)
        for event_id in events:
            rows.append(_row(
                prediction_id=next_id,
                odds_id=1000 + next_id,
                match_id=match_id,
                event_id=event_id,
                kickoff=kickoff,
                event_name=str(event_id)))
            next_id += 1
    rows.append(_row(
        prediction_id=next_id,
        odds_id=1000 + next_id,
        match_id=5,
        event_id=1,
        kickoff=datetime(2026, 1, 5, 18, 0),
        odds=1.0))
    rows.append(_row(
        prediction_id=next_id + 1,
        odds_id=1001 + next_id,
        match_id=11,
        kickoff=datetime(2026, 1, 11, 18, 0),
        result="0",
        home_team_goals=None,
        away_team_goals=None))
    return pd.DataFrame(rows)


def _prepared(
        frame: pd.DataFrame | None = None,
        **overrides: object
        ) -> tuple[pd.DataFrame, BettingDataset, list[TemporalSplit]]:
    source = _history() if frame is None else frame
    dataset = build_betting_dataset(source)
    splits = build_walk_forward_splits(
        dataset.split_frame(),
        _config(**overrides))
    return source, dataset, splits


def _settled(row: pd.Series) -> int:
    family = "OU" if int(row["event_id"]) == 8 else "REZULTAT"
    return evaluate_football_outcome(SettlementCandidate(
        record_id=int(row["prediction_id"]),
        target="final_prediction",
        event_id=int(row["event_id"]),
        event_name=str(row["event_name"]),
        family=family,
        result=str(row["result"]),
        home_goals=int(row["home_team_goals"]),
        away_goals=int(row["away_team_goals"]),
        match_id=int(row["match_id"]),
        sport_id=1))


def test_labels_match_the_outcome_evaluator() -> None:
    frame, dataset, _splits = _prepared()
    for event_id in (1, 2, 8):
        position = frame.index[
            (frame["match_id"] == 6) & (frame["event_id"] == event_id)][0]
        assert dataset.labels.loc[position] == _settled(frame.loc[position])
    assert set(dataset.labels.tolist()) <= {0, 1}
    assert dataset.labels.name == "label"


def test_unfinished_invalid_and_unknown_rows_are_dropped() -> None:
    frame = _history()
    unknown = _row(
        prediction_id=900,
        odds_id=1900,
        match_id=12,
        event_id=999,
        kickoff=datetime(2026, 1, 12, 18, 0),
        event_name="mystery")
    frame = pd.concat([frame, pd.DataFrame([unknown])], ignore_index=True)
    dataset = build_betting_dataset(frame)
    kept_matches = set(dataset.match_id.tolist())
    assert 11 not in kept_matches
    assert 12 not in kept_matches
    invalid_price = frame.index[frame["odds"] == 1.0]
    assert invalid_price[0] not in dataset.features.index
    assert len(dataset.features) == 12


def test_features_do_not_contain_the_outcome() -> None:
    _frame, dataset, _splits = _prepared()
    columns = list(dataset.features.columns)
    assert columns == list(FEATURE_COLUMNS)
    assert set(columns).isdisjoint(POST_MATCH_DENYLIST)
    for name in ("result", "home_team_goals", "away_team_goals", "label"):
        assert name not in columns
    assert dataset.labels.index.equals(dataset.features.index)
    assert dataset.odds.index.equals(dataset.features.index)
    assert "odds" not in columns


def test_splits_keep_matches_disjoint_and_chronological() -> None:
    frame, dataset, splits = _prepared()
    assert [split.role for split in splits] == [
        "train",
        "calibration",
        "test"]
    assert [split.match_ids for split in splits] == [
        (1, 2, 3, 4, 5, 6),
        (7, 8),
        (9, 10)]
    match_sets = [set(split.match_ids) for split in splits]
    assert match_sets[0].isdisjoint(match_sets[1])
    assert match_sets[0].isdisjoint(match_sets[2])
    assert match_sets[1].isdisjoint(match_sets[2])
    assert splits[0].kickoff_to < splits[1].kickoff_from
    assert splits[1].kickoff_to < splits[2].kickoff_from
    assert splits[0].kickoff_from == datetime(2026, 1, 1, 18, 0)
    assert splits[2].kickoff_to == datetime(2026, 1, 10, 18, 0)
    match_six = frame.index[frame["match_id"] == 6]
    assert set(match_six) <= set(splits[0].row_labels)
    assert set(match_six).isdisjoint(splits[1].row_labels)
    assert set(match_six).isdisjoint(splits[2].row_labels)
    assert splits[0].row_count == 8
    assert splits[0].match_count == 6
    covered = dataset.match_id.loc[list(splits[0].row_labels)]
    assert set(covered.tolist()) == {1, 2, 3, 4, 5, 6}


def test_same_kickoff_stays_in_the_earlier_block() -> None:
    rows = []
    shared = datetime(2026, 1, 6, 12, 0)
    kickoffs = {
        1: datetime(2026, 1, 1, 18, 0),
        2: datetime(2026, 1, 2, 18, 0),
        3: datetime(2026, 1, 3, 18, 0),
        4: datetime(2026, 1, 4, 18, 0),
        5: datetime(2026, 1, 5, 18, 0),
        6: shared,
        7: shared,
        8: datetime(2026, 1, 8, 18, 0),
        9: datetime(2026, 1, 9, 18, 0),
        10: datetime(2026, 1, 10, 18, 0)}
    next_id = 1
    for match_id, kickoff in kickoffs.items():
        copies = 2 if match_id == 6 else 1
        for _copy in range(copies):
            rows.append(_row(
                prediction_id=next_id,
                odds_id=1000 + next_id,
                match_id=match_id,
                kickoff=kickoff))
            next_id += 1
    _frame, _dataset, splits = _prepared(pd.DataFrame(rows))
    assert [split.match_ids for split in splits] == [
        (1, 2, 3, 4, 5, 6, 7),
        (8,),
        (9, 10)]
    assert splits[0].kickoff_to < splits[1].kickoff_from
    assert splits[1].kickoff_to < splits[2].kickoff_from
    assert splits[0].kickoff_to == shared
    assert splits[0].row_count == 8
    assert splits[0].match_count == 7
    assert splits[1].kickoff_from > shared
    assert splits[2].kickoff_from > shared


def test_assignment_repeats_for_the_same_matches() -> None:
    _frame, dataset, splits = _prepared()
    again = build_walk_forward_splits(dataset.split_frame(), _config())
    other = build_walk_forward_splits(
        dataset.split_frame().sample(frac=1, random_state=7),
        _config(random_state=0))
    assert [split.match_ids for split in again] == [
        split.match_ids for split in splits]
    assert [split.match_ids for split in other] == [
        split.match_ids for split in splits]
    for left, right in zip(splits, other):
        assert set(left.row_labels) == set(right.row_labels)


def test_manifest_records_ranges_counts_and_fingerprint() -> None:
    _frame, dataset, splits = _prepared()
    manifest = build_dataset_manifest(dataset.features, splits)
    assert isinstance(manifest, DatasetManifest)
    assert manifest.feature_schema_fingerprint == (
        feature_schema_fingerprint(FEATURE_COLUMNS))
    assert len(manifest.feature_schema_fingerprint) == 64
    assert [split.match_count for split in manifest.splits] == [6, 2, 2]
    assert [split.row_count for split in manifest.splits] == [8, 2, 2]
    assert manifest.splits[0].kickoff_from == datetime(2026, 1, 1, 18, 0)
    assert manifest.splits[0].kickoff_to == datetime(2026, 1, 6, 18, 0)
    assert manifest.splits[1].kickoff_from == datetime(2026, 1, 7, 18, 0)
    assert manifest.splits[2].kickoff_to == datetime(2026, 1, 10, 18, 0)


def test_open_matches_leave_an_empty_matrix() -> None:
    frame = pd.DataFrame([
        _row(result="0", home_team_goals=None, away_team_goals=None),
        _row(
            prediction_id=11,
            odds_id=21,
            match_id=31,
            result=None,
            home_team_goals=None,
            away_team_goals=None)])
    dataset = build_betting_dataset(frame)
    assert dataset.features.empty
    assert list(dataset.features.columns) == list(FEATURE_COLUMNS)
    assert dataset.labels.empty
    with pytest.raises(ValueError, match="not enough matches"):
        build_walk_forward_splits(dataset.split_frame(), _config())


def test_too_few_matches_and_bad_inputs_raise() -> None:
    two = pd.DataFrame([
        _row(match_id=1, kickoff=datetime(2026, 1, 1)),
        _row(match_id=2, kickoff=datetime(2026, 1, 2), prediction_id=2)])
    with pytest.raises(ValueError, match="not enough matches"):
        build_walk_forward_splits(two, _config())
    three = pd.concat([
        two,
        pd.DataFrame([_row(
            match_id=3,
            kickoff=datetime(2026, 1, 3),
            prediction_id=3)])],
        ignore_index=True)
    with pytest.raises(ValueError, match="not enough matches"):
        build_walk_forward_splits(three, _config())
    shared = datetime(2026, 1, 3, 12, 0)
    tied = pd.DataFrame([
        _row(match_id=1, prediction_id=1, kickoff=datetime(2026, 1, 1)),
        _row(match_id=2, prediction_id=2, kickoff=datetime(2026, 1, 2)),
        _row(match_id=3, prediction_id=3, kickoff=shared),
        _row(match_id=4, prediction_id=4, kickoff=shared),
        _row(
            match_id=5,
            prediction_id=5,
            kickoff=datetime(2026, 1, 4))])
    with pytest.raises(ValueError, match="not enough matches"):
        build_walk_forward_splits(tied, _config())
    conflict = pd.DataFrame([
        _row(match_id=1, kickoff=datetime(2026, 1, 1)),
        _row(
            match_id=1,
            prediction_id=2,
            kickoff=datetime(2026, 1, 2))])
    with pytest.raises(ValueError, match="more than one kickoff"):
        build_walk_forward_splits(conflict, _config())
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mixed = pd.DataFrame([
        _row(match_id=1, kickoff=aware),
        _row(match_id=2, prediction_id=2, kickoff=datetime(2026, 1, 2))])
    with pytest.raises(ValueError, match="comparable"):
        build_walk_forward_splits(mixed, _config())
    with pytest.raises(ValueError, match="BettingTrainingConfig"):
        build_walk_forward_splits(two, object())
    with pytest.raises(ValueError, match="result"):
        build_betting_dataset(pd.DataFrame([_row()]).drop(columns=["result"]))
    with pytest.raises(ValueError, match="goals must be integers"):
        build_betting_dataset(pd.DataFrame([_row(home_team_goals=1.5)]))
    duplicated = pd.DataFrame([_row(), _row(prediction_id=11)])
    duplicated.index = [4, 4]
    with pytest.raises(ValueError, match="index must be unique"):
        build_betting_dataset(duplicated)
    with pytest.raises(ValueError, match="DataFrame"):
        build_betting_dataset([])


def test_manifest_rejects_a_leaking_or_unordered_split() -> None:
    _frame, dataset, splits = _prepared()
    leaked = TemporalSplit(
        role="calibration",
        match_ids=splits[0].match_ids[:1],
        row_labels=splits[1].row_labels,
        kickoff_from=splits[1].kickoff_from,
        kickoff_to=splits[1].kickoff_to,
        match_count=1,
        row_count=splits[1].row_count)
    with pytest.raises(ValueError, match="two splits"):
        build_dataset_manifest(
            dataset.features,
            (splits[0], leaked, splits[2]))
    reversed_test = TemporalSplit(
        role="test",
        match_ids=splits[2].match_ids,
        row_labels=splits[2].row_labels,
        kickoff_from=datetime(2026, 1, 1, 12, 0),
        kickoff_to=datetime(2026, 1, 1, 12, 0),
        match_count=splits[2].match_count,
        row_count=splits[2].row_count)
    with pytest.raises(ValueError, match="kickoff order"):
        build_dataset_manifest(
            dataset.features,
            (splits[0], splits[1], reversed_test))
    same_instant = TemporalSplit(
        role="calibration",
        match_ids=splits[1].match_ids,
        row_labels=splits[1].row_labels,
        kickoff_from=splits[0].kickoff_to,
        kickoff_to=splits[1].kickoff_to,
        match_count=splits[1].match_count,
        row_count=splits[1].row_count)
    with pytest.raises(ValueError, match="kickoff order"):
        build_dataset_manifest(
            dataset.features,
            (splits[0], same_instant, splits[2]))
    dirty = dataset.features.copy()
    dirty["label"] = 1
    with pytest.raises(ValueError, match="feature columns"):
        build_dataset_manifest(dirty, splits)


def test_module_does_not_write_to_the_database() -> None:
    source = inspect.getsource(dataset_module)
    assert "evaluate_football_outcome" in source
    for word in _WRITE_WORDS:
        assert word not in source
