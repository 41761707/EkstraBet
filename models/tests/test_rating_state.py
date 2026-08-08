"""Tests for cloneable RatingState snapshot/commit semantics."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

import pandas as pd

from models.pipeline.features.ratings import compute_ratings_timeline
from models.pipeline.features.ratings.state import RatingState


def _matches(count: int = 4) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    rows = []
    for index in range(count):
        rows.append({
            "id": index + 1,
            "league": 1,
            "home_team": 10 if index % 2 == 0 else 20,
            "away_team": 20 if index % 2 == 0 else 10,
            "game_date": start + timedelta(days=index),
            "result": "1",
            "home_team_goals": 2,
            "away_team_goals": 1
        })
    return pd.DataFrame(rows)


def test_snapshot_before_commit_keeps_same_round_independent() -> None:
    state = RatingState()
    # oba snapshoty przed commitami — jak batchowanie kolejki
    first = state.snapshot(10, 20)
    second = state.snapshot(30, 40)
    assert first["home_elo"] == 1500.0
    assert second["home_elo"] == 1500.0
    assert second["away_elo"] == 1500.0
    assert first["home_czech_win_pct"] == 0.0
    state.commit(10, 20, home_goals=3, away_goals=0)
    state.commit(30, 40, home_goals=1, away_goals=1)
    after_first = state.snapshot(10, 20)
    after_second = state.snapshot(30, 40)
    assert after_first["home_elo"] > 1500.0
    assert after_first["home_czech_win_pct"] == 1.0
    # drużyna 30 nie grała z 10/20 — tylko własny remis
    assert after_second["home_elo"] != after_first["home_elo"]
    assert after_second["home_czech_win_pct"] == 0.0


def test_same_team_sees_identical_pre_match_rating_in_round() -> None:
    state = RatingState()
    first = state.snapshot(10, 20)
    # ta sama drużyna w drugim meczu kolejki — bez leakage z pierwszego
    second = state.snapshot(10, 30)
    assert first["home_elo"] == second["home_elo"] == 1500.0
    state.commit(10, 20, home_goals=4, away_goals=0)
    state.commit(10, 30, home_goals=1, away_goals=0)
    # dopiero po commitach całej kolejki rating rośnie
    later = state.snapshot(10, 40)
    assert later["home_elo"] > 1500.0


def test_trial_copies_are_independent() -> None:
    base = RatingState()
    base.snapshot(10, 20)
    base.commit(10, 20, home_goals=2, away_goals=1)
    trial_a = base.copy()
    trial_b = base.copy()
    before_a = trial_a.snapshot(10, 20)
    before_b = trial_b.snapshot(10, 20)
    assert before_a == before_b
    trial_a.commit(10, 20, home_goals=5, away_goals=0)
    after_a = trial_a.snapshot(10, 20)
    after_b = trial_b.snapshot(10, 20)
    base_again = base.snapshot(10, 20)
    assert after_a["home_elo"] > after_b["home_elo"]
    assert after_b == before_b
    assert base_again == before_b
    assert after_a["home_czech_win_pct"] == 1.0
    assert after_b["home_czech_win_pct"] == 1.0


def test_prune_to_teams_drops_outsiders() -> None:
    state = RatingState()
    state.snapshot(10, 20)
    state.commit(10, 20, home_goals=2, away_goals=1)
    state.snapshot(30, 40)
    state.commit(30, 40, home_goals=1, away_goals=0)
    state.prune_to_teams({10, 20})
    assert set(state._elo) == {10, 20}
    assert set(state._gap) == {10, 20}
    assert set(state._czech) == {10, 20}


def test_rating_state_matches_compute_ratings_timeline() -> None:
    matches = _matches(5)
    # dwa mecze tej samej daty — ten sam wzorzec batchowania
    matches.loc[1, "game_date"] = matches.loc[0, "game_date"]
    timeline = compute_ratings_timeline(matches)
    state = RatingState()
    rebuilt: list[dict[str, float]] = []
    for _, group in matches.groupby("game_date", sort=False):
        group_snaps: list[dict[str, float]] = []
        for _, row in group.iterrows():
            group_snaps.append(state.snapshot(
                int(row["home_team"]), int(row["away_team"])))
        for index, (_, row) in enumerate(group.iterrows()):
            home_id = int(row["home_team"])
            away_id = int(row["away_team"])
            state.commit(
                home_id,
                away_id,
                int(row["home_team_goals"]),
                int(row["away_team_goals"]))
            group_snaps[index].update(
                state.post_snapshot(home_id, away_id))
            rebuilt.append(group_snaps[index])
    for index, values in enumerate(rebuilt):
        for key, value in values.items():
            assert timeline.loc[index, key] == value


def test_copy_isolates_czech_deque_maxlen() -> None:
    state = RatingState()
    state.snapshot(1, 2)
    state.commit(1, 2, home_goals=1, away_goals=0)
    clone = state.copy()
    for _ in range(10):
        clone.snapshot(1, 2)
        clone.commit(1, 2, home_goals=2, away_goals=0)
    original = state.snapshot(1, 2)
    mutated = clone.snapshot(1, 2)
    assert original["home_czech_win_pct"] == 1.0
    assert mutated["home_czech_win_pct"] == 1.0
    assert original["home_elo"] < mutated["home_elo"]
