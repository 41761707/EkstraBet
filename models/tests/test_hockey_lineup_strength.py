"""Lineup strength ratios and the baseline lambda correction."""

from __future__ import annotations

import math
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)
from models.pipeline.features.hockey.lineup_strength import (
    apply_lineup_adjustment)
from models.pipeline.features.hockey.lineup_strength import (
    build_lineup_ratios)
from models.pipeline.features.hockey.lineup_strength import (
    compute_lineup_strength)
from models.pipeline.features.hockey.lineup_strength import (
    prepare_lineup_memory)
from models.pipeline.features.hockey.lineup_strength import (
    ratios_for_lineups)
from models.pipeline.features.hockey.line_slots import LineSlotResolver
from models.pipeline.features.hockey.lineup_strength import _Skater
from models.pipeline.features.hockey.lineup_strength import (
    _assigned_appearances)
from models.pipeline.features.hockey.lineup_strength import (
    _frequent_occupants)
from models.pipeline.features.hockey.lineup_strength import _strength
from models.pipeline.features.hockey.player_ratings import (
    HockeyPlayerRatingState)
from models.pipeline.prediction.hockey_markets import build_score_distribution
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.training.hockey_ratings_trainer import (
    HockeyDixonColesParams)
from models.pipeline.training.hockey_ratings_trainer import HockeyRatingsModel
from models.pipeline.training.hockey_ratings_trainer import (
    _fit_lineup_betas)
from models.pipeline.training.hockey_ratings_trainer import (
    _moneyline_home_probability)
from models.pipeline.training.hockey_ratings_trainer import (
    adjusted_match_rates)


AS_OF = datetime(2025, 10, 20)
SEASON = 12
SLOT_TOI = {
    "F1": 19.7,
    "F2": 17.5,
    "F3": 15.0,
    "F4": 10.7,
    "D1": 22.5,
    "D2": 20.1,
    "D3": 15.6}


def test_missing_first_line_lowers_offence_more_than_the_fourth() -> None:
    # Ten sam rating: różnicę robią minuty 19,7 przeciw 10,7.
    toi = {"F1": 19.7, "F4": 10.7}
    first = _off_skater(1, "F1", 2.0)
    fourth = _off_skater(2, "F4", 2.0)
    baseline = [first, fourth]
    full = _strength(baseline, baseline, toi)
    dropped_first = _strength([fourth], baseline, toi)
    dropped_fourth = _strength([first], baseline, toi)
    first_share = 19.7 / (19.7 + 10.7)
    fourth_share = 10.7 / (19.7 + 10.7)

    assert full["lineup_off_ratio"] == pytest.approx(1.0)
    assert dropped_first["lineup_off_ratio"] == pytest.approx(
        1.0 - first_share)
    assert dropped_fourth["lineup_off_ratio"] == pytest.approx(
        1.0 - fourth_share)
    assert (
        dropped_first["lineup_off_ratio"]
        < dropped_fourth["lineup_off_ratio"])
    assert dropped_first["missing_top6_f"] == pytest.approx(1.0)
    assert dropped_fourth["missing_top6_f"] == pytest.approx(0.0)


def test_typical_lineup_has_unit_ratios() -> None:
    ratings = HockeyPlayerRatingState()
    lineup = _lineup(_skater(1, 1), _skater(2, 4), _defender(3, 1))
    strength = _strength_of(lineup, lineup, ratings)
    assert strength["lineup_off_ratio"] == pytest.approx(1.0)
    assert strength["lineup_def_ratio"] == pytest.approx(1.0)
    assert strength["missing_top6_f"] == pytest.approx(0.0)
    assert strength["missing_top4_d"] == pytest.approx(0.0)


def test_predicted_confidence_shrinks_only_the_gap_from_typical() -> None:
    toi = {"F1": 19.7}
    typical = _off_skater(1, "F1", 2.0, weight=1.0)
    same_projected = _off_skater(1, "F1", 2.0, weight=0.8)
    weaker = _off_skater(2, "F1", 1.0, weight=0.5)
    certain_weaker = _off_skater(2, "F1", 1.0, weight=1.0)
    raw = _strength([certain_weaker], [typical], toi)["lineup_off_ratio"]
    shrunk = _strength([weaker], [typical], toi)
    same = _strength([same_projected], [typical], toi)
    assert same["lineup_off_ratio"] == pytest.approx(1.0)
    assert same["lineup_off"] == pytest.approx(
        _strength([typical], [typical], toi)["lineup_off"])
    assert raw == pytest.approx(0.5)
    assert shrunk["lineup_off_ratio"] == pytest.approx(
        1.0 + 0.5 * (raw - 1.0))


def test_projection_without_confidence_stays_at_typical() -> None:
    ratings = HockeyPlayerRatingState()
    certain = _lineup(_skater(1, 1, source="CONFIRMED"))
    external = _lineup(_skater(1, 1, source="EXTERNAL", confidence=0.5))
    missing = _lineup(_skater(1, 1, source="MODEL", confidence=None))
    full = _strength_of(certain, certain, ratings)
    half = _strength_of(external, certain, ratings)
    empty = _strength_of(missing, certain, ratings)
    assert half["lineup_off_ratio"] == pytest.approx(1.0)
    assert half["lineup_off"] == pytest.approx(full["lineup_off"])
    assert empty["lineup_off"] == pytest.approx(0.0)
    assert empty["lineup_off_ratio"] == pytest.approx(1.0)


def test_zero_share_replacement_stays_in_the_level_sum() -> None:
    toi = {"F1": 60.0}
    usual = _off_skater(1, "F1", 2.0, weight=1.0)
    replacement = _off_skater(2, "F1", 1.0, weight=0.0)
    kept = _off_skater(3, "F1", 2.0, weight=1.0)
    empty = _strength([], [usual], toi)
    filled = _strength([replacement], [usual], toi)
    without = _strength([kept], [usual, usual], toi)
    mixed = _strength([kept, replacement], [usual, usual], toi)
    assert empty["lineup_off"] == pytest.approx(0.0)
    assert filled["lineup_off"] == pytest.approx(1.0)
    assert mixed["lineup_off"] > without["lineup_off"]
    assert mixed["lineup_off_ratio"] > without["lineup_off_ratio"]


def test_zero_confidence_skater_is_not_left_out() -> None:
    ratings = HockeyPlayerRatingState()
    baseline = _lineup(_skater(1, 1))
    filled = _strength_of(
        _lineup(_skater(2, 1, source="MODEL", confidence=0.0)),
        baseline,
        ratings)
    assert filled["lineup_off"] > 0.0


def test_defence_ratio_follows_the_rating_even_when_it_is_negative() -> None:
    toi = {"D1": 22.5}
    baseline = [_defence_skater(1, 1.0)]
    weaker = [_defence_skater(2, -2.0)]
    stronger = [_defence_skater(3, 2.0)]
    negative_base = [_defence_skater(1, -0.25)]
    more_negative = [_defence_skater(2, -0.75)]
    even = [_defence_skater(4, 0.0)]
    modest = [_defence_skater(5, 0.5)]
    assert _strength(weaker, baseline, toi)["lineup_def_ratio"] < 1.0
    assert _strength(stronger, baseline, toi)["lineup_def_ratio"] > 1.0
    worse = _strength(more_negative, negative_base, toi)
    assert worse["lineup_def_ratio"] < 1.0
    assert worse["lineup_def"] < _strength(
        negative_base, negative_base, toi)["lineup_def"]
    assert _strength(modest, even, toi)["lineup_def_ratio"] > 1.2


def test_zero_beta_leaves_the_rate_unchanged() -> None:
    assert apply_lineup_adjustment(
        3.1, 1.8, 0.55, 1.0, 0.0, 0.0) == pytest.approx(3.1)


def test_zero_beta_distribution_ignores_lineup_ratios() -> None:
    model = _neutral_model()
    plain = model.score_distribution(1, 2, 0.91, 0.91, 0.91, 0.91)
    tilted = model.score_distribution(
        1,
        2,
        0.91,
        0.91,
        0.91,
        0.91,
        home_off_ratio=1.7,
        away_off_ratio=0.6,
        home_def_ratio=1.4,
        away_def_ratio=0.5)
    assert np.allclose(plain.regulation_matrix, tilted.regulation_matrix)


def test_positive_beta_scales_the_home_rate() -> None:
    model = _neutral_model(beta_off=1.0)
    base_home, base_away = model.base_lambdas(1, 2)
    lambda_home, lambda_away = adjusted_match_rates(
        model,
        1,
        2,
        0.9,
        0.9,
        0.9,
        0.9,
        home_off_ratio=1.25,
        away_def_ratio=0.8)
    assert lambda_home == pytest.approx(
        base_home * (1.25 ** 1.0) * (0.8 ** 0.0))
    assert lambda_away == pytest.approx(base_away)


def test_lineup_formula_matches_the_goalie_and_both_ratios() -> None:
    adjusted = apply_lineup_adjustment(3.0, 1.25, 0.8, 1.1, 0.5, 0.5)
    expected = 3.0 * (1.25 ** 0.5) * (0.8 ** -0.5) * 1.1
    assert adjusted == pytest.approx(expected)


def test_line_changes_backfill_the_slot_they_leave() -> None:
    # 1-3 mają 6 meczów w F1 i 4 w F2. 4-6 mają 4 w F1 i 3 w F2.
    # F1 bierze 1-3, a F2 nie może zostać puste.
    from collections import deque

    games: deque[list[tuple[int, str]]] = deque()
    for _index in range(3):
        games.append([
            (1, "F1"), (2, "F1"), (3, "F1"),
            (4, "F2"), (5, "F2"), (6, "F2")])
    for _index in range(3):
        games.append([(1, "F1"), (2, "F1"), (3, "F1")])
    for _index in range(4):
        games.append([
            (4, "F1"), (5, "F1"), (6, "F1"),
            (1, "F2"), (2, "F2"), (3, "F2")])
    by_slot: dict[str, list[int]] = {}
    for player_id, slot in _frequent_occupants(games):
        by_slot.setdefault(slot, []).append(player_id)
    assert by_slot["F1"] == [1, 2, 3]
    assert by_slot["F2"] == [4, 5, 6]
    start = datetime(2025, 10, 1)
    rosters, stats = _line_change_window(start)
    final = start + timedelta(days=10)
    rosters = pd.concat(
        [rosters, pd.DataFrame(_typical_night(11, final))],
        ignore_index=True)
    stats = pd.concat(
        [stats, pd.DataFrame(_typical_boxes(11))],
        ignore_index=True)
    ratios = build_lineup_ratios(rosters, stats, baseline_games=10)
    dressed = ratios.loc[ratios["match_id"] == 11].iloc[0]
    assert dressed["lineup_off_ratio"] == pytest.approx(1.0)
    assert dressed["lineup_def_ratio"] == pytest.approx(1.0)


def test_repeated_actual_lineup_stays_at_one() -> None:
    start = datetime(2025, 10, 1)
    later = start + timedelta(days=2)
    rosters = pd.DataFrame([
        _roster(1, 10, "C", 1, start),
        _roster(1, 11, "C", 4, start),
        _roster(2, 10, "C", 1, later),
        _roster(2, 11, "C", 4, later)])
    stats = pd.DataFrame([
        _box(1, 10, 2),
        _box(1, 11, 0),
        _box(2, 10, 1),
        _box(2, 11, 0)])
    ratios = build_lineup_ratios(rosters, stats, baseline_games=10)
    second = ratios.loc[ratios["match_id"] == 2].iloc[0]
    assert second["lineup_off_ratio"] == pytest.approx(1.0)
    assert second["lineup_def_ratio"] == pytest.approx(1.0)


def test_later_points_do_not_change_an_earlier_lineup_row() -> None:
    start = datetime(2025, 10, 1)
    mid = start + timedelta(days=2)
    late = start + timedelta(days=4)
    early_rosters = pd.DataFrame([
        _roster(1, 10, "C", 1, start),
        _roster(2, 10, "C", 1, mid)])
    early_stats = pd.DataFrame([
        _box(1, 10, 1),
        _box(2, 10, 1)])
    before = build_lineup_ratios(early_rosters, early_stats)
    later_rosters = pd.concat(
        [early_rosters, pd.DataFrame([_roster(3, 10, "C", 1, late)])],
        ignore_index=True)
    later_stats = pd.concat(
        [early_stats, pd.DataFrame([_box(3, 10, 50)])],
        ignore_index=True)
    after = build_lineup_ratios(later_rosters, later_stats)
    earlier = before.loc[before["match_id"] == 2].iloc[0]
    still = after.loc[after["match_id"] == 2].iloc[0]
    latest = after.loc[after["match_id"] == 3].iloc[0]
    assert still["lineup_off"] == pytest.approx(earlier["lineup_off"])
    assert still["lineup_off_ratio"] == pytest.approx(
        earlier["lineup_off_ratio"])
    assert latest["lineup_off"] != pytest.approx(still["lineup_off"])


def test_opening_night_minutes_match_build_slot_toi(
        monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2025, 4, 1)
    second = start + timedelta(days=3)
    opening = datetime(2025, 10, 5)
    rosters = pd.DataFrame([
        _season_roster(1, start, 12),
        _season_roster(2, second, 12),
        _season_roster(3, opening, 13)])
    stats = pd.DataFrame([
        _toi_box(1, 600),
        _toi_box(2, 1800),
        _toi_box(3, 600)])
    memory = prepare_lineup_memory(rosters.iloc[:2], stats.iloc[:2])
    expected = _opening_f1_minutes(rosters, stats)
    assert memory.slot_minutes.for_team(7, 13)["F1"] == pytest.approx(
        expected)
    same_rosters = rosters.copy()
    same_rosters.loc[same_rosters["match_id"] == 3, "season"] = 12
    carried = memory.slot_minutes.for_team(7, 12)["F1"]
    assert carried == pytest.approx(
        _opening_f1_minutes(same_rosters, stats))
    assert carried != pytest.approx(expected)
    seen: dict[str, float] = {}
    real = _strength

    def _capture(current, baseline, slot_toi):
        seen["F1"] = float(slot_toi["F1"])
        return real(current, baseline, slot_toi)

    monkeypatch.setattr(
        "models.pipeline.features.hockey.lineup_strength._strength",
        _capture)
    home = _lineup(_skater(10, 1, source="CONFIRMED"))
    scored = ratios_for_lineups(
        home, None, None, None, opening, 13, memory=memory)
    assert scored is not None
    assert seen["F1"] == pytest.approx(expected)


def test_future_reads_do_not_move_the_rating_cursor() -> None:
    start = datetime(2025, 10, 1)
    later = start + timedelta(days=2)
    rosters = pd.DataFrame([
        _roster(1, 10, "C", 1, start),
        _roster(2, 10, "C", 1, later)])
    stats = pd.DataFrame([_box(1, 10, 1), _box(2, 10, 1)])
    memory = prepare_lineup_memory(rosters, stats)
    home = _lineup(_skater(10, 1, source="CONFIRMED"))
    far = datetime(2025, 10, 20)
    near = datetime(2025, 10, 12)
    first = ratios_for_lineups(
        home, None, None, None, far, SEASON, memory=memory)
    second = ratios_for_lineups(
        home, None, None, None, near, SEASON, memory=memory)
    assert first is not None
    assert second is not None
    assert second["home_off_ratio"] == pytest.approx(first["home_off_ratio"])


def test_one_missing_side_stays_at_one_and_history_is_reused(
        monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2025, 10, 1)
    later = start + timedelta(days=2)
    rosters = pd.DataFrame([
        _roster(1, 10, "C", 1, start),
        _roster(1, 11, "C", 4, start),
        _roster(2, 10, "C", 1, later),
        _roster(2, 11, "C", 4, later)])
    stats = pd.DataFrame([
        _box(1, 10, 2),
        _box(1, 11, 0),
        _box(2, 10, 1),
        _box(2, 11, 0)])
    home = _lineup(_skater(11, 4, source="MODEL", confidence=1.0))
    calls = {"n": 0}
    real = prepare_lineup_memory

    def _count(rosters, player_stats, baseline_games=10):
        calls["n"] += 1
        return real(rosters, player_stats, baseline_games)

    monkeypatch.setattr(
        "models.pipeline.features.hockey.lineup_strength."
        "prepare_lineup_memory",
        _count)
    moment = datetime(2025, 10, 10)
    first = ratios_for_lineups(home, None, rosters, stats, moment, SEASON)
    assert first is not None
    assert first["away_off_ratio"] == pytest.approx(1.0)
    assert first["away_def_ratio"] == pytest.approx(1.0)
    assert first["home_off_ratio"] < 1.0
    memory = real(rosters, stats)
    second = ratios_for_lineups(
        None,
        home,
        None,
        None,
        moment,
        SEASON,
        memory=memory)
    assert second is not None
    assert second["home_off_ratio"] == pytest.approx(1.0)
    assert second["away_off_ratio"] == pytest.approx(first["home_off_ratio"])
    assert calls["n"] == 1


def test_vectorized_moneyline_matches_the_score_matrix() -> None:
    lambda_home = np.array([2.4, 3.1])
    lambda_away = np.array([2.2, 2.6])
    probability = _moneyline_home_probability(
        lambda_home, lambda_away, 1.2, 0.54, 12)
    for index in range(2):
        distribution = build_score_distribution(
            float(lambda_home[index]),
            float(lambda_away[index]),
            1.2,
            0.54,
            12)
        markets = derive_hockey_markets(distribution)
        assert probability[index] == pytest.approx(
            markets["ml_home"] / 100.0, abs=1e-8)


def test_beta_grid_keeps_zero_when_ratios_do_not_help() -> None:
    frame = _ratio_frame([1.0, 1.0, 1.0, 1.0], [1, 0, 1, 0])
    beta_off, beta_def = _fit_lineup_betas(
        frame, *_flat_strength(), _beta_params())
    assert beta_off == pytest.approx(0.0)
    assert beta_def == pytest.approx(0.0)


def test_beta_grid_raises_offence_when_it_lowers_log_loss() -> None:
    frame = _ratio_frame([1.8, 0.55] * 20, [1, 0] * 20)
    beta_off, beta_def = _fit_lineup_betas(
        frame, *_flat_strength(), _beta_params())
    assert beta_off == pytest.approx(1.0)
    assert beta_def == pytest.approx(0.0)


def _strength_of(
        lineup: ProbableLineup,
        baseline: ProbableLineup,
        ratings: HockeyPlayerRatingState) -> dict[str, float]:
    return compute_lineup_strength(
        lineup, ratings, SLOT_TOI, baseline, AS_OF, SEASON)


def _lineup(*players: ProbableLineupPlayer) -> ProbableLineup:
    return ProbableLineup(match_id=1, team_id=7, players=list(players))


def _skater(
        player_id: int,
        line: int,
        source: str = "CONFIRMED",
        confidence: float | None = 1.0) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="C",
        line=line,
        pp_unit=None,
        is_starting_goalie=None,
        confidence=confidence,
        source=source)


def _off_skater(
        player_id: int,
        slot: str,
        off_rating: float,
        weight: float = 1.0) -> _Skater:
    return _Skater(
        player_id=player_id,
        slot=slot,
        off_rating=off_rating,
        shot_rating=0.0,
        def_rating=0.0,
        weight=weight)


def _defence_skater(player_id: int, def_rating: float) -> _Skater:
    return _Skater(
        player_id=player_id,
        slot="D1",
        off_rating=0.0,
        shot_rating=0.0,
        def_rating=def_rating,
        weight=1.0)


def _defender(player_id: int, line: int) -> ProbableLineupPlayer:
    return ProbableLineupPlayer(
        player_id=player_id,
        position="D",
        line=line,
        pp_unit=None,
        is_starting_goalie=None,
        confidence=1.0,
        source="CONFIRMED")


def _neutral_model(beta_off: float = 0.0) -> HockeyRatingsModel:
    return HockeyRatingsModel(
        attack={1: 0.0, 2: 0.0},
        defense={1: math.log(3.0), 2: math.log(3.0)},
        home_adv=0.0,
        tie_inflation=1.1,
        p_ot_home=0.52,
        max_goals=8,
        mean_defense=math.log(3.0),
        beta_off=beta_off,
        beta_def=0.0)


def _opening_f1_minutes(
        rosters: pd.DataFrame,
        stats: pd.DataFrame) -> float:
    assigned = _assigned_appearances(rosters, stats)
    toi = LineSlotResolver().build_slot_toi(assigned)
    row = toi.loc[(toi["match_id"] == 3) & (toi["slot"] == "F1")]
    return float(row["slot_toi_minutes"].iloc[0])


def _season_roster(
        match_id: int,
        when: datetime,
        season: int) -> dict[str, object]:
    row = _roster(match_id, 10, "C", 1, when)
    row["season"] = season
    return row


def _toi_box(match_id: int, toi_seconds: int) -> dict[str, object]:
    row = _box(match_id, 10, 1)
    row["toi_seconds"] = toi_seconds
    return row


def _line_change_window(
        start: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
    rosters: list[dict[str, object]] = []
    stats: list[dict[str, object]] = []
    nights = (
        [(1, 1), (2, 1), (3, 1), (4, 2), (5, 2), (6, 2)],
        [(1, 1), (2, 1), (3, 1)],
        [(4, 1), (5, 1), (6, 1), (1, 2), (2, 2), (3, 2)])
    repeats = (3, 3, 4)
    match_id = 1
    for pattern, count in zip(nights, repeats):
        for _index in range(count):
            when = start + timedelta(days=match_id - 1)
            for player_id, line in pattern:
                rosters.append(_roster(
                    match_id, player_id, "C", line, when))
                stats.append(_box(match_id, player_id, 1))
            match_id += 1
    return pd.DataFrame(rosters), pd.DataFrame(stats)


def _typical_night(match_id: int, when: datetime) -> list[dict[str, object]]:
    rows = []
    for player_id in (1, 2, 3):
        rows.append(_roster(match_id, player_id, "C", 1, when))
    for player_id in (4, 5, 6):
        rows.append(_roster(match_id, player_id, "C", 2, when))
    return rows


def _typical_boxes(match_id: int) -> list[dict[str, object]]:
    return [
        _box(match_id, player_id, 1)
        for player_id in (1, 2, 3, 4, 5, 6)]


def _roster(
        match_id: int,
        player_id: int,
        position: str,
        line: int,
        when: datetime) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": 7,
        "position": position,
        "line": line,
        "game_date": when,
        "season": SEASON}


def _box(match_id: int, player_id: int, points: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": 7,
        "points": points,
        "sog": 2,
        "plus_minus": 0,
        "toi_seconds": 1200}


def _ratio_frame(off_ratios: list[float], wins: list[int]) -> pd.DataFrame:
    rows = []
    for off_ratio, win in zip(off_ratios, wins):
        rows.append({
            "home_team": 1,
            "away_team": 2,
            "home_goalie_save_pct": 0.9,
            "away_goalie_save_pct": 0.9,
            "home_team_save_pct": 0.9,
            "away_team_save_pct": 0.9,
            "home_lineup_off_ratio": off_ratio,
            "away_lineup_off_ratio": 1.0,
            "home_lineup_def_ratio": 1.0,
            "away_lineup_def_ratio": 1.0,
            "final_home_win": float(win)})
    return pd.DataFrame(rows)


def _flat_strength() -> tuple[
        dict[int, float], dict[int, float], float, float, float, float]:
    defense = math.log(2.8)
    return (
        {1: 0.0, 2: 0.0},
        {1: defense, 2: defense},
        0.05,
        defense,
        1.0,
        0.52)


def _beta_params() -> HockeyDixonColesParams:
    return HockeyDixonColesParams(
        lineup_beta_off_grid=(0.0, 1.0),
        lineup_beta_def_grid=(0.0,),
        early_season=EarlySeasonConfig(games=8, boost=1.0),
        max_goals=8)
