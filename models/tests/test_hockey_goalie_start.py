"""Goalie start features, the B2B effect and reported AUC."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from backend.config import REPO_ROOT
from models.pipeline.core.cli import run_train
from models.pipeline.core.config import TrainingReport
from models.pipeline.lineups.hockey_goalie_start import (
    DEFAULT_DAYS_SINCE_CAP)
from models.pipeline.lineups.hockey_goalie_start import (
    _holdout_probabilities)
from models.pipeline.lineups.hockey_goalie_start import (
    _season_weights)
from models.pipeline.lineups.hockey_goalie_start import (
    load_goalie_start_run)
from models.pipeline.lineups.hockey_goalie_start import GoalieStartConfig
from models.pipeline.lineups.hockey_goalie_start import GoalieStartHistory
from models.pipeline.lineups.hockey_goalie_start import GoalieStartModel
from models.pipeline.lineups.hockey_goalie_start import (
    build_goalie_start_frame)
from models.pipeline.lineups.hockey_goalie_start import (
    normalize_start_probabilities)
from models.pipeline.lineups.hockey_goalie_start import score_goalie_starts


def test_back_to_back_lowers_start_probability() -> None:
    matches, rosters = _rotation()
    frame = build_goalie_start_frame(matches, rosters)
    model = GoalieStartModel(GoalieStartConfig(random_state=0))
    model.fit(frame, frame["started"])
    probabilities = model.predict_proba(frame)
    primary = frame["player_id"] == 1
    rested = primary & (frame["is_b2b_second_game"] == 0)
    rested &= frame["started_yesterday"] == 0
    tired = primary & (frame["is_b2b_second_game"] == 1)
    tired &= frame["started_yesterday"] == 1
    assert int(tired.sum()) > 0
    assert int(rested.sum()) > 0
    tired_probability = float(probabilities[tired.to_numpy()].mean())
    rested_probability = float(probabilities[rested.to_numpy()].mean())
    assert tired_probability < rested_probability


def test_auc_is_reported_above_chance_on_the_rotation() -> None:
    matches, rosters = _rotation()
    frame = build_goalie_start_frame(matches, rosters)
    model = GoalieStartModel()
    model.fit(frame, frame["started"])
    metrics = score_goalie_starts(frame, model.predict_proba(frame))
    assert metrics["auc"] > 0.8
    assert metrics["starter_selection_accuracy_contested"] > 0.8


def test_first_game_does_not_see_later_starts() -> None:
    matches, rosters = _rotation()
    frame = build_goalie_start_frame(matches, rosters)
    first = frame.loc[frame["match_id"] == 1]
    assert len(first) == 1
    row = first.iloc[0]
    assert row["days_since_last_start"] == DEFAULT_DAYS_SINCE_CAP
    assert row["start_share_last_10"] == 0
    assert row["started_yesterday"] == 0
    assert row["is_b2b_second_game"] == 0


def test_back_to_back_marks_the_goalie_who_started_yesterday() -> None:
    matches, rosters = _rotation()
    frame = build_goalie_start_frame(matches, rosters)
    third = frame.loc[frame["match_id"] == 3]
    assert set(third["player_id"]) == {1, 2}
    backup = third.loc[third["player_id"] == 1].iloc[0]
    starter = third.loc[third["player_id"] == 2].iloc[0]
    assert int(backup["started"]) == 0
    assert backup["started_yesterday"] == 1
    assert backup["is_b2b_second_game"] == 1
    assert int(starter["started"]) == 1
    assert starter["is_b2b_second_game"] == 1


def test_closed_slate_cannot_be_read_again() -> None:
    history = GoalieStartHistory()
    moment = datetime(2024, 10, 1)
    history.observe(7, 1, moment)
    with pytest.raises(ValueError, match="observed"):
        history.feature_row(7, 1, moment, 1500.0)


def test_history_cannot_move_backwards() -> None:
    history = GoalieStartHistory()
    history.observe(7, 1, datetime(2024, 10, 3))
    with pytest.raises(ValueError, match="backwards"):
        history.observe(7, 1, datetime(2024, 10, 1))


def test_pool_drops_a_starter_outside_the_window() -> None:
    config = GoalieStartConfig(pool_games=2, start_share_games=2)
    matches, rosters = _sequence([3, 1, 1, 2], gap_days=2)
    frame = build_goalie_start_frame(matches, rosters, config)
    last = frame.loc[frame["match_id"] == 4]
    assert set(last["player_id"]) == {1, 2}
    share = last.loc[last["player_id"] == 1, "start_share_last_10"]
    assert float(share.iloc[0]) == pytest.approx(1.0)


def test_ten_straight_starts_have_full_share() -> None:
    matches, rosters = _sequence([1] * 11, gap_days=2)
    frame = build_goalie_start_frame(matches, rosters)
    last = frame.loc[frame["match_id"] == 11].iloc[0]
    assert last["start_share_last_10"] == pytest.approx(1.0)
    assert last["is_b2b_second_game"] == 0
    assert last["days_since_last_start"] == 2


def test_dressed_backup_is_not_labelled_as_the_starter() -> None:
    matches, rosters = _rotation()
    extra = pd.DataFrame([{
        "id": 900,
        "match_id": 5,
        "team_id": 7,
        "player_id": 5,
        "position": "G",
        "line": 2}])
    rosters = pd.concat([rosters, extra], ignore_index=True)
    frame = build_goalie_start_frame(matches, rosters)
    assert 5 not in set(frame.loc[frame["match_id"] == 5, "player_id"])


def test_duplicate_starter_row_keeps_the_lowest_id() -> None:
    matches, rosters = _sequence([1], gap_days=2)
    rosters["id"] = 2
    duplicate = pd.DataFrame([{
        "id": 1,
        "match_id": 1,
        "team_id": 7,
        "player_id": 8,
        "position": "G",
        "line": "1"}])
    rosters = pd.concat([rosters, duplicate], ignore_index=True)
    frame = build_goalie_start_frame(matches, rosters)
    assert int(frame.iloc[0]["player_id"]) == 8
    assert int(frame.iloc[0]["started"]) == 1


def test_opponent_elo_is_the_other_team_pre_match_rating() -> None:
    matches, rosters = _sequence([1, 1], gap_days=2)
    ratings = pd.DataFrame({
        "match_id": [1, 2],
        "home_team": [7, 7],
        "away_team": [99, 99],
        "home_elo": [1500.0, 1510.0],
        "away_elo": [1600.0, 1400.0]})
    frame = build_goalie_start_frame(matches, rosters, ratings=ratings)
    first = frame.loc[frame["match_id"] == 1].iloc[0]
    second = frame.loc[frame["match_id"] == 2].iloc[0]
    assert first["opponent_elo"] == pytest.approx(1600.0)
    assert second["opponent_elo"] == pytest.approx(1400.0)


def test_contested_accuracy_skips_a_single_candidate() -> None:
    frame = pd.DataFrame({
        "match_id": [1, 1, 2],
        "team_id": [7, 7, 7],
        "player_id": [1, 2, 1],
        "started": [0, 1, 1]})
    probabilities = np.array([0.9, 0.2, 0.7])
    metrics = score_goalie_starts(frame, probabilities)
    assert metrics["starter_selection_accuracy"] == pytest.approx(0.5)
    assert metrics["starter_selection_accuracy_contested"] == 0
    assert metrics["n_team_games"] == 2
    assert metrics["n_contested_team_games"] == 1
    assert 0.0 <= metrics["auc"] <= 1.0


def test_same_utc_day_second_game_counts_as_back_to_back() -> None:
    matches, rosters = _same_day_pair()
    frame = build_goalie_start_frame(matches, rosters)
    opening = frame.loc[frame["match_id"] == 1].iloc[0]
    follow_up = frame.loc[frame["match_id"] == 2]
    starter = follow_up.loc[follow_up["player_id"] == 1].iloc[0]
    fresh = follow_up.loc[follow_up["player_id"] == 2].iloc[0]
    assert opening["is_b2b_second_game"] == 0
    assert opening["started_yesterday"] == 0
    assert int(starter["started"]) == 0
    assert starter["is_b2b_second_game"] == 1
    assert starter["started_yesterday"] == 1
    assert starter["days_since_last_start"] >= 1
    assert starter["starts_last_4_days"] >= 1
    assert int(fresh["started"]) == 1
    assert fresh["is_b2b_second_game"] == 1
    assert fresh["started_yesterday"] == 0


def test_normalized_weights_sum_to_one_inside_a_team_game() -> None:
    frame = pd.DataFrame({
        "match_id": [1, 1, 2],
        "team_id": [7, 7, 7]})
    raw = np.array([0.7, 0.7, 0.0])
    weights = normalize_start_probabilities(frame, raw)
    assert weights[0] == pytest.approx(0.5)
    assert weights[1] == pytest.approx(0.5)
    assert weights[2] == pytest.approx(1.0)
    assert raw[0] == pytest.approx(0.7)
    zeros = normalize_start_probabilities(
        frame.iloc[:2], np.array([0.0, 0.0]))
    assert zeros[0] == pytest.approx(0.5)
    assert zeros[1] == pytest.approx(0.5)


def test_later_season_does_not_change_holdout_probabilities() -> None:
    frame = _dated_holdout_frame()
    config = GoalieStartConfig(test_season=12, random_state=0)
    test_rows, with_future, n_with = _holdout_probabilities(frame, config)
    earlier = frame.loc[frame["season"] != 13]
    _same_rows, without_future, n_without = _holdout_probabilities(
        earlier, config)
    assert n_with == n_without
    assert n_with < int((frame["season"] != 12).sum())
    assert np.allclose(with_future, without_future)
    leaked = GoalieStartModel(config)
    leaked_rows = frame.loc[frame["season"] != 12]
    leaked.fit(leaked_rows, leaked_rows["started"])
    changed = leaked.predict_proba(test_rows)
    assert not np.allclose(changed, with_future, atol=1e-6)


def test_shortened_season_weighs_half_as_much() -> None:
    frame = _balanced_label_frame()
    probe = frame.iloc[[0]]
    halved = GoalieStartModel(GoalieStartConfig(random_state=0))
    halved.fit(
        frame,
        frame["started"],
        sample_weight=_weights(frame, {4: 0.5}))
    even = GoalieStartModel(GoalieStartConfig(
        random_state=0,
        low_weight_seasons={}))
    even.fit(frame, frame["started"])
    assert float(halved.predict_proba(probe)[0]) > float(
        even.predict_proba(probe)[0])


def test_training_config_halves_the_2020_season() -> None:
    path = (
        REPO_ROOT / "models" / "configs" / "training"
        / "hockey_goalie_start_v1.json")
    run = load_goalie_start_run(path)
    assert run.config.low_weight_seasons[4] == pytest.approx(0.5)


def test_pool_games_must_be_positive() -> None:
    with pytest.raises(ValueError, match="pool_games"):
        GoalieStartConfig(pool_games=0)


def test_train_command_dispatches_the_goalie_config(tmp_path: Path) -> None:
    config = tmp_path / "goalie.json"
    config.write_text(
        '{"task_type": "goalie_start", "model_name": "X"}',
        encoding="utf-8")
    report = TrainingReport(
        model_name="HOCKEY_GOALIE_START_V1",
        model_version="1.0.0",
        artifact_dir="artifact")
    with patch(
            "models.pipeline.core.cli.train_goalie_start",
            return_value=report) as trained:
        payload = run_train(config)
    trained.assert_called_once_with(config)
    assert payload["model_name"] == "HOCKEY_GOALIE_START_V1"


def _dated_holdout_frame() -> pd.DataFrame:
    rows = []
    for index in range(24):
        yesterday = index % 2
        rows.append(_feature_row(
            index + 1,
            11,
            datetime(2025, 9, 1) + timedelta(days=index % 20),
            started=0 if yesterday else 1,
            started_yesterday=yesterday))
    for index in range(8):
        yesterday = index % 2
        rows.append(_feature_row(
            100 + index,
            12,
            datetime(2025, 10, 5) + timedelta(days=index),
            started=0 if yesterday else 1,
            started_yesterday=yesterday))
    for index in range(40):
        yesterday = index % 2
        rows.append(_feature_row(
            200 + index,
            13,
            datetime(2026, 10, 5) + timedelta(days=index),
            started=1 if yesterday else 0,
            started_yesterday=yesterday))
    return pd.DataFrame(rows)


def _balanced_label_frame() -> pd.DataFrame:
    rows = []
    for index in range(20):
        rows.append(_feature_row(
            index + 1,
            11,
            datetime(2024, 10, 1) + timedelta(days=index),
            started=1,
            started_yesterday=0))
        rows.append(_feature_row(
            100 + index,
            4,
            datetime(2021, 1, 15) + timedelta(days=index),
            started=0,
            started_yesterday=0))
    return pd.DataFrame(rows)


def _feature_row(
        match_id: int,
        season: int,
        when: datetime,
        started: int,
        started_yesterday: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "team_id": 7,
        "player_id": 1,
        "game_date": when,
        "season": season,
        "started": started,
        "start_share_last_10": 0.5,
        "started_yesterday": float(started_yesterday),
        "days_since_last_start": 2.0,
        "starts_last_4_days": 1.0,
        "is_b2b_second_game": float(started_yesterday),
        "opponent_elo": 1500.0}


def _weights(
        frame: pd.DataFrame,
        seasons: dict[int, float]) -> np.ndarray:
    config = GoalieStartConfig(low_weight_seasons=seasons)
    return _season_weights(frame, config)


def _same_day_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Minnesota, 26.10.2025: 00:00 i 23:00 UTC to dwa wieczory lokalnie.
    opening = datetime(2025, 10, 26, 0, 0)
    follow_up = datetime(2025, 10, 26, 23, 0)
    matches = pd.DataFrame([
        {
            "match_id": 1,
            "game_date": opening,
            "season": 12,
            "home_team": 7,
            "away_team": 99},
        {
            "match_id": 2,
            "game_date": follow_up,
            "season": 12,
            "home_team": 7,
            "away_team": 99}])
    rosters = pd.DataFrame([
        {
            "id": 1,
            "match_id": 1,
            "team_id": 7,
            "player_id": 1,
            "position": "G",
            "line": 1},
        {
            "id": 2,
            "match_id": 2,
            "team_id": 7,
            "player_id": 2,
            "position": "G",
            "line": 1}])
    return matches, rosters


def _rotation() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Dwa starty bramkarza 1, potem drugi mecz z rzędu dla bramkarza 2.
    return _sequence_pattern(((1, 2), (1, 1), (2, 2)), cycles=16)


def _sequence_pattern(
        pattern: tuple[tuple[int, int], ...],
        cycles: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    start = datetime(2024, 10, 1)
    matches = []
    rosters = []
    day = 0
    match_id = 1
    for _cycle in range(cycles):
        for starter, gap_after in pattern:
            _append_game(
                matches, rosters, match_id, start, day, starter)
            match_id += 1
            day += gap_after
    return pd.DataFrame(matches), pd.DataFrame(rosters)


def _sequence(
        starters: list[int],
        gap_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    pattern = tuple((starter, gap_days) for starter in starters)
    return _sequence_pattern(pattern, cycles=1)


def _append_game(
        matches: list[dict[str, object]],
        rosters: list[dict[str, object]],
        match_id: int,
        start: datetime,
        day: int,
        starter: int) -> None:
    matches.append({
        "match_id": match_id,
        "game_date": start + timedelta(days=day),
        "season": 11,
        "home_team": 7,
        "away_team": 99})
    rosters.append({
        "id": match_id,
        "match_id": match_id,
        "team_id": 7,
        "player_id": starter,
        "position": "G",
        "line": 1})
