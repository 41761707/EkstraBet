"""NHL GBM features, no future leakage, and holdout market metrics."""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from models.pipeline.core.registry import get_feature_builder
from models.pipeline.core.registry import get_trainer
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.team_features import (
    HOCKEY_GBM_FEATURE_COLUMNS)
from models.pipeline.features.hockey.team_features import (
    build_hockey_team_features)
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.training.hockey_gbm_trainer import HockeyGbmSettings
from models.pipeline.training.hockey_gbm_trainer import fit_hockey_gbm
from models.pipeline.training.hockey_gbm_trainer import score_gbm_holdout
from models.pipeline.training.hockey_ratings_trainer import (
    HockeyDixonColesParams)


DAY = datetime(2024, 10, 1)


def test_later_result_does_not_change_earlier_features() -> None:
    original = _matches()
    changed = original.copy()
    changed.loc[changed["match_id"] == 3, "home_team_goals"] = 9
    changed.loc[changed["match_id"] == 3, "away_team_goals"] = 0
    before = build_hockey_team_features(
        original, _arenas(), _empty_rosters(), _empty_stats())
    after = build_hockey_team_features(
        changed, _arenas(), _empty_rosters(), _empty_stats())
    early = HOCKEY_GBM_FEATURE_COLUMNS
    first = before.loc[before["match_id"] == 1, early].reset_index(drop=True)
    second = after.loc[after["match_id"] == 1, early].reset_index(drop=True)
    pd.testing.assert_frame_equal(first, second)
    kept = before.loc[before["match_id"] == 2, early].reset_index(drop=True)
    shifted = after.loc[after["match_id"] == 2, early].reset_index(drop=True)
    pd.testing.assert_frame_equal(kept, shifted)


def test_same_slate_does_not_leak_between_matches() -> None:
    frame = _matches()
    # Dwa mecze o tej samej godzinie nie widzą swoich bramek.
    frame.loc[frame["match_id"] == 2, "game_date"] = DAY + timedelta(days=1)
    features = build_hockey_team_features(
        frame, _arenas(), _empty_rosters(), _empty_stats())
    opening = features.loc[features["match_id"].isin([1, 2])]
    assert set(opening["elo_diff"].tolist()) == {0.0}
    assert set(opening["home_season_game_index"].tolist()) == {0.0}


def test_next_game_sees_the_previous_result() -> None:
    low = build_hockey_team_features(
        _matches(), _arenas(), _empty_rosters(), _empty_stats())
    blown = _matches()
    blown.loc[blown["match_id"] == 1, "home_team_goals"] = 8
    high = build_hockey_team_features(
        blown, _arenas(), _empty_rosters(), _empty_stats())
    low_third = float(low.loc[low["match_id"] == 3, "home_elo"].iloc[0])
    high_third = float(high.loc[high["match_id"] == 3, "home_elo"].iloc[0])
    assert high_third != low_third
    early = float(
        low.loc[low["match_id"] == 1, "home_early_form_goals_per_60"].iloc[0])
    assert early == 0.0


def test_later_box_score_does_not_leak_into_lineup_or_goalie() -> None:
    quiet = _box_features(0, 10, 0, 10)
    later = _box_features(0, 10, 6, 19)
    earlier = _box_features(5, 19, 0, 10)
    for match_id in (1, 2):
        pd.testing.assert_frame_equal(
            _box_slice(quiet, match_id),
            _box_slice(later, match_id))
    pd.testing.assert_frame_equal(
        _box_slice(quiet, 1), _box_slice(earlier, 1))
    for column in ("home_lineup_off", "home_goalie_save_pct"):
        assert _box_value(quiet, 2, column) != _box_value(earlier, 2, column)
    # Pusty skład zostawiłby te kolumny stałe i nic by nie ujawnił.
    assert _box_value(quiet, 1, "home_lineup_off") != _box_value(
        quiet, 2, "home_lineup_off")
    assert _box_value(quiet, 1, "home_goalie_save_pct") != _box_value(
        quiet, 2, "home_goalie_save_pct")


def test_early_form_off_uses_the_season_to_date() -> None:
    quiet = _rollover_features(0)
    busier = _rollover_features(5)
    ending_off = _box_value(quiet, 1, "home_lineup_off")
    opener_off = _box_value(quiet, 2, "home_lineup_off")
    third_off = _box_value(quiet, 3, "home_lineup_off")
    assert _box_value(quiet, 1, "home_early_form_off") == 0.0
    assert _box_value(quiet, 2, "home_early_form_off") == 0.0
    assert _box_value(quiet, 3, "home_early_form_off") == pytest.approx(
        opener_off - ending_off)
    assert _box_value(quiet, 3, "home_early_form_off") != pytest.approx(
        third_off - ending_off)
    assert _box_value(quiet, 2, "home_early_form_off") == _box_value(
        busier, 2, "home_early_form_off")
    assert _box_value(quiet, 3, "home_early_form_off") != _box_value(
        busier, 3, "home_early_form_off")


def test_confirmed_goalie_keeps_his_shrunk_save_rate() -> None:
    starter = _projected_save(False, "CONFIRMED", 0.9)
    with_backup = _projected_save(True, "CONFIRMED", 0.9, 0.4)
    blended = _projected_save(True, "MODEL", 0.9, 0.4)
    share_only = _projected_save(True, "MODEL", 0.9, None)
    marked = _projected_save(False, "MODEL", None)
    assert with_backup == pytest.approx(starter)
    assert marked == pytest.approx(starter)
    assert share_only == pytest.approx(starter)
    assert blended != pytest.approx(starter)


def test_projected_lineup_replaces_the_historical_ratio() -> None:
    features = build_hockey_team_features(
        _matches(),
        _arenas(),
        _empty_rosters(),
        _empty_stats(),
        projected={3: (_skater_lineup(3, 1), None)})
    row = features.loc[features["match_id"] == 3].iloc[0]
    typical = features.loc[features["match_id"] == 1].iloc[0]
    # Brak składu dostaje typowe sloty i ratio 1, nie NaN.
    assert pd.notna(row["home_lineup_off"])
    assert row["away_lineup_off"] == pytest.approx(typical["away_lineup_off"])
    assert row["away_lineup_shots"] == pytest.approx(
        typical["away_lineup_shots"])
    assert row["away_lineup_def"] == pytest.approx(typical["away_lineup_def"])
    assert row["away_top6_f_off"] == pytest.approx(typical["away_top6_f_off"])
    assert row["away_lineup_off_ratio"] == pytest.approx(1.0)
    assert row["home_lineup_off"] != pytest.approx(row["away_lineup_off"])
    assert row["is_playoff"] == 0.0


def test_holdout_markets_are_complementary() -> None:
    frame = _training_frame()
    params = HockeyDixonColesParams(
        test_season=2,
        validation_days=10,
        tie_inflation_step=0.2,
        max_goals=8)
    settings = HockeyGbmSettings(
        max_iter=20,
        min_samples_leaf=5,
        max_depth=3)
    metrics = score_gbm_holdout(
        frame, HOCKEY_GBM_FEATURE_COLUMNS, settings, params)
    assert metrics["n_scored"] > 0
    assert metrics["moneyline_log_loss"] > 0.0
    assert "over_55_log_loss" in metrics
    assert "puck_line_home_minus_15_log_loss" in metrics
    assert metrics["score_matrix_rps"] > 0.0
    assert metrics["score_matrix_rps"] != pytest.approx(
        metrics["moneyline_brier"])
    model = fit_hockey_gbm(
        frame.loc[frame["goals_home"].notna()],
        HOCKEY_GBM_FEATURE_COLUMNS,
        settings,
        params,
        pd.Timestamp(frame["game_date"].max()) + pd.Timedelta(days=1))
    markets = derive_hockey_markets(
        model.score_distribution(frame.iloc[0]))
    assert markets["ml_home"] + markets["ml_away"] == pytest.approx(100.0)
    assert markets["over_55"] + markets["under_55"] == pytest.approx(100.0)
    assert 1.0 <= model.tie_inflation <= 1.8


def test_trees_exclude_the_validation_window(monkeypatch) -> None:
    from models.pipeline.training import hockey_gbm_trainer as trainer

    seen: list[int] = []
    real = trainer._fit_poisson

    def _spy(matrix, target, weights, settings):
        seen.append(len(matrix))
        return real(matrix, target, weights, settings)

    monkeypatch.setattr(trainer, "_fit_poisson", _spy)
    frame = _training_frame()
    finished = frame.loc[frame["goals_home"].notna()].copy()
    finished["game_date"] = pd.to_datetime(finished["game_date"])
    params = HockeyDixonColesParams(
        test_season=2,
        validation_days=10,
        tie_inflation_step=0.2,
        max_goals=8)
    settings = HockeyGbmSettings(
        max_iter=5,
        min_samples_leaf=5,
        max_depth=2)
    as_of = pd.Timestamp(
        finished.loc[finished["season"] == 2, "game_date"].min())
    prior = finished.loc[finished["game_date"] < as_of]
    fit_hockey_gbm(
        finished, HOCKEY_GBM_FEATURE_COLUMNS, settings, params, as_of)
    assert seen
    assert seen[0] == seen[1]
    assert seen[0] < len(prior)


def test_score_matrix_rps_is_zero_on_the_actual_score() -> None:
    from models.pipeline.prediction.hockey_markets import (
        build_score_distribution)
    from models.pipeline.training.hockey_gbm_trainer import _matrix_rps

    distribution = build_score_distribution(2.8, 2.4, 1.1, 0.52, 8)
    perfect = np.zeros_like(distribution.final_matrix)
    perfect[3, 2] = 1.0
    assert _matrix_rps(perfect, 3, 2) == pytest.approx(0.0)
    assert _matrix_rps(distribution.final_matrix, 3, 2) > 0.0


def test_activation_uses_the_single_preseason_fit(
        tmp_path, monkeypatch) -> None:
    from models.pipeline.training import hockey_gbm_trainer as trainer

    published = 0.6879
    single_fit = 0.6972
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({
        "moneyline_log_loss": published,
        "refit_count": 34,
        "single_fit_moneyline_log_loss": single_fit}), encoding="utf-8")
    monkeypatch.setattr(trainer, "_BASELINE_METRICS", metrics)
    better = trainer._baseline_comparison(0.6906)
    worse = trainer._baseline_comparison(single_fit + 0.0004)
    assert better["recommended_active"] == 1
    assert better["beats_baseline_moneyline"] is True
    assert better["comparison_protocol"] == "single_preseason_fit"
    assert better["baseline_single_fit_moneyline_log_loss"] == single_fit
    assert better["baseline_walk_forward_moneyline_log_loss"] == published
    assert worse["recommended_active"] == 0
    assert worse["beats_baseline_moneyline"] is False
    walk_only = tmp_path / "walk.json"
    walk_only.write_text(json.dumps({
        "moneyline_log_loss": 0.99,
        "refit_count": 34}), encoding="utf-8")
    monkeypatch.setattr(trainer, "_BASELINE_METRICS", walk_only)
    unmatched = trainer._baseline_comparison(0.5)
    assert unmatched["recommended_active"] == 0
    assert unmatched["beats_baseline_moneyline"] is None
    assert unmatched["baseline_walk_forward_moneyline_log_loss"] == 0.99


def test_registry_names() -> None:
    assert get_feature_builder("HockeyTeamFeatureBuilder").__class__.__name__
    assert get_trainer("HockeyGbmTrainer").__class__.__name__ == (
        "HockeyGbmTrainer")


def _matches() -> pd.DataFrame:
    rows = []
    for index, (home, away, goals_home, goals_away) in enumerate((
            (1, 2, 2, 1),
            (2, 1, 1, 3),
            (1, 2, 4, 2)), start=1):
        rows.append({
            "match_id": index,
            "season": 1,
            "home_team": home,
            "away_team": away,
            "game_date": DAY + timedelta(days=index),
            "round": 1,
            "result": "1" if goals_home > goals_away else "2",
            "home_team_goals": goals_home,
            "away_team_goals": goals_away,
            "home_team_sog": 30,
            "away_team_sog": 25,
            "home_team_saves": 24,
            "away_team_saves": 28,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None,
            "so_winner": None})
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


def _empty_rosters() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "match_id",
        "player_id",
        "team_id",
        "position",
        "line",
        "game_date",
        "season"])


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "match_id",
        "player_id",
        "team_id",
        "points",
        "sog",
        "plus_minus",
        "toi_seconds",
        "shots_against",
        "shots_saved"])


_BOX_COLUMNS = [
    "home_lineup_off",
    "home_goalie_save_pct",
    "home_early_form_off"]


def _box_features(
        points: int,
        saves: int,
        later_points: int,
        later_saves: int) -> pd.DataFrame:
    return build_hockey_team_features(
        _box_matches(),
        _arenas(),
        _box_rosters(),
        _box_stats(points, saves, later_points, later_saves))


def _rollover_features(points: int) -> pd.DataFrame:
    return build_hockey_team_features(
        _rollover_matches(),
        _arenas(),
        _rollover_rosters(),
        _rollover_stats(points))


def _rollover_matches() -> pd.DataFrame:
    rows = []
    schedule = (
        (1, 1, DAY + timedelta(days=1), 2, 1),
        (2, 2, DAY + timedelta(days=40), 3, 1),
        (3, 2, DAY + timedelta(days=41), 4, 2))
    for match_id, season, moment, goals_home, goals_away in schedule:
        rows.append({
            "match_id": match_id,
            "season": season,
            "home_team": 1,
            "away_team": 2,
            "game_date": moment,
            "round": 1,
            "result": "1",
            "home_team_goals": goals_home,
            "away_team_goals": goals_away,
            "home_team_sog": 30,
            "away_team_sog": 25,
            "home_team_saves": 24,
            "away_team_saves": 28,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None,
            "so_winner": None})
    return pd.DataFrame(rows)


def _rollover_rosters() -> pd.DataFrame:
    rows = []
    for match_id, season, moment in (
            (1, 1, DAY + timedelta(days=1)),
            (2, 2, DAY + timedelta(days=40)),
            (3, 2, DAY + timedelta(days=41))):
        rows.append({
            "match_id": match_id,
            "player_id": 10,
            "team_id": 1,
            "position": "C",
            "line": 1,
            "game_date": moment,
            "season": season})
    return pd.DataFrame(rows)


def _rollover_stats(points: int) -> pd.DataFrame:
    rows = []
    for match_id, moment, skater_points in (
            (1, DAY + timedelta(days=1), points),
            (2, DAY + timedelta(days=40), 1),
            (3, DAY + timedelta(days=41), 1)):
        rows.append({
            "match_id": match_id,
            "player_id": 10,
            "team_id": 1,
            "game_date": moment,
            "points": skater_points,
            "sog": 3,
            "plus_minus": 0,
            "toi_seconds": 1200})
    return pd.DataFrame(rows)


def test_same_slate_team_save_ignores_the_other_game() -> None:
    features = _same_day_save_features()
    carried = _box_value(features, 1, "home_goalie_save_pct")
    assert _box_value(features, 2, "home_team_save_pct") == pytest.approx(
        carried)
    assert _box_value(features, 3, "home_team_save_pct") == pytest.approx(
        carried)


def _same_day_save_features() -> pd.DataFrame:
    second = DAY + timedelta(days=2)
    matches = _box_matches()
    matches.loc[matches["match_id"] == 2, "game_date"] = second
    matches.loc[matches["match_id"] == 3, "game_date"] = second
    rosters = _box_rosters()
    rosters.loc[rosters["match_id"] == 2, "game_date"] = second
    rosters.loc[rosters["match_id"] == 3, "game_date"] = second
    stats = _box_stats(0, 10, 19, 12)
    stats.loc[stats["match_id"] == 2, "game_date"] = second
    stats.loc[stats["match_id"] == 3, "game_date"] = second
    return build_hockey_team_features(
        matches, _arenas(), rosters, stats)


def _box_matches() -> pd.DataFrame:
    rows = []
    for match_id, goals_home, goals_away in ((1, 2, 1), (2, 3, 1), (3, 4, 2)):
        rows.append({
            "match_id": match_id,
            "season": 1,
            "home_team": 1,
            "away_team": 2,
            "game_date": DAY + timedelta(days=match_id),
            "round": 1,
            "result": "1",
            "home_team_goals": goals_home,
            "away_team_goals": goals_away,
            "home_team_sog": 30,
            "away_team_sog": 25,
            "home_team_saves": 24,
            "away_team_saves": 28,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None,
            "so_winner": None})
    return pd.DataFrame(rows)


def _box_slice(frame: pd.DataFrame, match_id: int) -> pd.DataFrame:
    return frame.loc[
        frame["match_id"] == match_id, _BOX_COLUMNS].reset_index(drop=True)


def _box_value(frame: pd.DataFrame, match_id: int, column: str) -> float:
    return float(frame.loc[frame["match_id"] == match_id, column].iloc[0])


def _box_rosters() -> pd.DataFrame:
    rows = []
    for match_id in (1, 2, 3):
        moment = DAY + timedelta(days=match_id)
        rows.append(_roster_row(match_id, 10, 1, "C", 1, moment))
        rows.append(_roster_row(match_id, 20, 1, "G", 1, moment))
    return pd.DataFrame(rows)


def _roster_row(
        match_id: int,
        player_id: int,
        team_id: int,
        position: str,
        line: int,
        moment: datetime) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "position": position,
        "line": line,
        "game_date": moment,
        "season": 1}


def _box_stats(
        points: int,
        saves: int,
        later_points: int,
        later_saves: int) -> pd.DataFrame:
    rows = []
    for match_id, skater_points, goalie_saves in (
            (1, points, saves),
            (2, 1, 15),
            (3, later_points, later_saves)):
        moment = DAY + timedelta(days=match_id)
        rows.append({
            "match_id": match_id,
            "player_id": 10,
            "team_id": 1,
            "game_date": moment,
            "points": skater_points,
            "sog": 3,
            "plus_minus": 0,
            "toi_seconds": 1200,
            "shots_against": 0,
            "shots_saved": 0})
        rows.append({
            "match_id": match_id,
            "player_id": 20,
            "team_id": 1,
            "game_date": moment,
            "points": 0,
            "sog": 0,
            "plus_minus": 0,
            "toi_seconds": 3600,
            "shots_against": 20,
            "shots_saved": goalie_saves})
    return pd.DataFrame(rows)


def _projected_save(
        include_backup: bool,
        source: str,
        confidence: float | None,
        backup_start: float | None = None) -> float:
    lineup = _goalie_lineup(
        include_backup, source, confidence, backup_start)
    features = build_hockey_team_features(
        _goalie_projection_matches(),
        _arenas(),
        _empty_rosters(),
        _two_goalie_appearances(),
        projected={2: (lineup, None)})
    return float(features.loc[
        features["match_id"] == 2, "home_goalie_save_pct"].iloc[0])


def _goalie_projection_matches() -> pd.DataFrame:
    played = _matches().iloc[[0]].copy()
    upcoming = played.copy()
    upcoming["match_id"] = 2
    upcoming["game_date"] = DAY + timedelta(days=10)
    upcoming["result"] = "0"
    for column in (
            "home_team_goals",
            "away_team_goals",
            "home_team_sog",
            "away_team_sog",
            "home_team_saves",
            "away_team_saves"):
        upcoming[column] = pd.NA
    return pd.concat([played, upcoming], ignore_index=True)


def _two_goalie_appearances() -> pd.DataFrame:
    moment = DAY + timedelta(days=1)
    return pd.DataFrame([
        _goalie_appearance(101, moment, 95),
        _goalie_appearance(102, moment, 80)])


def _goalie_appearance(
        player_id: int,
        moment: datetime,
        saves: int) -> dict[str, object]:
    return {
        "match_id": 1,
        "player_id": player_id,
        "team_id": 1,
        "game_date": moment,
        "shots_against": 100,
        "shots_saved": saves,
        "toi_seconds": 3600}


def _goalie_lineup(
        include_backup: bool,
        source: str,
        confidence: float | None,
        backup_start: float | None) -> ProbableLineup:
    starter_start = None
    if source == "MODEL" and backup_start is not None:
        starter_start = 0.9
    players = [
        _goalie_player(101, 1, confidence, source, starter_start),
        ProbableLineupPlayer(
            player_id=10,
            position="C",
            line=1,
            pp_unit=None,
            is_starting_goalie=0,
            confidence=1.0,
            source=source)]
    if include_backup:
        players.append(_goalie_player(102, 0, 0.4, source, backup_start))
    return ProbableLineup(match_id=2, team_id=1, players=players)


def _goalie_player(
        player_id: int,
        starter: int,
        confidence: float | None,
        source: str,
        start_probability: float | None) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="G",
        line=1,
        pp_unit=None,
        is_starting_goalie=starter,
        confidence=confidence,
        source=source,
        start_probability=start_probability)


def _skater_lineup(match_id: int, team_id: int) -> ProbableLineup:
    return ProbableLineup(
        match_id=match_id,
        team_id=team_id,
        players=[ProbableLineupPlayer(
            player_id=10,
            position="C",
            line=1,
            pp_unit=None,
            is_starting_goalie=0,
            confidence=1.0,
            source="MODEL")])


def _training_frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    start = datetime(2024, 1, 1)
    for index in range(80):
        season = 1 if index < 50 else 2
        home_goals = int(rng.poisson(2.6))
        away_goals = int(rng.poisson(2.4))
        if home_goals == away_goals:
            ot_home = int(rng.integers(0, 2))
            result = "X"
        elif home_goals > away_goals:
            ot_home = None
            result = "1"
        else:
            ot_home = None
            result = "2"
        rows.append({
            "match_id": index + 1,
            "season": season,
            "home_team": int(rng.integers(1, 5)),
            "away_team": int(rng.integers(5, 9)),
            "game_date": start + timedelta(days=index),
            "round": 1,
            "result": result,
            "home_team_goals": home_goals,
            "away_team_goals": away_goals,
            "home_team_sog": int(rng.integers(20, 40)),
            "away_team_sog": int(rng.integers(20, 40)),
            "home_team_saves": 20,
            "away_team_saves": 20,
            "home_team_en": 0,
            "away_team_en": 0,
            "ot_winner": None if ot_home is None else (
                1 if ot_home == 1 else 2),
            "so_winner": None})
    features = build_hockey_team_features(
        pd.DataFrame(rows), _arenas(), _empty_rosters(), _empty_stats())
    return features
