"""Artifact persistence helpers for trained models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import joblib


ARTIFACT_MODEL_NAME = "model.joblib"
ARTIFACT_FEATURES_NAME = "feature_columns.json"
ARTIFACT_METRICS_NAME = "metrics.json"
ARTIFACT_META_NAME = "meta.json"


def ensure_artifact_dir(artifact_dir: Path) -> Path:
    """Create the artifact directory when it does not exist."""
    path = Path(artifact_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model_artifact(artifact_dir: Path, model: Any) -> Path:
    """Serialize a fitted estimator/pipeline with joblib."""
    target = ensure_artifact_dir(artifact_dir) / ARTIFACT_MODEL_NAME
    joblib.dump(model, target)
    return target


def load_model_artifact(artifact_dir: Path) -> Any:
    """Load a previously saved estimator/pipeline."""
    target = Path(artifact_dir) / ARTIFACT_MODEL_NAME
    if not target.is_file():
        raise FileNotFoundError(f"Model artifact not found: {target}")
    return joblib.load(target)


def save_feature_columns(
        artifact_dir: Path, feature_columns: list[str]) -> Path:
    """Persist the ordered feature column list used at training time."""
    target = ensure_artifact_dir(artifact_dir) / ARTIFACT_FEATURES_NAME
    with target.open("w", encoding="utf-8") as handle:
        json.dump({"feature_columns": feature_columns}, handle, indent=2)
    return target


def load_feature_columns(artifact_dir: Path) -> list[str]:
    """Load the ordered feature column list from artifacts."""
    target = Path(artifact_dir) / ARTIFACT_FEATURES_NAME
    if not target.is_file():
        raise FileNotFoundError(f"Feature columns artifact not found: {target}")
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    columns = payload.get("feature_columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("feature_columns artifact is empty or invalid")
    return [str(column) for column in columns]


def save_metrics(artifact_dir: Path, metrics: dict[str, Any]) -> Path:
    """Persist training or evaluation metrics as JSON."""
    target = ensure_artifact_dir(artifact_dir) / ARTIFACT_METRICS_NAME
    with target.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    return target


def load_metrics(artifact_dir: Path) -> dict[str, Any]:
    """Load metrics JSON from the artifact directory."""
    target = Path(artifact_dir) / ARTIFACT_METRICS_NAME
    if not target.is_file():
        return {}
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("metrics artifact must be a JSON object")
    return payload


def save_meta(artifact_dir: Path, meta: dict[str, Any]) -> Path:
    """Persist run metadata such as model version and config path."""
    target = ensure_artifact_dir(artifact_dir) / ARTIFACT_META_NAME
    with target.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, default=str)
    return target


def load_meta(artifact_dir: Path) -> dict[str, Any]:
    """Load run metadata from the artifact directory."""
    target = Path(artifact_dir) / ARTIFACT_META_NAME
    if not target.is_file():
        return {}
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("meta artifact must be a JSON object")
    return payload
