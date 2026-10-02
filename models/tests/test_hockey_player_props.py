"""Skater props: line ice time, Poisson trees and seven rows per skater."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.cli import build_parser
from models.pipeline.core.registry import get_feature_builder
from models.pipeline.core.registry import get_labeler
from models.pipeline.core.registry import get_trainer
from models.pipeline.features.hockey.early_season import early_season_alpha
from models.pipeline.features.hockey.line_slots import DEFAULT_SLOT_MINUTES
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.player_features import (
    PLAYER_PROP_FEATURE_COLUMNS)
from models.pipeline.features.hockey.player_features import (
    build_hockey_player_features)
from models.pipeline.features.hockey.player_features import ewma_alpha
from models.pipeline.features.hockey.player_features import (
    prepare_player_prop_memory)
from models.pipeline.features.hockey.player_ratings import DEFAULT_SLOT_OFF
from models.pipeline.labels.hockey_player_props import LINES_PER_SKATER
from models.pipeline.labels.hockey_player_props import (
    poisson_over_probability)
from models.pipeline.prediction.hockey_player_props import rows_for_match
from models.pipeline.training.hockey_gbm_trainer import HockeyGbmSettings
from models.pipeline.training.hockey_player_props_trainer import (
    HockeyPlayerPropsModel)
from models.pipeline.training.hockey_player_props_trainer import (
    fit_player_prop_models)


def test_registry_loads_the_props_components() -> None:
    assert get_trainer("HockeyPlayerPropsTrainer").__class__.__name__ == (
        "HockeyPlayerPropsTrainer")
    assert get_feature_builder(
        "HockeyPlayerFeatureBuilder").__class__.__name__ == (
        "HockeyPlayerFeatureBuilder")
    assert get_labeler("HockeyPlayerPropsLabeler").__class__.__name__ == (
        "HockeyPlayerPropsLabeler")


def test_parser_accepts_predict_hockey_props_without_stage() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "predict-hockey-props",
        "--league-id",
        "45"])
    assert args.command == "predict-hockey-props"
    assert args.write_db is False
    assert not hasattr(args, "stage")


def test_first_game_uses_slot_priors_and_does_not_see_the_next_game() -> None:
    frame = build_hockey_player_features(
        _matches(), _rosters(), _stats(), _arenas())
    first = frame.loc[frame["match_id"] == 1].set_index("player_id")
    second = frame.loc[
        (frame["match_id"] == 2) & (frame["player_id"] == 10)].iloc[0]
    top = first.loc[10]
    bottom = first.loc[11]
    assert top["slot_toi"] == pytest.approx(DEFAULT_SLOT_MINUTES["F1"])
    assert bottom["slot_toi"] == pytest.approx(DEFAULT_SLOT_MINUTES["F4"])
    assert top["slot_toi"] > bottom["slot_toi"]
    assert top["off_rating"] == pytest.approx(DEFAULT_SLOT_OFF["F1"])
    assert bottom["off_rating"] == pytest.approx(DEFAULT_SLOT_OFF["F4"])
    assert np.isnan(top["goals_per_game_10"])
    assert second["goals_per_game_10"] == pytest.approx(1.0)
    assert top["is_home"] == pytest.approx(1.0)
    assert top["is_b2b"] == pytest.approx(0.0)
    assert second["is_b2b"] == pytest.approx(1.0)
    assert top["team_expected_goals"] == pytest.approx(3.0)
    assert top["opp_shots_allowed"] == pytest.approx(28.0)
    assert int(top["is_forward"]) == 1
    assert top["line_number"] == pytest.approx(1.0)
    assert bottom["line_number"] == pytest.approx(4.0)


def test_opening_games_boost_the_counting_ewma() -> None:
    frame = build_hockey_player_features(
        _opening_matches(), _opening_rosters(), _opening_stats(), _arenas())
    third = frame.loc[frame["match_id"] == 3].iloc[0]
    boosted = early_season_alpha(ewma_alpha(10), 1)
    assert third["goals_per_game_10"] == pytest.approx(boosted * 10.0)
    assert boosted > ewma_alpha(10)


def test_whole_number_line_is_rejected() -> None:
    with pytest.raises(ValueError, match="half-point"):
        poisson_over_probability(1.0, 2.0)


def test_point_rate_is_at_least_goals_plus_assists() -> None:
    row = {column: 0.0 for column in PLAYER_PROP_FEATURE_COLUMNS}
    model = HockeyPlayerPropsModel(
        models={
            "sog": _Fixed(1.0),
            "goals": _Fixed(0.8),
            "assists": _Fixed(0.6),
            "points": _Fixed(0.2)},
        feature_columns=list(PLAYER_PROP_FEATURE_COLUMNS))
    rates = model.predict_rates(pd.DataFrame([row]))
    assert float(rates["points"][0]) == pytest.approx(1.4)
    point = poisson_over_probability(float(rates["points"][0]), 0.5)
    assert point >= poisson_over_probability(float(rates["goals"][0]), 0.5)
    assert point >= poisson_over_probability(
        float(rates["assists"][0]), 0.5)


def test_larger_line_has_a_smaller_poisson_probability() -> None:
    rate = 2.4
    high = poisson_over_probability(rate, 1.5)
    middle = poisson_over_probability(rate, 2.5)
    low = poisson_over_probability(rate, 3.5)
    assert high > middle > low
    assert poisson_over_probability(rate, 0.5) > poisson_over_probability(
        rate, 1.5)


def test_higher_slot_toi_raises_the_shot_rate() -> None:
    frame = _toi_frame()
    settings = HockeyGbmSettings(
        learning_rate=0.2,
        max_iter=40,
        max_depth=2,
        min_samples_leaf=1,
        random_state=1)
    model = fit_player_prop_models(frame, settings)
    high = model.predict_rates(frame.iloc[[0]])["sog"][0]
    low = model.predict_rates(frame.iloc[[1]])["sog"][0]
    assert high > low
    assert poisson_over_probability(
        float(high), 2.5) > poisson_over_probability(float(low), 2.5)


def test_each_dressed_skater_gets_seven_rows_and_goalies_are_skipped() -> None:
    memory = prepare_player_prop_memory(
        _matches(), _rosters(), _stats(), _arenas())
    model = _ConstantModel()
    lineup = ProbableLineup(
        match_id=3,
        team_id=1,
        players=[
            _skater(10, "C", 1),
            _skater(11, "LW", 4),
            ProbableLineupPlayer(
                player_id=90,
                position="G",
                line=1,
                pp_unit=None,
                is_starting_goalie=1,
                confidence=1.0,
                source="MODEL",
                start_probability=0.7)])
    rows = rows_for_match(
        model,
        memory,
        3,
        1,
        2,
        datetime(2024, 10, 3, 18, 0),
        12,
        lineup,
        None,
        13,
        {
            "sog_over": 190,
            "points_over": 192,
            "assists_over": 194,
            "goals_over": 196})
    assert len(rows) == 2 * LINES_PER_SKATER
    assert {row.player_id for row in rows} == {10, 11}
    per_player = {
        player_id: sum(row.player_id == player_id for row in rows)
        for player_id in (10, 11)}
    assert per_player == {10: 7, 11: 7}


class _Fixed:
    """Regressor that ignores the matrix and returns one mean."""

    def __init__(self, value: float) -> None:
        self._value = value

    def predict(self, matrix: pd.DataFrame) -> np.ndarray:
        return np.full(len(matrix), self._value)


class _ConstantModel:
    """Stand-in that ignores features and returns fixed means."""

    def predict_rates(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        count = len(frame)
        return {
            "sog": np.full(count, 3.0),
            "goals": np.full(count, 0.4),
            "assists": np.full(count, 0.5),
            "points": np.full(count, 0.9)}


def _toi_frame() -> pd.DataFrame:
    rows = []
    for index in range(40):
        minutes = 20.0 if index % 2 == 0 else 10.0
        row = {column: 0.0 for column in PLAYER_PROP_FEATURE_COLUMNS}
        row["slot_toi"] = minutes
        row["sog"] = 4.0 if minutes == 20.0 else 1.0
        row["goals"] = 0.2
        row["assists"] = 0.2
        row["points"] = 0.4
        row["season"] = 1
        rows.append(row)
    return pd.DataFrame(rows)


def _skater(
        player_id: int,
        position: str,
        line: int) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position=position,
        line=line,
        pp_unit=1 if line == 1 else None,
        is_starting_goalie=None,
        confidence=0.8,
        source="MODEL")


def _matches() -> pd.DataFrame:
    rows = []
    for match_id, day, result, goals in (
            (1, 1, "1", 3),
            (2, 2, "2", 2),
            (3, 3, "0", None)):
        rows.append({
            "match_id": match_id,
            "season": 12,
            "home_team": 1,
            "away_team": 2,
            "game_date": datetime(2024, 10, day, 18, 0),
            "home_team_goals": goals,
            "away_team_goals": 1 if goals is not None else None,
            "result": result,
            "home_team_sog": 30,
            "away_team_sog": 25,
            "home_team_saves": 24,
            "away_team_saves": 27,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None,
            "so_winner": None})
    return pd.DataFrame(rows)


def _rosters() -> pd.DataFrame:
    rows = []
    for match_id, day in ((1, 1), (2, 2)):
        rows.append(_roster(match_id, day, 10, "C", 1))
        rows.append(_roster(match_id, day, 11, "LW", 4))
    return pd.DataFrame(rows)


def _roster(
        match_id: int,
        day: int,
        player_id: int,
        position: str,
        line: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": 1,
        "position": position,
        "line": line,
        "game_date": datetime(2024, 10, day, 18, 0),
        "season": 12}


def _stats() -> pd.DataFrame:
    rows = []
    for match_id, day, goals in ((1, 1, 1.0), (2, 2, 5.0)):
        rows.append(_stat(match_id, day, 10, goals, 4.0))
        rows.append(_stat(match_id, day, 11, 0.0, 1.0))
    return pd.DataFrame(rows)


def _stat(
        match_id: int,
        day: int,
        player_id: int,
        goals: float,
        shots: float) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": 1,
        "game_date": datetime(2024, 10, day, 18, 0),
        "season": 12,
        "goals": goals,
        "assists": 0.0,
        "points": goals,
        "sog": shots,
        "plus_minus": 0.0,
        "toi_seconds": 1200.0}


def _opening_matches() -> pd.DataFrame:
    rows = []
    for match_id, day in ((1, 1), (2, 2), (3, 4)):
        rows.append({
            "match_id": match_id,
            "season": 13,
            "home_team": 1,
            "away_team": 2,
            "game_date": datetime(2026, 10, day, 18, 0),
            "home_team_goals": 2,
            "away_team_goals": 1,
            "result": "1",
            "home_team_sog": 30,
            "away_team_sog": 25,
            "home_team_saves": 24,
            "away_team_saves": 28,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None,
            "so_winner": None})
    return pd.DataFrame(rows)


def _opening_rosters() -> pd.DataFrame:
    rows = []
    for match_id, day in ((1, 1), (2, 2), (3, 4)):
        rows.append({
            "match_id": match_id,
            "player_id": 10,
            "team_id": 1,
            "position": "C",
            "line": 1,
            "game_date": datetime(2026, 10, day, 18, 0),
            "season": 13})
    return pd.DataFrame(rows)


def _opening_stats() -> pd.DataFrame:
    goals = {1: 0.0, 2: 10.0, 3: 0.0}
    rows = []
    for match_id, day in ((1, 1), (2, 2), (3, 4)):
        rows.append({
            "match_id": match_id,
            "player_id": 10,
            "team_id": 1,
            "game_date": datetime(2026, 10, day, 18, 0),
            "season": 13,
            "goals": goals[match_id],
            "assists": 0.0,
            "points": goals[match_id],
            "sog": 1.0,
            "plus_minus": 0.0,
            "toi_seconds": 1200.0})
    return pd.DataFrame(rows)


def _arenas() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "team_id": 1,
            "latitude": 40.7,
            "longitude": -74.0,
            "timezone": "America/New_York"},
        {
            "team_id": 2,
            "latitude": 42.3,
            "longitude": -71.1,
            "timezone": "America/New_York"}])
