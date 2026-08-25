"""Tests for optional single-family future-event prediction."""

from __future__ import annotations

import json
import logging
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import tqdm as tqdm_module
import tqdm.std as tqdm_std

from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import _future_predictor
from models.pipeline.core.config import BttsPrediction
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import SequenceBatch
from models.pipeline.persistence.prediction_writer import (
    map_predictions_to_rows)
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor,
    LoadedFutureModels)


def _matchup() -> MatchupInput:
    return MatchupInput(
        home_team_id=10,
        away_team_id=945,
        league_id=1,
        season_id=1,
        as_of_date=date(2026, 7, 24),
        match_id=None)


def _btts_config() -> FutureEventsRunConfig:
    return FutureEventsRunConfig(
        model_name="FOOTBALL_BTTS_V2",
        task_type="btts",
        model_version="2.0.0",
        artifact_dir="models/artifacts/dev/football_btts_v2",
        feature_config={},
        feature_builder="FutureEventsFeatureBuilder",
        labeler="FootballBttsLabeler",
        trainer="LstmTrainer",
        output_columns=["p_yes", "p_no"],
        window_size=8,
        events={"btts_yes": 6, "btts_no": 172})


def _batch() -> SequenceBatch:
    return SequenceBatch(
        X_home=np.zeros((1, 2, 3), dtype=float),
        X_away=np.zeros((1, 2, 3), dtype=float),
        X_static=np.zeros((1, 4), dtype=float))


def test_predict_pair_returns_only_btts_when_other_configs_missing() -> None:
    model = MagicMock()
    model.predict.return_value = np.asarray([[0.4, 0.6]], dtype=float)
    predictor = FutureEventsPredictor(
        btts_config=_btts_config(),
        models=LoadedFutureModels(btts_model=model),
        feature_provider=lambda _matchup, _config: _batch())

    payload = predictor.predict_pair(_matchup())

    assert set(payload) == {"btts"}
    assert isinstance(payload["btts"], BttsPrediction)
    assert payload["btts"].p_yes == pytest.approx(0.6)
    assert payload["btts"].p_no == pytest.approx(0.4)
    model.predict.assert_called_once()


def test_predictor_requires_at_least_one_config() -> None:
    with pytest.raises(ValueError, match="At least one"):
        FutureEventsPredictor()


def test_mapping_supports_btts_only_payload() -> None:
    rows = map_predictions_to_rows(
        100,
        {"btts": BttsPrediction(0.7, 0.3)},
        {"btts": 11},
        {"btts_yes": 6, "btts_no": 172},
        select_finals=True)

    assert len(rows) == 2
    finals = {row.event_id for row in rows if row.is_final}
    assert finals == {6}


def test_cli_accepts_btts_config_without_result_or_goals() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "predict-pair",
        "--btts_config",
        "models/configs/training/football_btts_v2.json",
        "--home",
        "10",
        "--away",
        "945",
        "--as-of",
        "2026-07-24"
    ])

    assert args.btts_config is not None
    assert args.result_config is None
    assert args.goals_config is None


def test_future_predictor_rejects_empty_config_set() -> None:
    args = SimpleNamespace(
        result_config=None,
        btts_config=None,
        goals_config=None)
    with pytest.raises(ValueError, match="At least one"):
        _future_predictor(args)


def test_run_predict_batch_skips_insufficient_history_and_continues(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    good = MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=101)
    bad = MatchupInput(
        home_team_id=30,
        away_team_id=40,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=102)
    predictor = MagicMock()
    predictor.predict_pair.side_effect = [
        ValueError("Insufficient match history for team id(s): 30"),
        {"btts": BttsPrediction(0.55, 0.45)}
    ]
    monkeypatch.setattr(
        cli_module,
        "_load_batch_matchups",
        lambda _args: [bad.model_dump(), good.model_dump()])
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "_build_predict_history_context",
        lambda _predictor, _matchups: None)

    payload = cli_module.run_predict_batch(SimpleNamespace(
        write_db=False,
        select_finals=False))

    assert payload["processed"] == 2
    assert payload["predicted"] == 1
    assert payload["skipped"] == 1
    assert payload["results"][0]["skipped"] is True
    assert "30" in payload["results"][0]["error"]
    assert payload["results"][1]["skipped"] is False
    assert payload["results"][1]["predictions"]["btts"]["p_yes"] == pytest.approx(
        0.55)


@pytest.mark.parametrize("is_tty", [False, True])
def test_predict_batch_main_keeps_json_stdout_contract(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        is_tty: bool) -> None:
    from models.pipeline.core import cli as cli_module

    good = MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=101)
    bad = MatchupInput(
        home_team_id=30,
        away_team_id=40,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=102)
    predictor = MagicMock()
    predictor.predict_pair.side_effect = [
        ValueError("Insufficient match history for team id(s): 30"),
        {"btts": BttsPrediction(0.55, 0.45)}]
    monkeypatch.setattr(
        cli_module.sys.stderr, "isatty", lambda: is_tty)
    monkeypatch.setattr(
        cli_module,
        "_load_batch_matchups",
        lambda _args: [bad.model_dump(), good.model_dump()])
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "_build_predict_history_context",
        lambda _predictor, _matchups: None)

    code = cli_module.main([
        "predict-batch",
        "--btts-config",
        "models/configs/training/football_btts_v2.json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["ok"] is True
    result = payload["result"]
    assert result["processed"] == 2
    assert result["predicted"] == 1
    assert result["skipped"] == 1
    assert result["results"][0]["skipped"] is True
    assert result["results"][1]["skipped"] is False
    assert result["results"][1]["predictions"]["btts"]["p_yes"] == pytest.approx(
        0.55)


def test_predict_batch_skip_logs_use_tqdm_write(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    written: list[str] = []

    def spy(s, file=None, end="\n", nolock=False):
        del file, end, nolock
        written.append(str(s))

    monkeypatch.setattr(tqdm_std.tqdm, "write", staticmethod(spy))
    monkeypatch.setattr(
        cli_module.sys.stderr, "isatty", lambda: True)
    matchup = MatchupInput(
        home_team_id=30,
        away_team_id=40,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=102)
    predictor = MagicMock()
    predictor.predict_pair.side_effect = [
        ValueError("Insufficient match history for team id(s): 30")]
    monkeypatch.setattr(
        cli_module,
        "_load_batch_matchups",
        lambda _args: [matchup.model_dump()])
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "_build_predict_history_context",
        lambda _predictor, _matchups: None)
    cli_module._configure_logging(False)

    cli_module.run_predict_batch(SimpleNamespace(
        write_db=False,
        select_finals=False))

    assert any("Skipping match_id=102" in message for message in written)


def test_predict_batch_progress_bar_disabled_without_tty(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    recorded: dict[str, object] = {}

    def fake_tqdm(iterable, **kwargs):
        recorded.update(kwargs)
        return iterable

    monkeypatch.setattr(tqdm_module, "tqdm", fake_tqdm)
    monkeypatch.setattr(
        cli_module.sys.stderr, "isatty", lambda: False)
    matchups = [MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24))]
    assert list(cli_module._predict_batch_progress(matchups)) == matchups
    assert recorded["disable"] is True
    assert recorded["file"] is cli_module.sys.stderr


def test_predict_batch_progress_bar_enabled_on_tty(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    recorded: dict[str, object] = {}

    def fake_tqdm(iterable, **kwargs):
        recorded.update(kwargs)
        return iterable

    monkeypatch.setattr(tqdm_module, "tqdm", fake_tqdm)
    monkeypatch.setattr(
        cli_module.sys.stderr, "isatty", lambda: True)
    matchups = [MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24))]
    list(cli_module._predict_batch_progress(matchups))
    assert recorded["disable"] is False
    assert recorded["file"] is cli_module.sys.stderr


def test_run_predict_batch_logs_history_stages(
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture) -> None:
    from models.pipeline.core import cli as cli_module

    matchup = MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=101)
    predictor = MagicMock()
    predictor.result_config = None
    predictor.btts_config = _btts_config()
    predictor.goals_config = None
    predictor.predict_pair.return_value = {
        "btts": BttsPrediction(0.55, 0.45)}
    fake_context = MagicMock()
    fake_context.finished_matches = [1, 2, 3]
    fake_context.ratings_by_key = {"a": None}
    monkeypatch.setattr(
        cli_module,
        "_load_batch_matchups",
        lambda _args: [matchup.model_dump()])
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "build_shared_history_context",
        lambda *_args, **_kwargs: fake_context)

    with caplog.at_level(logging.INFO):
        payload = cli_module.run_predict_batch(SimpleNamespace(
            write_db=False,
            select_finals=False))

    messages = [record.getMessage() for record in caplog.records]
    assert "Building shared history..." in messages
    assert "History ready (3 finished, 1 rating timelines)" in messages
    assert payload["predicted"] == 1
    assert predictor.predict_pair.call_args.kwargs["context"] is fake_context


def test_run_predict_batch_shares_context_and_feature_cache(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    first = MatchupInput(
        home_team_id=10,
        away_team_id=20,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=101)
    second = MatchupInput(
        home_team_id=30,
        away_team_id=40,
        league_id=19,
        as_of_date=date(2026, 7, 24),
        match_id=102)
    context = object()
    predictor = MagicMock()
    predictor.predict_pair.return_value = {
        "btts": BttsPrediction(0.55, 0.45)}
    monkeypatch.setattr(
        cli_module,
        "_load_batch_matchups",
        lambda _args: [first.model_dump(), second.model_dump()])
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "_build_predict_history_context",
        lambda _predictor, _matchups: context)

    cli_module.run_predict_batch(SimpleNamespace(
        write_db=False,
        select_finals=False))

    calls = predictor.predict_pair.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["context"] is context
    assert calls[1].kwargs["context"] is context
    assert calls[0].kwargs["feature_cache"] is calls[1].kwargs["feature_cache"]


def test_run_predict_pair_builds_shared_history(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from models.pipeline.core import cli as cli_module

    context = object()
    predictor = MagicMock()
    predictor.predict_pair.return_value = {
        "btts": BttsPrediction(0.6, 0.4)}
    monkeypatch.setattr(
        cli_module, "_future_predictor", lambda _args: predictor)
    monkeypatch.setattr(
        cli_module,
        "_build_predict_history_context",
        lambda _predictor, _matchups: context)

    payload = cli_module.run_predict_pair(SimpleNamespace(
        home=10,
        away=20,
        league_id=1,
        season_id=1,
        as_of=date(2026, 7, 24),
        match_id=None,
        write_db=False,
        select_finals=False))

    assert payload["written"] == 0
    assert predictor.predict_pair.call_args.kwargs["context"] is context
