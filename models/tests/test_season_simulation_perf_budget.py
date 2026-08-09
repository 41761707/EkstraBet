"""Unit tests for season simulation performance budget helpers."""

from __future__ import annotations

import pytest

from models.pipeline.simulation import perf_budget


def test_reference_budget_matches_measured_run() -> None:
    """Approved wall limit is 2x the measured 2000-trial reference."""
    assert perf_budget.REFERENCE_TEAM_COUNT == 18
    assert perf_budget.REFERENCE_FIXTURE_COUNT == 306
    assert perf_budget.REFERENCE_TRIALS == 2000
    assert perf_budget.REFERENCE_WALL_SECONDS == 3079
    assert (
        perf_budget.APPROVED_WALL_SECONDS_LIMIT
        == 2 * perf_budget.REFERENCE_WALL_SECONDS)
    assert perf_budget.REFERENCE_PEAK_RSS_MB is None
    assert perf_budget.PEAK_RSS_LIMIT_IS_MEASURED is False
    assert (
        perf_budget.APPROVED_PEAK_RSS_MB_LIMIT
        == perf_budget.UNMEASURED_PEAK_RSS_SOFT_CEILING_MB)
    assert perf_budget.MOCK_PERF_REFERENCE_WALL_SECONDS == 77.0
    assert perf_budget.MOCK_PERF_REFERENCE_RSS_MB == 144.0


def test_perf_enabled_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(perf_budget.PERF_ENV_FLAG, raising=False)
    assert perf_budget.perf_enabled() is False
    monkeypatch.setenv(perf_budget.PERF_ENV_FLAG, "1")
    assert perf_budget.perf_enabled() is True
    monkeypatch.setenv(perf_budget.PERF_ENV_FLAG, "yes")
    assert perf_budget.perf_enabled() is True


def test_resolve_perf_trials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(perf_budget.PERF_TRIALS_ENV, raising=False)
    assert (
        perf_budget.resolve_perf_trials()
        == perf_budget.DEFAULT_PERF_TRIALS)
    monkeypatch.setenv(perf_budget.PERF_TRIALS_ENV, "250")
    assert perf_budget.resolve_perf_trials() == 250
    monkeypatch.setenv(perf_budget.PERF_TRIALS_ENV, "0")
    with pytest.raises(ValueError):
        perf_budget.resolve_perf_trials()


def test_peak_rss_mb_returns_non_negative_or_none() -> None:
    value = perf_budget.peak_rss_mb()
    if value is not None:
        assert value >= 0.0


def test_wall_clock_measures_elapsed() -> None:
    with perf_budget.WallClock() as clock:
        pass
    assert clock.elapsed >= 0.0
