"""Unit tests for champion configs used by the prediction preview."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services import prediction_preview_service as service
from models.pipeline.core.config import FeatureConfig
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.model_lineup import LineupEntry
from models.pipeline.core.model_lineup import LineupError
from models.pipeline.core.model_lineup import ModelLineup
from models.pipeline.core.model_roles import MODEL_STATUS_CHALLENGER
from models.pipeline.core.model_roles import MODEL_STATUS_CHAMPION


RESULT_PATH = Path("models/configs/prediction/football_result_v2.json")
BTTS_PATH = Path("models/configs/prediction/football_btts_v2.json")
GOALS_PATH = Path(
    "models/configs/prediction/football_goals_poisson_v1.json")


def _entry(
        model_name: str,
        task_type: Literal["result", "btts", "goals_poisson"],
        config_path: Path,
        *,
        status: str = MODEL_STATUS_CHAMPION,
        families: dict[int, str] | None = None) -> LineupEntry:
    config = FutureEventsRunConfig(
        model_name=model_name,
        task_type=task_type,
        artifact_dir=Path("models/artifacts/unused"),
        feature_config=FeatureConfig(),
        feature_builder="builder",
        labeler="labeler",
        output_columns=["p"])
    return LineupEntry(
        model_name=model_name,
        model_id=1,
        config_path=config_path,
        config=config,
        family_statuses=families or {1: status})


def _lineup(*entries: LineupEntry) -> ModelLineup:
    return ModelLineup(entries=entries)


class TestChampionConfigPaths(unittest.TestCase):
    """Preview reads champion configs and ignores challengers."""

    def test_maps_one_champion_per_task_type(self) -> None:
        lineup = _lineup(
            _entry("FOOTBALL_RESULT_V2", "result", RESULT_PATH),
            _entry("FOOTBALL_BTTS_V2", "btts", BTTS_PATH),
            _entry(
                "FOOTBALL_GOALS_POISSON_V1",
                "goals_poisson",
                GOALS_PATH,
                families={
                    1: MODEL_STATUS_CHAMPION,
                    3: MODEL_STATUS_CHAMPION,
                    5: MODEL_STATUS_CHAMPION}))
        with patch(
                "models.pipeline.core.model_lineup.resolve_lineup",
                return_value=lineup):
            paths = service._champion_config_paths()
        self.assertEqual(paths, (RESULT_PATH, BTTS_PATH, GOALS_PATH))

    def test_leaves_missing_slot_empty_and_skips_challenger(self) -> None:
        lineup = _lineup(
            _entry("FOOTBALL_RESULT_V2", "result", RESULT_PATH),
            _entry(
                "FOOTBALL_RESULT_V3",
                "result",
                Path("football_result_v3.json"),
                status=MODEL_STATUS_CHALLENGER))
        with patch(
                "models.pipeline.core.model_lineup.resolve_lineup",
                return_value=lineup):
            paths = service._champion_config_paths()
        self.assertEqual(paths, (RESULT_PATH, None, None))

    def test_rejects_two_champions_of_one_task(self) -> None:
        lineup = _lineup(
            _entry("FOOTBALL_RESULT_V2", "result", RESULT_PATH),
            _entry(
                "FOOTBALL_RESULT_V3",
                "result",
                Path("football_result_v3.json"),
                families={2: MODEL_STATUS_CHAMPION}))
        with patch(
                "models.pipeline.core.model_lineup.resolve_lineup",
                return_value=lineup):
            with self.assertRaises(LineupError):
                service._champion_config_paths()

    def test_rejects_unsupported_task_type(self) -> None:
        entry = LineupEntry(
            model_name="ODD",
            model_id=4,
            config_path=Path("odd.json"),
            config=SimpleNamespace(task_type="corners"),
            family_statuses={9: MODEL_STATUS_CHAMPION})
        with patch(
                "models.pipeline.core.model_lineup.resolve_lineup",
                return_value=_lineup(entry)):
            with self.assertRaises(LineupError):
                service._champion_config_paths()

    def test_load_predictor_passes_champion_paths(self) -> None:
        lineup = _lineup(
            _entry("FOOTBALL_RESULT_V2", "result", RESULT_PATH),
            _entry("FOOTBALL_BTTS_V2", "btts", BTTS_PATH),
            _entry(
                "FOOTBALL_GOALS_POISSON_V1",
                "goals_poisson",
                GOALS_PATH))
        module = MagicMock()
        predictor = object()
        module.FutureEventsPredictor.from_config_paths.return_value = (
            predictor)
        service._load_predictor.cache_clear()
        try:
            with patch(
                    "models.pipeline.core.model_lineup.resolve_lineup",
                    return_value=lineup), patch.object(
                    service, "_load_predictor_module", return_value=module):
                loaded = service._load_predictor()
        finally:
            service._load_predictor.cache_clear()
        called = module.FutureEventsPredictor.from_config_paths
        called.assert_called_once_with(RESULT_PATH, BTTS_PATH, GOALS_PATH)
        self.assertIs(loaded, predictor)


if __name__ == "__main__":
    unittest.main()
