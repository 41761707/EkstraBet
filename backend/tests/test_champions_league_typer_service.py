"""Unit tests for Champions League Typer domain rules."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from backend.repositories import champions_league_typer_repository as repo
from backend.services import champions_league_typer_service as service

_REPO = "backend.services.champions_league_typer_service.repository"
_SPECIAL_ROUNDS = (
    "backend.services.champions_league_typer_service"
    ".league_repository.fetch_special_round_names")
_GAME_DATE = datetime(2026, 9, 16, 21, 0)
_PUBLISHED_AT = datetime(2026, 9, 10, 12, 0)
_CHANGED_AT = datetime(2026, 9, 11, 18, 30)
_GROUP_IDS = list(range(101, 110))


def _settings(count: int = 9) -> MagicMock:
    settings = MagicMock()
    settings.typer_lm_group_match_count = count
    return settings


def _publication_row(
        match_id: int, round_number: int = 1) -> dict[str, object]:
    return {
        "typer_match_id": match_id + 1000,
        "match_id": match_id,
        "season_id": 13,
        "round_number": round_number,
        "published_by": 7,
        "published_at": _PUBLISHED_AT
    }


def _candidate_row(
        match_id: int,
        round_number: int = 900,
        is_published: bool = False) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season_id": 13,
        "round_number": round_number,
        "game_date": _GAME_DATE,
        "home_team_id": 1,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": 2,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "is_published": is_published,
        "has_complete_superbet_odds": False
    }


def _group_candidates(
        match_ids: list[int],
        published_ids: list[int] | None = None) -> list[dict[str, object]]:
    published = set(published_ids or [])
    return [
        _candidate_row(
            match_id,
            round_number=1,
            is_published=match_id in published)
        for match_id in match_ids]


def _dashboard_match_row(
        match_id: int,
        *,
        round_number: int = 1,
        result: str | None = None,
        odds_home: float | None = None,
        odds_draw: float | None = None,
        odds_away: float | None = None,
        selected_event_id: int | None = None) -> dict[str, object]:
    return {
        "typer_match_id": match_id + 1000,
        "match_id": match_id,
        "season_id": 13,
        "round_number": round_number,
        "published_at": _PUBLISHED_AT,
        "game_date": _GAME_DATE,
        "is_locked": False,
        "result": result,
        "home_team_id": 1,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": 2,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "odds_home": odds_home,
        "odds_draw": odds_draw,
        "odds_away": odds_away,
        "prediction_id": None if selected_event_id is None else 10,
        "selected_event_id": selected_event_id
    }


def _change_row(
        match_id: int,
        *,
        previous_event_id: int | None,
        new_event_id: int) -> dict[str, object]:
    return {
        "id": 1,
        "prediction_id": 10,
        "match_id": match_id,
        "user_uuid": "u-1",
        "display_name": "Ada",
        "previous_selected_event_id": previous_event_id,
        "new_selected_event_id": new_event_id,
        "changed_at": _CHANGED_AT
    }


def _revealed_row(
        match_id: int,
        *,
        round_number: int = 1,
        user_uuid: str | None = "u-1",
        display_name: str | None = "Ada",
        selected_event_id: int | None = 1,
        game_date: datetime | None = None) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season_id": 13,
        "round_number": round_number,
        "game_date": game_date or _GAME_DATE,
        "home_team_id": 1,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": 2,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "user_uuid": user_uuid,
        "display_name": display_name,
        "selected_event_id": selected_event_id
    }


def _revealed_document(
        rows: list[dict[str, object]],
        *,
        round_number: int = 1) -> dict[str, object]:
    return {
        "season_id": 13,
        "round_number": round_number,
        "rows": rows
    }


def _saved_row(
        outcome_event_id: int,
        *,
        previous_event_id: int | None,
        audit_written: bool) -> dict[str, object]:
    return {
        "prediction_id": 10,
        "typer_match_id": 50,
        "match_id": 101,
        "user_id": 4,
        "selected_event_id": outcome_event_id,
        "previous_selected_event_id": previous_event_id,
        "audit_written": audit_written,
        "created_at": _CHANGED_AT,
        "updated_at": _CHANGED_AT
    }


class TestConstants(unittest.TestCase):
    """Service constants stay aligned with the repository layer."""

    def test_league_bookmaker_and_event_ids_match_repository(self) -> None:
        self.assertEqual(
            service.CHAMPIONS_LEAGUE_ID, repo.CHAMPIONS_LEAGUE_ID)
        self.assertEqual(
            service.SUPERBET_BOOKMAKER_ID, repo.SUPERBET_BOOKMAKER_ID)
        self.assertEqual(service.HOME_EVENT_ID, repo.HOME_EVENT_ID)
        self.assertEqual(service.DRAW_EVENT_ID, repo.DRAW_EVENT_ID)
        self.assertEqual(service.AWAY_EVENT_ID, repo.AWAY_EVENT_ID)


class TestOutcomeMapping(unittest.TestCase):
    """1X2 letters map to Superbet events 1/2/3."""

    def test_maps_one_x_two_to_events(self) -> None:
        self.assertEqual(service.event_id_for_outcome("1"), 1)
        self.assertEqual(service.event_id_for_outcome("X"), 2)
        self.assertEqual(service.event_id_for_outcome("2"), 3)

    def test_rejects_outcome_outside_one_x_two(self) -> None:
        with self.assertRaises(service.TyperValidationError):
            service.event_id_for_outcome("0")


class TestScorePrediction(unittest.TestCase):
    """Regulation 1X2 scoring; extra time and penalties are ignored."""

    def test_correct_home_uses_home_odds(self) -> None:
        self.assertEqual(
            service.score_prediction("1", "1", 1.85, 3.4, 4.2),
            1.85)

    def test_correct_draw_uses_draw_odds(self) -> None:
        self.assertEqual(
            service.score_prediction("X", "X", 1.85, 3.4, 4.2),
            3.4)

    def test_correct_away_uses_away_odds(self) -> None:
        self.assertEqual(
            service.score_prediction("2", "2", 1.85, 3.4, 4.2),
            4.2)

    def test_wrong_pick_is_zero_without_odds(self) -> None:
        self.assertEqual(
            service.score_prediction("1", "X", None, None, None),
            0.0)

    def test_hit_without_odds_is_unsettled(self) -> None:
        self.assertIsNone(
            service.score_prediction("1", "1", None, 3.4, 4.2))

    def test_missing_regulation_result_is_unsettled(self) -> None:
        self.assertIsNone(
            service.score_prediction(None, "1", 1.85, 3.4, 4.2))

    def test_non_one_x_two_result_is_unsettled(self) -> None:
        self.assertIsNone(
            service.score_prediction("0", "1", 1.85, 3.4, 4.2))

    def test_does_not_consult_extra_time_or_penalties(self) -> None:
        # punktacja czyta wyłącznie matches.result; brak argumentu na dogrywkę
        self.assertEqual(
            service.score_prediction.__code__.co_argcount, 5)
        self.assertNotIn(
            "extra_time", service.score_prediction.__code__.co_varnames)
        self.assertNotIn(
            "penalties", service.score_prediction.__code__.co_varnames)


class TestPublishMatches(unittest.TestCase):
    """Group stage needs exactly 9; knockout needs the unpublished set."""

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_group_stage_publishes_nine_without_odds(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = _group_candidates(_GROUP_IDS)
        mock_publish.return_value = [
            _publication_row(match_id) for match_id in _GROUP_IDS]
        result = service.publish_matches(13, 1, list(_GROUP_IDS), admin_id=7)
        self.assertEqual(len(result), 9)
        self.assertEqual(result[0]["match_id"], 101)
        self.assertNotIn("published_by", result[0])
        mock_publish.assert_called_once_with(
            13, 1, _GROUP_IDS, 7, group_match_count=9)

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_rejects_five_group_stage_matches(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = _group_candidates(list(range(101, 119)))
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 1, [101, 102, 103, 104, 105], 7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_rejects_seven_group_stage_matches(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = _group_candidates(list(range(1, 19)))
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 8, list(range(1, 8)), 7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_rejects_second_group_stage_batch_of_nine(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        first_batch = list(_GROUP_IDS)
        second_batch = list(range(201, 210))
        mock_candidates.return_value = (
            _group_candidates(first_batch, published_ids=first_batch)
            + _group_candidates(second_batch))
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 1, second_batch, admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_republish_of_same_group_ids_is_conflict(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = _group_candidates(
            _GROUP_IDS, published_ids=_GROUP_IDS)
        with self.assertRaises(service.TyperConflictError):
            service.publish_matches(13, 1, list(_GROUP_IDS), admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(8))
    def test_configured_group_count_eight_is_enforced(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        eight_ids = list(range(101, 109))
        mock_candidates.return_value = _group_candidates(eight_ids)
        mock_publish.return_value = [
            _publication_row(match_id) for match_id in eight_ids]
        result = service.publish_matches(13, 1, eight_ids, admin_id=7)
        self.assertEqual(len(result), 8)
        mock_publish.assert_called_once_with(
            13, 1, eight_ids, 7, group_match_count=8)
        mock_publish.reset_mock()
        nine_ids = list(range(101, 110))
        mock_candidates.return_value = _group_candidates(nine_ids)
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 1, nine_ids, admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_rejects_duplicate_match_ids(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 1, [101, 101, *range(102, 110)], 7)
        mock_candidates.assert_not_called()
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_rejects_mixed_rounds_in_group_stage(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = _group_candidates(_GROUP_IDS)
        mixed_ids = [*_GROUP_IDS[:8], 999]
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 1, mixed_ids, admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    def test_knockout_publishes_complete_unpublished_set(
            self,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = [
            _candidate_row(201, is_published=True),
            _candidate_row(202),
            _candidate_row(203)]
        mock_publish.return_value = [
            _publication_row(202, 900),
            _publication_row(203, 900)]
        result = service.publish_matches(13, 900, [202, 203], admin_id=7)
        self.assertEqual([row["match_id"] for row in result], [202, 203])
        mock_publish.assert_called_once_with(
            13, 900, [202, 203], 7, group_match_count=None)

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    def test_rejects_incomplete_knockout_set(
            self,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = [
            _candidate_row(202),
            _candidate_row(203)]
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 900, [202], admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    def test_rejects_already_published_ids_in_knockout_payload(
            self,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.return_value = [
            _candidate_row(201, is_published=True),
            _candidate_row(202),
            _candidate_row(203)]
        with self.assertRaises(service.TyperConflictError):
            service.publish_matches(13, 900, [201, 202, 203], admin_id=7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    def test_unsupported_round_is_validation_error(
            self, mock_publish: MagicMock) -> None:
        with self.assertRaises(service.TyperValidationError):
            service.publish_matches(13, 50, list(_GROUP_IDS), 7)
        mock_publish.assert_not_called()

    @patch(f"{_REPO}.publish_matches")
    @patch(f"{_REPO}.fetch_admin_candidates")
    @patch(
        "backend.services.champions_league_typer_service.get_settings",
        return_value=_settings(9))
    def test_foreign_season_is_not_found(
            self,
            _mock_settings: MagicMock,
            mock_candidates: MagicMock,
            mock_publish: MagicMock) -> None:
        mock_candidates.side_effect = repo.TyperNotFoundError(
            "Season not found")
        with self.assertRaises(service.TyperNotFoundError):
            service.publish_matches(13, 1, list(_GROUP_IDS), 7)
        mock_publish.assert_not_called()


class TestSavePrediction(unittest.TestCase):
    """UPSERT before kick-off; deadline conflicts stay conflicts."""

    @patch(f"{_REPO}.save_prediction")
    def test_first_save_maps_home_and_null_previous(
            self, mock_save: MagicMock) -> None:
        mock_save.return_value = _saved_row(
            1, previous_event_id=None, audit_written=True)
        result = service.save_prediction(4, 101, "1")
        mock_save.assert_called_once_with(4, 101, 1)
        self.assertEqual(result["outcome"], "1")
        self.assertIsNone(result["previous_outcome"])
        self.assertTrue(result["audit_written"])
        self.assertNotIn("user_id", result)

    @patch(f"{_REPO}.save_prediction")
    def test_change_from_one_to_draw(
            self, mock_save: MagicMock) -> None:
        mock_save.return_value = _saved_row(
            2, previous_event_id=1, audit_written=True)
        result = service.save_prediction(4, 101, "X")
        mock_save.assert_called_once_with(4, 101, 2)
        self.assertEqual(result["outcome"], "X")
        self.assertEqual(result["previous_outcome"], "1")

    @patch(f"{_REPO}.save_prediction")
    def test_identical_pick_is_noop(
            self, mock_save: MagicMock) -> None:
        mock_save.return_value = _saved_row(
            1, previous_event_id=1, audit_written=False)
        result = service.save_prediction(4, 101, "1")
        self.assertFalse(result["audit_written"])
        self.assertEqual(result["previous_outcome"], "1")

    @patch(f"{_REPO}.save_prediction")
    def test_kickoff_conflict_is_mapped(
            self, mock_save: MagicMock) -> None:
        mock_save.side_effect = repo.TyperConflictError(
            "Prediction cannot be saved after kickoff")
        with self.assertRaises(service.TyperConflictError):
            service.save_prediction(4, 101, "2")


class TestDashboardAndHistory(unittest.TestCase):
    """Dashboard is private, grouped by round, and scores regulation 1X2."""

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_dashboard")
    def test_groups_rounds_and_attaches_private_changes(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = {
            "season_id": 13,
            "matches": [
                _dashboard_match_row(
                    101,
                    result="X",
                    odds_draw=3.1,
                    selected_event_id=2),
                _dashboard_match_row(201, round_number=900)
            ],
            "changes": [
                _change_row(101, previous_event_id=None, new_event_id=2)
            ]
        }
        document = service.get_dashboard(4, 13)
        self.assertEqual(document["season_id"], 13)
        self.assertEqual(len(document["rounds"]), 2)
        first = document["rounds"][0]["matches"][0]
        self.assertEqual(first["outcome"], "X")
        self.assertEqual(first["points"], 3.1)
        self.assertEqual(first["changes"][0]["previous_outcome"], None)
        self.assertEqual(first["changes"][0]["new_outcome"], "X")
        self.assertIsNone(document["rounds"][1]["matches"][0]["odds_home"])

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_dashboard")
    def test_wrong_pick_scores_zero_and_hit_without_odds_is_unsettled(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = {
            "season_id": 13,
            "matches": [
                _dashboard_match_row(
                    101, result="1", selected_event_id=2),
                _dashboard_match_row(
                    102, result="1", selected_event_id=1)
            ],
            "changes": []
        }
        document = service.get_dashboard(4, 13)
        matches = document["rounds"][0]["matches"]
        self.assertEqual(matches[0]["points"], 0.0)
        self.assertIsNone(matches[1]["points"])

    @patch(
        _SPECIAL_ROUNDS,
        return_value={
            973: "1/8-FINAŁU",
            972: "ĆWIERĆFINAŁ",
            900: "Baraże"
        })
    @patch(f"{_REPO}.fetch_dashboard")
    def test_dashboard_round_labels_keep_knockout_rounds_distinct(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = {
            "season_id": 13,
            "matches": [
                _dashboard_match_row(101, round_number=973),
                _dashboard_match_row(201, round_number=972),
                _dashboard_match_row(301, round_number=900)
            ],
            "changes": []
        }
        document = service.get_dashboard(4, 13)
        labels = [row["round_label"] for row in document["rounds"]]
        self.assertEqual(
            labels, ["1/8-FINAŁU", "ĆWIERĆFINAŁ", "Baraże"])

    @patch(f"{_REPO}.fetch_own_prediction_history")
    def test_own_history_maps_events_to_outcomes(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            _change_row(101, previous_event_id=None, new_event_id=1),
            _change_row(101, previous_event_id=1, new_event_id=2)
        ]
        rows = service.get_own_prediction_history(4, 101)
        self.assertEqual(rows[0]["new_outcome"], "1")
        self.assertEqual(rows[1]["previous_outcome"], "1")
        self.assertEqual(rows[1]["new_outcome"], "X")

    @patch(f"{_REPO}.fetch_admin_prediction_history")
    def test_admin_history_passes_public_uuid(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = []
        service.get_admin_prediction_history(
            "u-1", match_id=101, season_id=13)
        mock_fetch.assert_called_once_with("u-1", 101, 13)

    @patch(f"{_REPO}.fetch_leaderboard")
    def test_leaderboard_delegates_to_repository(
            self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{
            "place": 1,
            "user_uuid": "u-1",
            "display_name": "Ada",
            "total_points": 5.5,
            "correct_predictions": 2,
            "settled_predictions": 3
        }]
        rows = service.get_leaderboard(13)
        self.assertEqual(rows[0]["total_points"], 5.5)
        mock_fetch.assert_called_once_with(13)


class TestGetRevealedPredictions(unittest.TestCase):
    """Revealed picks are grouped, mapped to 1X2 and never 404 when empty."""

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_maps_events_one_x_two(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(101, selected_event_id=1),
            _revealed_row(
                102,
                user_uuid="u-2",
                display_name="Ben",
                selected_event_id=2),
            _revealed_row(
                103,
                user_uuid="u-3",
                display_name="Cora",
                selected_event_id=3)
        ])
        document = service.get_revealed_predictions(13, 1)
        outcomes = [
            match["picks"][0]["outcome"] for match in document["matches"]]
        self.assertEqual(outcomes, ["1", "X", "2"])
        mock_fetch.assert_called_once_with(13, 1)

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_groups_many_picks_and_repeats_one_user(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(101, selected_event_id=1),
            _revealed_row(
                101,
                user_uuid="u-2",
                display_name="Ben",
                selected_event_id=3),
            _revealed_row(102, selected_event_id=2)
        ])
        document = service.get_revealed_predictions(13, 1)
        first, second = document["matches"]
        self.assertEqual(first["match_id"], 101)
        self.assertEqual(
            [(pick["user_uuid"], pick["outcome"]) for pick in first["picks"]],
            [("u-1", "1"), ("u-2", "2")])
        self.assertEqual(second["picks"][0]["user_uuid"], "u-1")
        self.assertEqual(second["picks"][0]["outcome"], "X")
        self.assertEqual(
            [row["user_uuid"] for row in document["participants"]],
            ["u-1", "u-2"])

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_sorts_participants_case_insensitively_then_uuid(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(
                101,
                user_uuid="u-2",
                display_name="ada",
                selected_event_id=1),
            _revealed_row(
                101,
                user_uuid="u-1",
                display_name="Ada",
                selected_event_id=2),
            _revealed_row(
                102,
                user_uuid="z-1",
                display_name="Zoe",
                selected_event_id=3)
        ])
        document = service.get_revealed_predictions(13, 1)
        self.assertEqual(
            [row["user_uuid"] for row in document["participants"]],
            ["u-1", "u-2", "z-1"])
        self.assertEqual(
            [row["display_name"] for row in document["participants"]],
            ["Ada", "ada", "Zoe"])

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_uses_coalesced_username_as_display_name(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        # SQL COALESCE zwraca username, gdy display_name jest puste
        mock_fetch.return_value = _revealed_document([
            _revealed_row(
                101,
                user_uuid="u-9",
                display_name="bob",
                selected_event_id=1)
        ])
        document = service.get_revealed_predictions(13, 1)
        self.assertEqual(document["participants"][0]["display_name"], "bob")
        self.assertEqual(document["participants"][0]["user_uuid"], "u-9")

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_empty_round_returns_empty_lists(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([])
        document = service.get_revealed_predictions(13, 1)
        self.assertEqual(document["season_id"], 13)
        self.assertEqual(document["round_number"], 1)
        self.assertEqual(document["round_label"], "1")
        self.assertEqual(document["participants"], [])
        self.assertEqual(document["matches"], [])

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_started_match_without_picks_stays_in_matches(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(
                101,
                user_uuid=None,
                display_name=None,
                selected_event_id=None)
        ])
        document = service.get_revealed_predictions(13, 1)
        self.assertEqual(document["participants"], [])
        self.assertEqual(len(document["matches"]), 1)
        self.assertEqual(document["matches"][0]["picks"], [])
        self.assertEqual(document["matches"][0]["home_team"]["name"], "Home")

    @patch(_SPECIAL_ROUNDS, return_value={900: "Baraże"})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_knockout_round_uses_special_label(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document(
            [_revealed_row(201, round_number=900, selected_event_id=1)],
            round_number=900)
        document = service.get_revealed_predictions(13, 900)
        self.assertEqual(document["round_label"], "Baraże")
        mock_fetch.assert_called_once_with(13, 900)

    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_rejects_round_nine_and_899(
            self, mock_fetch: MagicMock) -> None:
        for round_number in (9, 899):
            with self.subTest(round_number=round_number):
                with self.assertRaises(service.TyperValidationError):
                    service.get_revealed_predictions(13, round_number)
        mock_fetch.assert_not_called()

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_unsupported_event_is_validation_error(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(101, selected_event_id=99)
        ])
        with self.assertRaises(service.TyperValidationError):
            service.get_revealed_predictions(13, 1)

    @patch(_SPECIAL_ROUNDS, return_value={})
    @patch(f"{_REPO}.fetch_revealed_predictions")
    def test_contract_omits_internal_and_audit_fields(
            self,
            mock_fetch: MagicMock,
            _mock_special: MagicMock) -> None:
        mock_fetch.return_value = _revealed_document([
            _revealed_row(101, selected_event_id=2)
        ])
        document = service.get_revealed_predictions(13, 1)
        match = document["matches"][0]
        self.assertNotIn("user_id", document)
        self.assertNotIn("prediction_id", match)
        self.assertNotIn("changed_at", match)
        self.assertNotIn("selected_event_id", match)
        self.assertNotIn("odds_home", match)
        self.assertEqual(match["picks"][0]["outcome"], "X")


class TestRemovePublication(unittest.TestCase):
    """Removal keeps the plan's admin_id argument without persisting it."""

    @patch(f"{_REPO}.remove_publication")
    def test_calls_repository_without_admin_id(
            self, mock_remove: MagicMock) -> None:
        service.remove_publication(101, admin_id=7)
        mock_remove.assert_called_once_with(101)

    @patch(f"{_REPO}.remove_publication")
    def test_conflict_is_mapped(self, mock_remove: MagicMock) -> None:
        mock_remove.side_effect = repo.TyperConflictError(
            "Publication cannot be removed while picks exist")
        with self.assertRaises(service.TyperConflictError):
            service.remove_publication(101, admin_id=7)


if __name__ == "__main__":
    unittest.main()
