"""Tests for lineup prediction, shared features and shadow routing."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import ResultPrediction
from models.pipeline.core.model_lineup import LineupEntry
from models.pipeline.core.model_lineup import ModelLineup
from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION
from models.pipeline.core.model_roles import FamilyRole
from models.pipeline.core.model_roles import ModelRoles
from models.pipeline.prediction.lineup_runner import build_lineup_predictors
from models.pipeline.prediction.lineup_runner import lineup_rating_params
from models.pipeline.prediction.lineup_runner import persist_lineup_prediction
from models.pipeline.prediction.lineup_runner import predict_lineup_pair


def _config(
        model_name: str,
        task_type: str,
        events: dict[str, int],
        ratings: dict[str, Any] | None = None) -> FutureEventsRunConfig:
    return FutureEventsRunConfig.model_validate({
        "model_name": model_name,
        "sport_id": 1,
        "task_type": task_type,
        "artifact_dir": "models/artifacts/unused",
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "unused",
        "trainer": "unused",
        "output_columns": ["value"],
        "feature_config": {},
        "events": events,
        "ratings": ratings or {"elo": True}})


def _entry(
        model_name: str,
        model_id: int,
        task_type: str,
        status: str,
        family_id: int,
        events: dict[str, int] | None = None,
        ratings: dict[str, Any] | None = None) -> LineupEntry:
    mapped = events or {
        "result_home": 1,
        "result_draw": 2,
        "result_away": 3}
    return LineupEntry(
        model_name=model_name,
        model_id=model_id,
        config_path=Path(f"{model_name}.json"),
        config=_config(model_name, task_type, mapped, ratings),
        family_statuses={family_id: status})


class _RecordingPredictor:
    """Stand-in predictor that records the feature cache it received."""

    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.cache: dict[Any, Any] | None = None

    def predict_pair(
            self,
            matchup: MatchupInput,
            *,
            context: object,
            feature_cache: dict[Any, Any]) -> dict[str, object]:
        self.cache = feature_cache
        feature_cache["calls"] = feature_cache.get("calls", 0) + 1
        return {"marker": self.marker, "match_id": matchup.match_id}


def _matchup() -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=20,
        as_of_date=date(2026, 7, 23),
        league_id=1,
        match_id=123)


def _result_roles() -> ModelRoles:
    return ModelRoles(
        roles=(
            FamilyRole(
                8,
                "FOOTBALL_RESULT_V2",
                1,
                MODEL_STATUS_CHAMPION,
                MODEL_STATUS_CHAMPION),
            FamilyRole(
                9,
                "FOOTBALL_RESULT_V3",
                1,
                MODEL_STATUS_CHALLENGER,
                MODEL_STATUS_CHALLENGER)),
        active_by_model={8: 1, 9: 0})


def test_build_lineup_predictors_slots_config_by_task_type() -> None:
    result_entry = _entry(
        "FOOTBALL_RESULT_V2", 8, "result", MODEL_STATUS_CHAMPION, 1)
    btts_entry = _entry(
        "FOOTBALL_BTTS_V2",
        9,
        "btts",
        MODEL_STATUS_CHAMPION,
        2,
        events={"btts_yes": 4, "btts_no": 5},
        ratings={"elo": False})
    goals_entry = _entry(
        "FOOTBALL_GOALS_POISSON_V1",
        10,
        "goals_poisson",
        MODEL_STATUS_CHAMPION,
        3,
        events={"over_25": 6})
    lineup = ModelLineup(entries=(result_entry, btts_entry, goals_entry))
    created: list[dict[str, object]] = []

    def _factory(**kwargs: object) -> object:
        created.append(kwargs)
        return object()

    with patch(
            "models.pipeline.prediction.lineup_runner.FutureEventsPredictor",
            new=_factory):
        built = build_lineup_predictors(lineup)
    assert [entry.model_name for entry, _predictor in built] == [
        "FOOTBALL_RESULT_V2",
        "FOOTBALL_BTTS_V2",
        "FOOTBALL_GOALS_POISSON_V1"]
    assert created == [
        {"result_config": result_entry.config},
        {"btts_config": btts_entry.config},
        {"goals_config": goals_entry.config}]
    assert lineup_rating_params(lineup) == [
        result_entry.config.ratings,
        btts_entry.config.ratings,
        goals_entry.config.ratings]


def test_predict_lineup_pair_shares_one_feature_cache() -> None:
    champion = _entry(
        "FOOTBALL_RESULT_V2", 8, "result", MODEL_STATUS_CHAMPION, 1)
    challenger = _entry(
        "FOOTBALL_RESULT_V3", 9, "result", MODEL_STATUS_CHALLENGER, 1)
    first = _RecordingPredictor("champion")
    second = _RecordingPredictor("challenger")
    cache: dict[Any, Any] = {}
    predicted = predict_lineup_pair(
        _matchup(),
        [(champion, first), (challenger, second)],
        context=None,
        feature_cache=cache)
    assert first.cache is cache
    assert second.cache is cache
    assert cache["calls"] == 2
    assert predicted == {
        "FOOTBALL_RESULT_V2": {"marker": "champion", "match_id": 123},
        "FOOTBALL_RESULT_V3": {"marker": "challenger", "match_id": 123}}


def test_persist_uses_one_model_id_per_entry() -> None:
    champion = _entry(
        "FOOTBALL_RESULT_V2", 8, "result", MODEL_STATUS_CHAMPION, 1)
    challenger = _entry(
        "FOOTBALL_BTTS_V2",
        9,
        "btts",
        MODEL_STATUS_CHALLENGER,
        2,
        events={"btts_yes": 4, "btts_no": 5})
    seen: list[dict[str, int]] = []

    def _map(
            match_id: int,
            prediction: dict[str, object],
            model_ids: dict[str, int],
            event_ids: dict[str, int],
            select_finals: bool = False) -> list[object]:
        del prediction, event_ids, select_finals
        seen.append(dict(model_ids))
        from models.pipeline.core.config import PredictionWriteRow
        model_id = next(iter(model_ids.values()))
        # Zdarzenie musi należeć do rodziny, na którą model ma rolę.
        event_id = 1 if model_id == 8 else 4
        return [PredictionWriteRow(
            match_id=match_id,
            model_id=model_id,
            event_id=event_id,
            value=0.5,
            is_final=False)]

    roles = ModelRoles(
        roles=(
            FamilyRole(8, "FOOTBALL_RESULT_V2", 1, MODEL_STATUS_CHAMPION),
            FamilyRole(9, "FOOTBALL_BTTS_V2", 2, MODEL_STATUS_CHALLENGER)),
        active_by_model={8: 1, 9: 0})
    with patch(
            "models.pipeline.prediction.lineup_runner.map_predictions_to_rows",
            side_effect=_map), patch(
            "models.pipeline.prediction.lineup_runner.persist_routed_rows",
            side_effect=[(1, 0), (0, 1)]):
        written = persist_lineup_prediction(
            _matchup(),
            [(champion, object()), (challenger, object())],
            {
                "FOOTBALL_RESULT_V2": {"result": {}},
                "FOOTBALL_BTTS_V2": {"btts": {}}},
            roles,
            False,
            event_families={1: 1, 4: 2, 5: 2})
    assert seen == [{"result": 8}, {"btts": 9}]
    assert written == {"published": 1, "shadow": 1}


def test_persist_routes_challenger_rows_to_shadow() -> None:
    champion = _entry(
        "FOOTBALL_RESULT_V2", 8, "result", MODEL_STATUS_CHAMPION, 1)
    challenger = _entry(
        "FOOTBALL_RESULT_V3", 9, "result", MODEL_STATUS_CHALLENGER, 1)
    prediction = {
        "result": ResultPrediction(p_home=0.5, p_draw=0.3, p_away=0.2)}
    with patch(
            "models.pipeline.prediction.lineup_runner.persist_routed_rows",
            return_value=(0, 0)) as persist:
        persist_lineup_prediction(
            _matchup(),
            [(champion, object()), (challenger, object())],
            {
                "FOOTBALL_RESULT_V2": prediction,
                "FOOTBALL_RESULT_V3": prediction},
            _result_roles(),
            True,
            event_families={1: 1, 2: 1, 3: 1})
    published_rows = persist.call_args_list[0].args[0]
    shadow_rows = persist.call_args_list[1].args[0]
    assert published_rows
    assert all(row.model_id == 8 for row in published_rows)
    assert any(row.is_final for row in published_rows)
    assert shadow_rows
    assert all(row.model_id == 9 for row in shadow_rows)
    assert all(row.is_final is False for row in shadow_rows)


def test_persist_loads_event_families_once_when_omitted() -> None:
    champion = _entry(
        "FOOTBALL_RESULT_V2", 8, "result", MODEL_STATUS_CHAMPION, 1)
    challenger = _entry(
        "FOOTBALL_RESULT_V3", 9, "result", MODEL_STATUS_CHALLENGER, 1)
    prediction = {
        "result": ResultPrediction(p_home=0.4, p_draw=0.4, p_away=0.2)}
    with patch(
            "models.pipeline.prediction.lineup_runner.fetch_event_family_ids",
            return_value={1: 1, 2: 1, 3: 1}) as fetch, patch(
            "models.pipeline.prediction.lineup_runner.persist_routed_rows",
            return_value=(1, 0)):
        persist_lineup_prediction(
            _matchup(),
            [(champion, object()), (challenger, object())],
            {
                "FOOTBALL_RESULT_V2": prediction,
                "FOOTBALL_RESULT_V3": prediction},
            _result_roles(),
            False)
    fetch.assert_called_once()
    assert set(fetch.call_args.args[0]) == {1, 2, 3}
