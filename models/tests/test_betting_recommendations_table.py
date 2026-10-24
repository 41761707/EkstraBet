"""Schema contract for betting_recommendations and its domain row."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from models.pipeline.betting.domain import BettingRecommendation


REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = REPO_ROOT / "sql" / "betting_recommendations.sql"
DOCS_PATH = REPO_ROOT / "db_documentation" / "db_documentation.md"
_FINGERPRINT = "a" * 64
_COMMENT = re.compile(r"/\*.*?\*/|--.*?$", re.DOTALL | re.MULTILINE)
_UNIQUE_KEY = re.compile(
    r"unique key unique_betting_recommendation\s*\(\s*"
    r"prediction_id\s*,\s*odds_id\s*,\s*model_fingerprint\s*\)")
_READ_INDEX = re.compile(
    r"key idx_betting_recommendations_model_decision\s*\(\s*"
    r"model_fingerprint\s*,\s*decision\s*\)")


def _active_sql() -> str:
    """Return the script with comments removed."""
    return _COMMENT.sub("", SQL_PATH.read_text(encoding="utf-8")).lower()


def _docs_section() -> str:
    """Return the betting_recommendations entry and nothing after it."""
    text = DOCS_PATH.read_text(encoding="utf-8")
    start = text.index("### BETTING_RECOMMENDATIONS")
    end = text.index("\n### ", start + 1)
    return text[start:end]


def _recommendation(**overrides: object) -> BettingRecommendation:
    payload = {
        "prediction_id": 10,
        "odds_id": 20,
        "decision": "bet",
        "calibrated_probability": 0.62,
        "model_fingerprint": _FINGERPRINT
    }
    payload.update(overrides)
    return BettingRecommendation(**payload)


def test_script_creates_only_the_verdict_table() -> None:
    active = _active_sql()
    assert active.count("create table") == 1
    assert "create table betting_recommendations" in active
    for forbidden in ("alter", "update", "delete", "insert", "drop"):
        assert forbidden not in active
    assert "bets" not in active
    assert "check" not in active
    assert "enum" not in active


def test_script_has_the_unique_key_and_read_index() -> None:
    active = _active_sql()
    assert "prediction_id int not null" in active
    assert "odds_id int not null" in active
    assert "decision varchar(16) not null" in active
    assert "calibrated_probability double not null" in active
    assert "model_fingerprint char(64) not null" in active
    assert "created_at timestamp not null default current_timestamp" in active
    assert _UNIQUE_KEY.search(active) is not None
    assert _READ_INDEX.search(active) is not None
    assert "references predictions (id)" in active
    assert "references odds (id)" in active
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert "-- DROP TABLE betting_recommendations;" in raw


def test_documentation_describes_the_same_table() -> None:
    section = _docs_section()
    assert "### BETTING_RECOMMENDATIONS" in section
    for column in (
            "ID",
            "PREDICTION_ID",
            "ODDS_ID",
            "DECISION",
            "CALIBRATED_PROBABILITY",
            "MODEL_FINGERPRINT",
            "CREATED_AT"):
        assert column in section
    assert "(PREDICTION_ID, ODDS_ID, MODEL_FINGERPRINT)" in section
    assert "(MODEL_FINGERPRINT, DECISION)" in section
    assert "CHECK" not in section
    assert "ENUM" not in section
    toc = DOCS_PATH.read_text(encoding="utf-8").split("## Legenda", 1)[0]
    assert "[BETTING_RECOMMENDATIONS](#betting_recommendations)" in toc


def test_recommendation_accepts_boundary_probabilities() -> None:
    low = _recommendation(decision="no_bet", calibrated_probability=0.0)
    high = _recommendation(calibrated_probability=1.0)
    assert low.decision == "no_bet"
    assert high.calibrated_probability == 1.0
    assert "value" not in BettingRecommendation.__dataclass_fields__
    assert "odds" not in BettingRecommendation.__dataclass_fields__
    assert "stake" not in BettingRecommendation.__dataclass_fields__


def test_recommendation_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError, match="decision"):
        _recommendation(decision="stake")


def test_recommendation_rejects_probability_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="calibrated_probability"):
        _recommendation(calibrated_probability=-0.01)
    with pytest.raises(ValueError, match="calibrated_probability"):
        _recommendation(calibrated_probability=1.01)
    with pytest.raises(ValueError, match="calibrated_probability"):
        _recommendation(calibrated_probability=float("nan"))


def test_recommendation_rejects_a_short_fingerprint() -> None:
    with pytest.raises(ValueError, match="model_fingerprint"):
        _recommendation(model_fingerprint="abc")
