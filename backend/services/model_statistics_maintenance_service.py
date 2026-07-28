"""Orchestrate model bet generation and outcome settlement.

Coordinates repository reads/writes with dry-run, batching, EV checks,
per-batch transactions, and a mergeable cycle report. Contains no SQL.
"""

from __future__ import annotations

import logging
from contextlib import nullcontext
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from backend.database import get_db_connection
from backend.repositories import model_statistics_maintenance_repository as repo
from backend.repositories.model_statistics_maintenance_repository import (
    BetGenerationScope,
    GeneratedBet)
from backend.sports.football.outcome_evaluator import InvalidMatchResultError
from backend.sports.football.outcome_evaluator import SettlementCandidate
from backend.sports.football.outcome_evaluator import UnsupportedFootballEventError
from backend.sports.football.outcome_evaluator import evaluate_football_outcome


logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 500
DEFAULT_PREVIEW_LIMIT = 50


@dataclass
class StatisticsRefreshReport:
    """Aggregated counters and warnings for one maintenance cycle."""

    read: int = 0
    generated: int = 0
    updated: int = 0
    settled: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = True
    preview: list[dict[str, Any]] = field(default_factory=list)
    preview_truncated: bool = False

    def merge(self, other: StatisticsRefreshReport) -> StatisticsRefreshReport:
        """Return a new report with summed counters and combined warnings."""
        return StatisticsRefreshReport(
            read=self.read + other.read,
            generated=self.generated + other.generated,
            updated=self.updated + other.updated,
            settled=self.settled + other.settled,
            skipped=self.skipped + other.skipped,
            warnings=[*self.warnings, *other.warnings],
            dry_run=self.dry_run and other.dry_run,
            preview=[*self.preview, *other.preview],
            preview_truncated=(
                self.preview_truncated or other.preview_truncated))


def compute_bet_ev(probability_percent: float, odds: float) -> float:
    """Return EV for a 0–100 probability and decimal odds.

    Matches backend formula: ``(value / 100) * odds - 1``, rounded to 4 dp.
    """
    return round((probability_percent / 100.0) * odds - 1, 4)


def generate_bets(
        scope: BetGenerationScope,
        dry_run: bool,
        conn: Any | None = None,
        preview: bool = False,
        preview_limit: int = DEFAULT_PREVIEW_LIMIT
) -> StatisticsRefreshReport:
    """Generate or plan automatic model bets for priced markets.

    Candidates without a positive odds row are already excluded by the
    repository; this stage never invents bets for GOALS/EXACT.
    """
    _validate_preview_args(preview, preview_limit, dry_run)
    report = StatisticsRefreshReport(dry_run=dry_run)
    candidates = repo.fetch_bet_generation_candidates(scope)
    report.read = len(candidates)
    valid_rows: list[GeneratedBet] = []
    for row in candidates:
        if row.odds is None or row.odds <= 0:
            report.skipped += 1
            warning = (
                f"Skipped bet generation for match={row.match_id} "
                f"event={row.event_id} model={row.model_id}: "
                f"invalid odds {row.odds!r}")
            report.warnings.append(warning)
            continue
        # EV zawsze w serwisie — jedno źródło prawdy względem SQL w repo
        valid_rows.append(_with_computed_ev(row))

    if dry_run:
        report.generated = len(valid_rows)
        if preview:
            for row in valid_rows:
                _add_preview(
                    report,
                    _bet_upsert_preview(row),
                    preview_limit)
        return report

    if not valid_rows:
        return report

    written = _write_generated_bets_transaction(valid_rows, conn)
    report.generated = written
    report.updated = written
    return report


def settle_outcomes(
        batch_size: int,
        dry_run: bool,
        conn: Any | None = None,
        preview: bool = False,
        preview_limit: int = DEFAULT_PREVIEW_LIMIT,
        scope: BetGenerationScope | None = None
) -> StatisticsRefreshReport:
    """Settle pending final predictions and priced-market bets in batches.

    Final predictions cover all supported families. Bet settlement is limited
    to the priced markets already filtered by the repository.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    _validate_preview_args(preview, preview_limit, dry_run)

    report = StatisticsRefreshReport(dry_run=dry_run)
    report = report.merge(
        _settle_target_batches(
            fetch_fn=repo.fetch_pending_final_predictions,
            write_fn=repo.write_final_prediction_outcomes,
            batch_size=batch_size,
            dry_run=dry_run,
            conn=conn,
            preview=preview,
            preview_limit=preview_limit,
            scope=scope))
    report = report.merge(
        _settle_target_batches(
            fetch_fn=repo.fetch_pending_bets,
            write_fn=repo.write_bet_outcomes,
            batch_size=batch_size,
            dry_run=dry_run,
            conn=conn,
            preview=preview,
            preview_limit=preview_limit,
            scope=scope))
    return _trim_preview(report, preview_limit if preview else None)


def refresh_model_statistics(
        scope: BetGenerationScope,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = True,
        preview: bool = False,
        preview_limit: int = DEFAULT_PREVIEW_LIMIT
) -> StatisticsRefreshReport:
    """Run bet generation then outcome settlement and merge reports.

    Write errors rollback the failing batch and propagate to the caller.
    When ``preview`` is True, scope filters also apply to settlement and
    the report includes sample planned writes.
    """
    _validate_preview_args(preview, preview_limit, dry_run)
    # Przy preview scope filtruje też settlement (smoke-test per mecz)
    settlement_scope = scope if preview else None
    if dry_run:
        generation = generate_bets(
            scope,
            dry_run=True,
            preview=preview,
            preview_limit=preview_limit)
        settlement = settle_outcomes(
            batch_size,
            dry_run=True,
            preview=preview,
            preview_limit=preview_limit,
            scope=settlement_scope)
        return _trim_preview(
            generation.merge(settlement),
            preview_limit if preview else None)

    with get_db_connection() as conn:
        generation = generate_bets(scope, dry_run=False, conn=conn)
        settlement = settle_outcomes(
            batch_size, dry_run=False, conn=conn)
        return generation.merge(settlement)


def _with_computed_ev(row: GeneratedBet) -> GeneratedBet:
    """Return a copy of ``row`` with EV from ``compute_bet_ev``."""
    return GeneratedBet(
        match_id=row.match_id,
        event_id=row.event_id,
        model_id=row.model_id,
        bookmaker_id=row.bookmaker_id,
        odds=row.odds,
        probability=row.probability,
        ev=compute_bet_ev(row.probability, row.odds))


def _settle_target_batches(
        fetch_fn: Any,
        write_fn: Any,
        batch_size: int,
        dry_run: bool,
        conn: Any | None,
        preview: bool,
        preview_limit: int,
        scope: BetGenerationScope | None
) -> StatisticsRefreshReport:
    """Keyset-paginate one settlement target until candidates are exhausted."""
    report = StatisticsRefreshReport(dry_run=dry_run)
    after_id = 0
    while True:
        batch = fetch_fn(
            after_id=after_id, limit=batch_size, scope=scope)
        if not batch:
            break
        report.read += len(batch)
        evaluated, skipped, warnings = _evaluate_settlement_batch(batch)
        report.skipped += skipped
        report.warnings.extend(warnings)
        if evaluated:
            if dry_run:
                report.settled += len(evaluated)
                if preview:
                    for candidate, outcome in evaluated:
                        _add_preview(
                            report,
                            _settlement_preview(candidate, outcome),
                            preview_limit)
            else:
                outcomes = [
                    (candidate.record_id, outcome)
                    for candidate, outcome in evaluated]
                written = _write_outcomes_transaction(
                    outcomes, write_fn, conn)
                report.settled += len(evaluated)
                report.updated += written
        after_id = batch[-1].record_id
    return report


def _evaluate_settlement_batch(
        batch: list[SettlementCandidate]
) -> tuple[list[tuple[SettlementCandidate, int]], int, list[str]]:
    """Evaluate a batch; skip invalid/unsupported rows with warnings."""
    evaluated: list[tuple[SettlementCandidate, int]] = []
    warnings: list[str] = []
    skipped = 0
    for candidate in batch:
        try:
            outcome = evaluate_football_outcome(candidate)
        except (UnsupportedFootballEventError, InvalidMatchResultError) as exc:
            skipped += 1
            warnings.append(
                f"Skipped {candidate.target} id={candidate.record_id} "
                f"event_id={candidate.event_id}: {exc}")
            continue
        evaluated.append((candidate, outcome))
    return evaluated, skipped, warnings


def _write_generated_bets_transaction(
        rows: list[GeneratedBet],
        conn: Any | None
) -> int:
    """Upsert generated bets in a single transaction."""
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        try:
            written = repo.write_generated_bets(rows, connection)
            connection.commit()
            return written
        except Exception:
            connection.rollback()
            logger.exception(
                "Failed to write generated bets; batch rolled back")
            raise


def _write_outcomes_transaction(
        outcomes: list[tuple[int, int]],
        write_fn: Any,
        conn: Any | None
) -> int:
    """Persist one settlement batch in a single transaction."""
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        try:
            written = write_fn(outcomes, connection)
            connection.commit()
            return written
        except Exception:
            connection.rollback()
            logger.exception(
                "Failed to write settlement outcomes; batch rolled back")
            raise


def _validate_preview_args(
        preview: bool,
        preview_limit: int,
        dry_run: bool
) -> None:
    """Reject invalid preview combinations before any DB work."""
    if preview_limit <= 0:
        raise ValueError("preview_limit must be a positive integer")
    if preview and not dry_run:
        raise ValueError("preview requires dry_run (cannot use with writes)")


def _add_preview(
        report: StatisticsRefreshReport,
        entry: dict[str, Any],
        preview_limit: int
) -> None:
    """Append one planned write or mark the preview as truncated."""
    if len(report.preview) >= preview_limit:
        report.preview_truncated = True
        return
    report.preview.append(entry)


def _trim_preview(
        report: StatisticsRefreshReport,
        preview_limit: int | None
) -> StatisticsRefreshReport:
    """Cap merged preview samples after combining stage reports."""
    if preview_limit is None:
        return report
    if len(report.preview) <= preview_limit:
        return report
    return StatisticsRefreshReport(
        read=report.read,
        generated=report.generated,
        updated=report.updated,
        settled=report.settled,
        skipped=report.skipped,
        warnings=list(report.warnings),
        dry_run=report.dry_run,
        preview=report.preview[:preview_limit],
        preview_truncated=True)


def _bet_upsert_preview(row: GeneratedBet) -> dict[str, Any]:
    """Describe one planned bets upsert for dry-run preview."""
    return {
        "action": "upsert_bet",
        "table": "bets",
        "match_id": row.match_id,
        "event_id": row.event_id,
        "model_id": row.model_id,
        "before": None,
        "after": {
            "odds": row.odds,
            "bookmaker": row.bookmaker_id,
            "EV": row.ev,
            "model_id": row.model_id,
            "custom_bet": 0
        },
        "probability": row.probability
    }


def _settlement_preview(
        candidate: SettlementCandidate,
        outcome: int
) -> dict[str, Any]:
    """Describe one planned outcome update for dry-run preview."""
    table = (
        "final_predictions"
        if candidate.target == "final_prediction"
        else "bets")
    return {
        "action": "settle_outcome",
        "table": table,
        "id": candidate.record_id,
        "match_id": candidate.match_id,
        "event_id": candidate.event_id,
        "event_name": candidate.event_name,
        "family": candidate.family,
        "before": {"outcome": None},
        "after": {"outcome": outcome},
        "match_result": candidate.result,
        "home_goals": candidate.home_goals,
        "away_goals": candidate.away_goals
    }
