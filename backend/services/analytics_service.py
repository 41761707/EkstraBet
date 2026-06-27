"""Business logic for model analytics endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
import pandas as pd
from backend.repositories import analytics_repository
from backend.services.bet_service import BETTING_TAX_RATE

StatType = Literal["ou", "btts", "result", "all"]
GroupBy = Literal["none", "team", "league"]
AggregationMetric = Literal["accuracy", "profit"]

_OU_LABELS = ("under_2_5", "over_2_5")
_BTTS_LABELS = ("no", "yes")
_RESULT_LABELS = ("home", "draw", "away")

_STAT_CONFIG = {
    "ou": {
        "pred_event_map": {12: "under_2_5", 8: "over_2_5"},
        "bet_event_map": {12: "under_2_5", 8: "over_2_5"},
        "labels": _OU_LABELS,
    },
    "btts": {
        "pred_event_map": {172: "no", 6: "yes"},
        "bet_event_map": {172: "no", 6: "yes"},
        "labels": _BTTS_LABELS,
    },
    "result": {
        "pred_event_map": {1: "home", 2: "draw", 3: "away"},
        "bet_event_map": {1: "home", 2: "draw", 3: "away"},
        "labels": _RESULT_LABELS,
    },
}


def _safe_pct(numerator: int, denominator: int) -> float | None:
    """Return percentage rounded to two decimals or None when empty."""
    if denominator == 0:
        return None
    return round(numerator * 100 / denominator, 2)


def _compute_bet_profit(
    frame: pd.DataFrame,
    event_id: int,
    apply_tax: bool,
    tax_rate: float) -> float:
    """Sum unit profit for settled bets on one event type."""
    subset = frame[frame["bet_event_id"] == event_id]
    if subset.empty:
        return 0.0
    total = 0.0
    for _, row in subset.iterrows():
        if pd.isna(row["bet_outcome"]):
            continue
        if int(row["bet_outcome"]) == 1:
            payout = float(row["odds"])
            if apply_tax:
                payout *= (1 - tax_rate)
            total += payout - 1
        else:
            total -= 1
    return round(total, 2)


def _build_type_breakdown(
    frame: pd.DataFrame,
    event_column: str,
    event_map: dict[int, str],
    labels: tuple[str, ...],
    outcome_column: str | None = None,
    include_profit: bool = False,
    apply_tax: bool = False,
    tax_rate: float = BETTING_TAX_RATE) -> dict[str, Any]:
    """Build per-type counts, accuracy and optional profit."""
    types: list[dict[str, Any]] = []
    total = 0
    correct = 0
    profit_total = 0.0

    reverse_map = {label: event_id for event_id, label in event_map.items()}

    if frame.empty:
        for label in labels:
            types.append({
                "key": label,
                "total": 0,
                "correct": 0,
                "accuracy_pct": None,
                "share_pct": None,
                "profit": 0.0 if include_profit else None,
            })
        return {
            "total": 0,
            "correct": 0,
            "accuracy_pct": None,
            "profit_total": 0.0 if include_profit else None,
            "by_type": types,
        }

    for label in labels:
        event_id = reverse_map[label]
        subset = frame[frame[event_column] == event_id]
        type_total = int(len(subset))
        if outcome_column is None:
            type_correct = 0
        else:
            type_correct = int(subset[outcome_column].fillna(0).astype(int).sum())
        total += type_total
        correct += type_correct
        type_profit = None
        if include_profit:
            type_profit = _compute_bet_profit(
                frame,
                event_id,
                apply_tax,
                tax_rate)
            profit_total += type_profit
        types.append({
            "key": label,
            "total": type_total,
            "correct": type_correct,
            "accuracy_pct": _safe_pct(type_correct, type_total),
            "share_pct": None,
            "profit": type_profit,
        })

    for item in types:
        item["share_pct"] = _safe_pct(item["total"], total)

    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": _safe_pct(correct, total),
        "profit_total": round(profit_total, 2) if include_profit else None,
        "by_type": types,
    }


def _build_chart_data(
    breakdown: dict[str, Any],
    label_names: dict[str, str]) -> dict[str, Any]:
    """Build chart-friendly distribution and comparison payloads."""
    labels = [label_names[item["key"]] for item in breakdown["by_type"]]
    values = [item["total"] for item in breakdown["by_type"]]
    correct = [item["correct"] for item in breakdown["by_type"]]
    incorrect = [item["total"] - item["correct"] for item in breakdown["by_type"]]
    percentages = [
        item["share_pct"] if item["share_pct"] is not None else 0.0
        for item in breakdown["by_type"]
    ]
    return {
        "distribution": {
            "labels": labels,
            "values": values,
            "percentages": percentages,
        },
        "comparison": {
            "labels": labels,
            "correct": correct,
            "incorrect": incorrect,
        },
    }


def _generate_category_statistics(
    frame: pd.DataFrame,
    stat_type: str,
    apply_tax: bool,
    tax_rate: float) -> dict[str, Any]:
    """Compute prediction and bet statistics for one event family."""
    config = _STAT_CONFIG[stat_type]
    if frame.empty:
        empty_breakdown = _build_type_breakdown(
            frame,
            "event_id",
            config["pred_event_map"],
            config["labels"],
            outcome_column="pred_outcome")
        empty_bet_breakdown = _build_type_breakdown(
            frame,
            "bet_event_id",
            config["bet_event_map"],
            config["labels"],
            outcome_column="bet_outcome",
            include_profit=True,
            apply_tax=apply_tax,
            tax_rate=tax_rate)
        display_labels = {
            "under_2_5": "Under 2.5",
            "over_2_5": "Over 2.5",
            "no": "NO BTTS",
            "yes": "BTTS",
            "home": "Home",
            "draw": "Draw",
            "away": "Away",
        }
        return {
            "predictions": {
                **empty_breakdown,
                **{"charts": _build_chart_data(
                    empty_breakdown,
                    display_labels)},
            },
            "bets": {
                **empty_bet_breakdown,
                **{"charts": _build_chart_data(
                    empty_bet_breakdown,
                    display_labels)},
            },
        }

    pred_frame = frame[frame["event_id"].isin(config["pred_event_map"])]
    bet_frame = frame[
        frame["bet_event_id"].isin(config["bet_event_map"])
        & frame["bet_outcome"].notna()]

    pred_breakdown = _build_type_breakdown(
        pred_frame,
        "event_id",
        config["pred_event_map"],
        config["labels"],
        outcome_column="pred_outcome")
    bet_breakdown = _build_type_breakdown(
        bet_frame,
        "bet_event_id",
        config["bet_event_map"],
        config["labels"],
        outcome_column="bet_outcome",
        include_profit=True,
        apply_tax=apply_tax,
        tax_rate=tax_rate)

    display_labels = {
        "under_2_5": "Under 2.5",
        "over_2_5": "Over 2.5",
        "no": "NO BTTS",
        "yes": "BTTS",
        "home": "Home",
        "draw": "Draw",
        "away": "Away",
    }

    return {
        "predictions": {
            **pred_breakdown,
            "charts": _build_chart_data(pred_breakdown, display_labels),
        },
        "bets": {
            **bet_breakdown,
            "charts": _build_chart_data(bet_breakdown, display_labels),
        },
    }


def _resolve_stat_types(stat_type: StatType) -> list[str]:
    """Expand stat_type filter to concrete families."""
    if stat_type == "all":
        return ["ou", "btts", "result"]
    return [stat_type]


def _map_aggregation_rows(
    frame: pd.DataFrame,
    total_predictions: int,
    correct_predictions: int) -> list[dict[str, Any]]:
    """Map repository rows and append a league-wide average row."""
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        total = int(row["total_predictions"])
        correct = int(row["correct_predictions"])
        rows.append({
            "entity_id": int(row["entity_id"]),
            "entity_name": str(row["entity_name"]),
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy_pct": _safe_pct(correct, total),
        })
    rows.append({
        "entity_id": None,
        "entity_name": "AVERAGE",
        "total_predictions": total_predictions,
        "correct_predictions": correct_predictions,
        "accuracy_pct": _safe_pct(correct_predictions, total_predictions),
    })
    return rows


def _build_profit_aggregation(
    frame: pd.DataFrame,
    profit_column: str) -> list[dict[str, Any]]:
    """Map league profit rows sorted descending by profit."""
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append({
            "entity_id": int(row["entity_id"]),
            "entity_name": str(row["entity_name"]),
            "profit": round(float(row[profit_column]), 2),
        })
    rows.sort(key=lambda item: item["profit"], reverse=True)
    return rows


def get_model_statistics(
    stat_type: StatType = "all",
    model_result_ids: list[int] | None = None,
    model_ou_ids: list[int] | None = None,
    model_btts_ids: list[int] | None = None,
    league_ids: list[int] | None = None,
    season_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    round_from: int | None = None,
    round_to: int | None = None,
    team_id: int | None = None,
    settled_only: bool = True,
    positive_ev_only: bool = False,
    apply_tax: bool = False,
    group_by: GroupBy = "none",
    aggregation_metric: AggregationMetric = "accuracy",
    include_league_characteristics: bool = False) -> dict[str, Any]:
    """Return model effectiveness statistics ready for API responses."""
    tax_rate = BETTING_TAX_RATE if apply_tax else 0.0
    model_map = {
        "ou": model_ou_ids or [],
        "btts": model_btts_ids or [],
        "result": model_result_ids or [],
    }

    categories: dict[str, Any] = {}
    for family in _resolve_stat_types(stat_type):
        model_ids = model_map[family]
        if not model_ids:
            continue
        frame = analytics_repository.fetch_prediction_bet_rows(
            stat_type=family,
            model_ids=model_ids,
            league_ids=league_ids,
            season_id=season_id,
            date_from=date_from,
            date_to=date_to,
            round_from=round_from,
            round_to=round_to,
            team_id=team_id,
            settled_only=settled_only,
            positive_ev_only=positive_ev_only,
            apply_tax=apply_tax,
            tax_rate=tax_rate)
        categories[family] = _generate_category_statistics(
            frame,
            family,
            apply_tax,
            tax_rate)

    aggregations: dict[str, Any] = {}
    if group_by == "league" and season_id is not None:
        if aggregation_metric == "profit":
            profit_frame = (
                analytics_repository.fetch_league_bet_profit_aggregation(
                    season_id=season_id,
                    apply_tax=apply_tax,
                    tax_rate=tax_rate))
            aggregations["by_league"] = {
                "metric": "profit",
                "ou": _build_profit_aggregation(profit_frame, "ou_profit"),
                "btts": _build_profit_aggregation(profit_frame, "btts_profit"),
                "result": _build_profit_aggregation(
                    profit_frame,
                    "result_profit"),
            }
        else:
            by_league: dict[str, list[dict[str, Any]]] = {}
            for family in _resolve_stat_types(stat_type):
                entity_frame = (
                    analytics_repository.fetch_league_prediction_aggregation(
                        season_id=season_id,
                        stat_type=family))
                total, correct = (
                    analytics_repository.fetch_league_average_prediction_stats(
                        season_id=season_id,
                        stat_type=family))
                by_league[family] = _map_aggregation_rows(
                    entity_frame,
                    total,
                    correct)
            aggregations["by_league"] = {
                "metric": "accuracy",
                **by_league,
            }

    if (
        group_by == "team"
        and season_id is not None
        and league_ids
        and len(league_ids) == 1
    ):
        league_id = league_ids[0]
        by_team: dict[str, list[dict[str, Any]]] = {}
        for family in _resolve_stat_types(stat_type):
            entity_frame = (
                analytics_repository.fetch_team_prediction_aggregation(
                    season_id=season_id,
                    league_id=league_id,
                    stat_type=family))
            total, correct = (
                analytics_repository.fetch_league_average_prediction_stats(
                    season_id=season_id,
                    stat_type=family,
                    league_id=league_id))
            by_team[family] = _map_aggregation_rows(
                entity_frame,
                total,
                correct)
        aggregations["by_team"] = {
            "metric": "accuracy",
            **by_team,
        }

    league_characteristics = None
    if (
        include_league_characteristics
        and season_id is not None
        and league_ids
        and len(league_ids) == 1
    ):
        league_characteristics = (
            analytics_repository.fetch_league_characteristics(
                league_id=league_ids[0],
                season_id=season_id))

    return {
        "categories": categories,
        "aggregations": aggregations,
        "league_characteristics": league_characteristics,
        "filters_applied": {
            "stat_type": stat_type,
            "model_result_ids": model_result_ids,
            "model_ou_ids": model_ou_ids,
            "model_btts_ids": model_btts_ids,
            "league_ids": league_ids,
            "season_id": season_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "round_from": round_from,
            "round_to": round_to,
            "team_id": team_id,
            "settled_only": settled_only,
            "positive_ev_only": positive_ev_only,
            "apply_tax": apply_tax,
            "tax_rate": BETTING_TAX_RATE if apply_tax else None,
            "group_by": group_by,
            "aggregation_metric": aggregation_metric,
            "include_league_characteristics": include_league_characteristics,
        },
    }
