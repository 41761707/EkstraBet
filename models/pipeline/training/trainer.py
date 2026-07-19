"""Abstract trainer contract for model-specific implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from models.pipeline.core.config import (
    EvaluationReport,
    ModelRunConfig,
    TrainingReport)


class Trainer(ABC):
    """Common interface for model training and evaluation."""

    @abstractmethod
    def train(self, config: ModelRunConfig) -> TrainingReport:
        """Train a model, persist artifacts, and return a report."""

    @abstractmethod
    def evaluate(self, config: ModelRunConfig) -> EvaluationReport:
        """Evaluate a persisted model and return metrics."""

    @abstractmethod
    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: ModelRunConfig,
            sample_weight: pd.Series | None = None) -> Any:
        """Fit an estimator on prepared feature/label frames."""
