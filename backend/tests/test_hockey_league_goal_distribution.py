"""Tests for NHL league goal pie buckets."""

from __future__ import annotations
from backend.sports.hockey.league_stats import bucket_goal_totals


def test_bucket_goal_totals_splits_streamlit_slices() -> None:
    buckets = bucket_goal_totals([4, 5, 6, 7, 8, 3])
    assert buckets["total_matches"] == 6
    assert buckets["under_5"] == 2
    assert buckets["exactly_5"] == 1
    assert buckets["exactly_6"] == 1
    assert buckets["exactly_7"] == 1
    assert buckets["over_7"] == 1


def test_bucket_goal_totals_empty() -> None:
    buckets = bucket_goal_totals([])
    assert buckets["total_matches"] == 0
    assert buckets["under_5"] == 0
    assert buckets["over_7"] == 0
