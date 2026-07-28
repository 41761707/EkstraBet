"""Unit tests for model statistics maintenance service orchestration."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.repositories.model_statistics_maintenance_repository import (
    BetGenerationScope,
    GeneratedBet)
from backend.services.model_statistics_maintenance_service import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_PREVIEW_LIMIT,
    StatisticsRefreshReport,
    compute_bet_ev,
    generate_bets,
    refresh_model_statistics,
    settle_outcomes)
from backend.sports.football.outcome_evaluator import EventFamily
from backend.sports.football.outcome_evaluator import SettlementCandidate


def _fp_candidate(
        record_id: int,
        event_id: int = 1,
        family: EventFamily = "REZULTAT",
        event_name: str = "home",
        result: str = "1",
        home_goals: int | None = 2,
        away_goals: int | None = 1,
        match_id: int | None = 100
) -> SettlementCandidate:
    return SettlementCandidate(
        record_id=record_id,
        target="final_prediction",
        event_id=event_id,
        event_name=event_name,
        family=family,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        match_id=match_id)


def _bet_candidate(
        record_id: int,
        event_id: int = 1,
        family: EventFamily = "REZULTAT",
        event_name: str = "home",
        result: str = "1",
        home_goals: int | None = 2,
        away_goals: int | None = 1,
        match_id: int | None = 100
) -> SettlementCandidate:
    return SettlementCandidate(
        record_id=record_id,
        target="bet",
        event_id=event_id,
        event_name=event_name,
        family=family,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        match_id=match_id)


class TestComputeBetEv(unittest.TestCase):
    """EV must follow the backend 0–100 probability scale."""

    def test_ev_uses_percent_scale(self) -> None:
        # 50% at odds 2.5 => (0.5 * 2.5) - 1 = 0.25
        self.assertEqual(compute_bet_ev(50.0, 2.5), 0.25)

    def test_ev_rounds_to_four_decimals(self) -> None:
        # (33.33/100)*2.1 - 1 = -0.30007 → -0.3001
        self.assertEqual(compute_bet_ev(33.33, 2.1), -0.3001)


class TestGenerateBets(unittest.TestCase):
    """Bet generation dry-run, EV computation, and write path."""

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates")
    def test_dry_run_does_not_write(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            GeneratedBet(
                match_id=1,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=2.0,
                probability=60.0)]
        with patch(
                "backend.services.model_statistics_maintenance_service.repo"
                ".write_generated_bets") as mock_write:
            report = generate_bets(
                BetGenerationScope(league_id=1), dry_run=True)
        self.assertTrue(report.dry_run)
        self.assertEqual(report.read, 1)
        self.assertEqual(report.generated, 1)
        self.assertEqual(report.updated, 0)
        mock_write.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_generated_bets",
        return_value=1)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates")
    def test_write_recomputes_ev_before_persist(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock) -> None:
        # Celowo złe EV z „repo” — serwis musi nadpisać formułą compute_bet_ev
        mock_fetch.return_value = [
            GeneratedBet(
                match_id=10,
                event_id=8,
                model_id=4,
                bookmaker_id=1,
                odds=2.5,
                probability=50.0,
                ev=999.0)]
        conn = MagicMock()
        report = generate_bets(
            BetGenerationScope(match_id=10), dry_run=False, conn=conn)
        written_rows = mock_write.call_args.args[0]
        self.assertEqual(len(written_rows), 1)
        self.assertEqual(written_rows[0].ev, compute_bet_ev(50.0, 2.5))
        self.assertEqual(written_rows[0].ev, 0.25)
        conn.commit.assert_called_once()
        self.assertEqual(report.generated, 1)
        self.assertEqual(report.updated, 1)
        self.assertFalse(report.dry_run)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_generated_bets")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates")
    def test_invalid_odds_are_skipped(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock) -> None:
        mock_fetch.return_value = [
            GeneratedBet(
                match_id=1,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=0.0,
                probability=60.0)]
        report = generate_bets(BetGenerationScope(), dry_run=True)
        self.assertEqual(report.skipped, 1)
        self.assertEqual(report.generated, 0)
        self.assertEqual(len(report.warnings), 1)
        mock_write.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_generated_bets",
        side_effect=RuntimeError("db down"))
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates")
    def test_write_failure_rollbacks_and_propagates(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock) -> None:
        mock_fetch.return_value = [
            GeneratedBet(
                match_id=1,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=2.0,
                probability=55.0)]
        conn = MagicMock()
        with self.assertRaises(RuntimeError):
            generate_bets(BetGenerationScope(), dry_run=False, conn=conn)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        mock_write.assert_called_once()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_generated_bets")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates",
        return_value=[])
    def test_second_generate_pass_with_empty_candidates(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock) -> None:
        conn = MagicMock()
        report = generate_bets(
            BetGenerationScope(), dry_run=False, conn=conn)
        self.assertEqual(report.read, 0)
        self.assertEqual(report.generated, 0)
        self.assertEqual(report.updated, 0)
        mock_write.assert_not_called()
        conn.commit.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_generated_bets")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates",
        return_value=[])
    def test_dry_run_after_success_reports_zero_planned_writes(
            self,
            mock_fetch: MagicMock,
            mock_write: MagicMock) -> None:
        report = generate_bets(BetGenerationScope(), dry_run=True)
        self.assertEqual(report.read, 0)
        self.assertEqual(report.generated, 0)
        self.assertEqual(report.updated, 0)
        self.assertEqual(report.settled, 0)
        self.assertEqual(report.skipped, 0)
        mock_write.assert_not_called()


class TestSettleOutcomes(unittest.TestCase):
    """Settlement batching, skips, and priced-market separation."""

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_dry_run_settles_without_writes(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [_fp_candidate(1), _fp_candidate(2, event_id=2, result="1")],
            []]
        with patch(
                "backend.services.model_statistics_maintenance_service.repo"
                ".write_final_prediction_outcomes") as mock_write_fp:
            with patch(
                    "backend.services.model_statistics_maintenance_service.repo"
                    ".write_bet_outcomes") as mock_write_bets:
                report = settle_outcomes(batch_size=10, dry_run=True)
        self.assertEqual(report.read, 2)
        self.assertEqual(report.settled, 2)
        self.assertEqual(report.updated, 0)
        mock_write_fp.assert_not_called()
        mock_write_bets.assert_not_called()
        mock_bets.assert_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_bet_outcomes",
        return_value=0)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_final_prediction_outcomes",
        return_value=1)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_batching_uses_keyset_pagination(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock,
            mock_write_fp: MagicMock,
            mock_write_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [_fp_candidate(10)],
            [_fp_candidate(20)],
            []]
        conn = MagicMock()
        report = settle_outcomes(
            batch_size=1, dry_run=False, conn=conn)
        self.assertEqual(report.read, 2)
        self.assertEqual(report.settled, 2)
        self.assertEqual(mock_fp.call_count, 3)
        self.assertEqual(
            mock_fp.call_args_list[0].kwargs,
            {"after_id": 0, "limit": 1, "scope": None})
        self.assertEqual(
            mock_fp.call_args_list[1].kwargs,
            {"after_id": 10, "limit": 1, "scope": None})
        self.assertEqual(mock_write_fp.call_count, 2)
        self.assertEqual(conn.commit.call_count, 2)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_skips_invalid_and_unsupported_candidates(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [
                _fp_candidate(
                    1, result="0", home_goals=1, away_goals=0),
                _fp_candidate(
                    2,
                    event_id=999,
                    family="EXACT",
                    event_name="bad-label",
                    home_goals=1,
                    away_goals=1),
                _fp_candidate(3)],
            []]
        report = settle_outcomes(batch_size=50, dry_run=True)
        self.assertEqual(report.skipped, 2)
        self.assertEqual(report.settled, 1)
        self.assertEqual(len(report.warnings), 2)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_bet_outcomes",
        return_value=1)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_final_prediction_outcomes",
        return_value=1)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_goals_settle_finals_but_not_bets(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock,
            mock_write_fp: MagicMock,
            mock_write_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [_fp_candidate(
                50,
                event_id=176,
                family="GOALS",
                event_name="2",
                home_goals=1,
                away_goals=1)],
            []]
        mock_bets.side_effect = [
            [_bet_candidate(7, event_id=1)],
            []]
        conn = MagicMock()
        report = settle_outcomes(
            batch_size=10, dry_run=False, conn=conn)
        self.assertEqual(report.settled, 2)
        fp_rows = mock_write_fp.call_args.args[0]
        self.assertEqual(fp_rows, [(50, 1)])
        bet_rows = mock_write_bets.call_args.args[0]
        self.assertEqual(bet_rows, [(7, 1)])
        # GOALS nigdy nie trafia do ścieżki bets — tylko rynki kursowe
        bet_fetch_kwargs = mock_bets.call_args_list[0].kwargs
        self.assertEqual(bet_fetch_kwargs["limit"], 10)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_final_prediction_outcomes",
        side_effect=RuntimeError("write failed"))
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_settlement_write_failure_rollbacks(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock,
            mock_write_fp: MagicMock) -> None:
        mock_fp.side_effect = [[_fp_candidate(1)], []]
        conn = MagicMock()
        with self.assertRaises(RuntimeError):
            settle_outcomes(batch_size=5, dry_run=False, conn=conn)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_bet_outcomes")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_final_prediction_outcomes")
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions",
        return_value=[])
    def test_second_settle_pass_with_empty_candidates(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock,
            mock_write_fp: MagicMock,
            mock_write_bets: MagicMock) -> None:
        conn = MagicMock()
        report = settle_outcomes(
            batch_size=50, dry_run=False, conn=conn)
        self.assertEqual(report.read, 0)
        self.assertEqual(report.settled, 0)
        self.assertEqual(report.updated, 0)
        self.assertEqual(report.skipped, 0)
        mock_write_fp.assert_not_called()
        mock_write_bets.assert_not_called()
        conn.commit.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_bet_outcomes",
        return_value=0)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".write_final_prediction_outcomes",
        return_value=0)
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_settle_rowcount_zero_does_not_inflate_updated(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock,
            mock_write_fp: MagicMock,
            mock_write_bets: MagicMock) -> None:
        # Kandydat nadal widoczny, ale UPDATE nie zmienia wiersza (idempotencja)
        mock_fp.side_effect = [[_fp_candidate(1)], []]
        conn = MagicMock()
        report = settle_outcomes(
            batch_size=10, dry_run=False, conn=conn)
        self.assertEqual(report.read, 1)
        self.assertEqual(report.settled, 1)
        self.assertEqual(report.updated, 0)
        mock_write_fp.assert_called_once()
        mock_write_bets.assert_not_called()

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions",
        return_value=[])
    def test_dry_run_settle_with_empty_candidates_reports_zero(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        report = settle_outcomes(batch_size=50, dry_run=True)
        self.assertEqual(report.read, 0)
        self.assertEqual(report.settled, 0)
        self.assertEqual(report.updated, 0)
        self.assertEqual(report.generated, 0)

class TestRefreshModelStatistics(unittest.TestCase):
    """Top-level cycle merges generation and settlement reports."""

    @patch(
        "backend.services.model_statistics_maintenance_service.settle_outcomes")
    @patch(
        "backend.services.model_statistics_maintenance_service.generate_bets")
    def test_dry_run_merges_reports_without_connection(
            self,
            mock_generate: MagicMock,
            mock_settle: MagicMock) -> None:
        mock_generate.return_value = StatisticsRefreshReport(
            read=3, generated=3, dry_run=True)
        mock_settle.return_value = StatisticsRefreshReport(
            read=5, settled=4, skipped=1, dry_run=True,
            warnings=["skip"])
        with patch(
                "backend.services.model_statistics_maintenance_service"
                ".get_db_connection") as mock_db:
            report = refresh_model_statistics(
                BetGenerationScope(date_from=date(2026, 7, 27)),
                batch_size=100,
                dry_run=True)
        mock_db.assert_not_called()
        mock_generate.assert_called_once()
        mock_settle.assert_called_once_with(
            100,
            dry_run=True,
            preview=False,
            preview_limit=DEFAULT_PREVIEW_LIMIT,
            scope=None)
        self.assertEqual(report.read, 8)
        self.assertEqual(report.generated, 3)
        self.assertEqual(report.settled, 4)
        self.assertEqual(report.skipped, 1)
        self.assertEqual(report.warnings, ["skip"])
        self.assertTrue(report.dry_run)

    @patch(
        "backend.services.model_statistics_maintenance_service.settle_outcomes")
    @patch(
        "backend.services.model_statistics_maintenance_service.generate_bets")
    @patch(
        "backend.services.model_statistics_maintenance_service"
        ".get_db_connection")
    def test_write_mode_opens_connection_and_propagates_error(
            self,
            mock_db: MagicMock,
            mock_generate: MagicMock,
            mock_settle: MagicMock) -> None:
        conn = MagicMock()
        mock_db.return_value.__enter__.return_value = conn
        mock_generate.side_effect = RuntimeError("upsert failed")
        with self.assertRaises(RuntimeError):
            refresh_model_statistics(
                BetGenerationScope(), dry_run=False)
        mock_generate.assert_called_once()
        mock_settle.assert_not_called()

    def test_rejects_non_positive_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            settle_outcomes(batch_size=0, dry_run=True)

    @patch(
        "backend.services.model_statistics_maintenance_service.settle_outcomes")
    @patch(
        "backend.services.model_statistics_maintenance_service.generate_bets")
    def test_preview_passes_scope_to_settlement(
            self,
            mock_generate: MagicMock,
            mock_settle: MagicMock) -> None:
        scope = BetGenerationScope(match_id=120084)
        mock_generate.return_value = StatisticsRefreshReport(
            dry_run=True, preview=[])
        mock_settle.return_value = StatisticsRefreshReport(
            dry_run=True, preview=[])
        refresh_model_statistics(
            scope, dry_run=True, preview=True, preview_limit=10)
        mock_generate.assert_called_once_with(
            scope,
            dry_run=True,
            preview=True,
            preview_limit=10)
        mock_settle.assert_called_once_with(
            DEFAULT_BATCH_SIZE,
            dry_run=True,
            preview=True,
            preview_limit=10,
            scope=scope)


class TestPreviewPlannedWrites(unittest.TestCase):
    """Dry-run preview samples planned upserts and settlements."""

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_bet_generation_candidates")
    def test_generate_preview_includes_ev_upsert(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            GeneratedBet(
                match_id=10,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=2.0,
                probability=60.0)]
        report = generate_bets(
            BetGenerationScope(match_id=10),
            dry_run=True,
            preview=True)
        self.assertEqual(report.generated, 1)
        self.assertEqual(len(report.preview), 1)
        entry = report.preview[0]
        self.assertEqual(entry["action"], "upsert_bet")
        self.assertEqual(entry["table"], "bets")
        self.assertEqual(entry["match_id"], 10)
        self.assertEqual(entry["after"]["EV"], 0.2)
        self.assertEqual(entry["after"]["odds"], 2.0)
        self.assertIsNone(entry["before"])
        self.assertFalse(report.preview_truncated)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_settle_preview_includes_outcome_update(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [_fp_candidate(7, match_id=55)],
            []]
        report = settle_outcomes(
            batch_size=10, dry_run=True, preview=True)
        self.assertEqual(report.settled, 1)
        self.assertEqual(len(report.preview), 1)
        entry = report.preview[0]
        self.assertEqual(entry["action"], "settle_outcome")
        self.assertEqual(entry["table"], "final_predictions")
        self.assertEqual(entry["id"], 7)
        self.assertEqual(entry["match_id"], 55)
        self.assertEqual(entry["before"], {"outcome": None})
        self.assertEqual(entry["after"], {"outcome": 1})
        mock_fp.assert_called_with(
            after_id=7, limit=10, scope=None)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_preview_limit_truncates_samples(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        mock_fp.side_effect = [
            [_fp_candidate(1), _fp_candidate(2), _fp_candidate(3)],
            []]
        report = settle_outcomes(
            batch_size=10,
            dry_run=True,
            preview=True,
            preview_limit=2)
        self.assertEqual(report.settled, 3)
        self.assertEqual(len(report.preview), 2)
        self.assertTrue(report.preview_truncated)

    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_bets",
        return_value=[])
    @patch(
        "backend.services.model_statistics_maintenance_service.repo"
        ".fetch_pending_final_predictions")
    def test_preview_passes_scope_to_fetch(
            self,
            mock_fp: MagicMock,
            mock_bets: MagicMock) -> None:
        scope = BetGenerationScope(match_id=120084)
        mock_fp.side_effect = [[], []]
        settle_outcomes(
            batch_size=5,
            dry_run=True,
            preview=True,
            scope=scope)
        mock_fp.assert_called_once_with(
            after_id=0, limit=5, scope=scope)

    def test_preview_rejected_with_writes(self) -> None:
        with self.assertRaises(ValueError):
            generate_bets(
                BetGenerationScope(),
                dry_run=False,
                preview=True)


class TestReportMerge(unittest.TestCase):
    """Report aggregation helpers."""

    def test_merge_sums_counters(self) -> None:
        left = StatisticsRefreshReport(
            read=1, generated=1, warnings=["a"], dry_run=True,
            preview=[{"action": "upsert_bet"}])
        right = StatisticsRefreshReport(
            read=2, settled=2, skipped=1, warnings=["b"], dry_run=True,
            preview=[{"action": "settle_outcome"}],
            preview_truncated=True)
        merged = left.merge(right)
        self.assertEqual(merged.read, 3)
        self.assertEqual(merged.generated, 1)
        self.assertEqual(merged.settled, 2)
        self.assertEqual(merged.skipped, 1)
        self.assertEqual(merged.warnings, ["a", "b"])
        self.assertEqual(len(merged.preview), 2)
        self.assertTrue(merged.preview_truncated)


if __name__ == "__main__":
    unittest.main()
