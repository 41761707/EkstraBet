"""Performance budget constants and helpers for season simulation."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass


# Referencyjny run produkcyjny (TensorFlow, liga 1 / sezon 13, N=18):
# season_projection_runs.id=5, n_trials=2000, 306 fixture'ów, ~3079 s.
REFERENCE_LEAGUE_ID = 1
REFERENCE_SEASON_ID = 13
REFERENCE_TEAM_COUNT = 18
REFERENCE_FIXTURE_COUNT = 306
REFERENCE_TRIALS = 2000
REFERENCE_WALL_SECONDS = 3079
# Limit operacyjny pod scheduler: 2x pomiar referencyjny (bufor CPU/IO).
APPROVED_WALL_SECONDS_LIMIT = 2 * REFERENCE_WALL_SECONDS

# Peak RSS z runu id=5 nie było zapisane — brak REFERENCE_PEAK_RSS_MB.
REFERENCE_PEAK_RSS_MB: float | None = None
PEAK_RSS_LIMIT_IS_MEASURED = False
# Interim soft ceiling (nie zatwierdzony pomiarem). Po kolejnym TF runie
# ustaw REFERENCE_PEAK_RSS_MB z CLI `peak_rss_mb` i podnieś flagę.
UNMEASURED_PEAK_RSS_SOFT_CEILING_MB = 4096
APPROVED_PEAK_RSS_MB_LIMIT = UNMEASURED_PEAK_RSS_SOFT_CEILING_MB

# Opt-in harness (mock predictor) — nie w domyślnym CI.
PERF_ENV_FLAG = "EKSTRABET_SEASON_PERF"
PERF_TRIALS_ENV = "EKSTRABET_SEASON_PERF_TRIALS"
DEFAULT_PERF_TRIALS = 100
# Soft budget mock: pełna liga N=18, 100 triali — luźny limit antyregresyjny.
# Pomiar referencyjny harnessu (Win, mock lambdas): ~77 s wall, ~144 MiB RSS.
MOCK_PERF_WALL_SECONDS_LIMIT = 180.0
MOCK_PERF_PEAK_RSS_MB_LIMIT = 2048.0
MOCK_PERF_REFERENCE_WALL_SECONDS = 77.0
MOCK_PERF_REFERENCE_RSS_MB = 144.0


@dataclass(frozen=True)
class PerfSample:
    """One wall-clock / RSS sample from a simulation run."""

    wall_seconds: float
    peak_rss_mb: float | None
    n_trials: int
    fixture_count: int
    team_count: int


def perf_enabled() -> bool:
    """Return True when the opt-in performance harness should run."""
    raw = os.environ.get(PERF_ENV_FLAG, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_perf_trials(default: int = DEFAULT_PERF_TRIALS) -> int:
    """Read trial count for the opt-in harness from the environment."""
    raw = os.environ.get(PERF_TRIALS_ENV)
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{PERF_TRIALS_ENV} must be >= 1")
    return value


def peak_rss_mb() -> float | None:
    """Best-effort peak resident set size in MiB for this process."""
    if sys.platform == "win32":
        return _peak_rss_mb_windows()
    try:
        import resource
    except ImportError:
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux: KB; macOS: bytes
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024.0 * 1024.0)
    return usage.ru_maxrss / 1024.0


def _peak_rss_mb_windows() -> float | None:
    # GetProcessMemoryInfo bez dodatkowych zależności (psutil).
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t)
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    get_mem = ctypes.windll.psapi.GetProcessMemoryInfo
    get_mem.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD
    ]
    get_mem.restype = wintypes.BOOL
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ok = get_mem(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        return None
    return counters.PeakWorkingSetSize / (1024.0 * 1024.0)


class WallClock:
    """Simple wall-clock timer used by the performance harness."""

    def __init__(self) -> None:
        self._started = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> WallClock:
        self._started = time.perf_counter()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.elapsed = time.perf_counter() - self._started
