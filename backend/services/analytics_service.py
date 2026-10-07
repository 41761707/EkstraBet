"""Business logic for model analytics endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.repositories import analytics_repository
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.services.model_metadata_service import get_sport_market_families

StatType = Literal["ou", "btts", "result", "all"]
GroupBy = Literal["none", "team", "league"]
AggregationMetric = Literal["accuracy", "profit"]
FamilyFrames = dict[str, tuple[pd.DataFrame, pd.DataFrame]]

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

_MODEL_LEAGUE_KEY_COLUMNS = (
    "model_id", "model_name", "league_id", "league_name")
_PREDICTION_COMPARISON_COLUMNS = _MODEL_LEAGUE_KEY_COLUMNS + ("pred_outcome",)
_BET_COMPARISON_COLUMNS = _MODEL_LEAGUE_KEY_COLUMNS + (
    "bet_event_id", "odds", "bet_outcome")
_STAT_FAMILIES = ("ou", "btts", "result")
_FOOTBALL_DISPLAY_LABELS = {
    "under_2_5": "Poniżej 2.5",
    "over_2_5": "Powyżej 2.5",
    "no": "BTTS nie",
    "yes": "BTTS tak",
    "home": "Gospodarz",
    "draw": "Remis",
    "away": "Gość"
}


def _display_labels_for(config: dict[str, Any]) -> dict[str, str]:
    """Return chart labels for a stat family."""
    custom = config.get("display_labels")
    if isinstance(custom, dict) and custom:
        return custom
    return _FOOTBALL_DISPLAY_LABELS


def _config_from_market_family(family: dict[str, Any]) -> dict[str, Any]:
    """Map a catalog family onto the analytics stat config."""
    pred_event_map: dict[int, str] = {}
    labels: list[str] = []
    display_labels: dict[str, str] = {}
    for event in family["events"]:
        label = str(event["name"])
        event_id = int(event["event_id"])
        pred_event_map[event_id] = label
        labels.append(label)
        display_labels[label] = label
    return {
        "pred_event_map": pred_event_map,
        "bet_event_map": pred_event_map,
        "labels": tuple(labels),
        "display_labels": display_labels,
        "event_ids": tuple(pred_event_map)
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
    pred_frame: pd.DataFrame,
    bet_frame: pd.DataFrame,
    stat_type: str,
    apply_tax: bool,
    tax_rate: float,
    config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute prediction and bet statistics for one event family."""
    if config is None:
        config = _STAT_CONFIG[stat_type]
    display_labels = _display_labels_for(config)
    if pred_frame.empty and bet_frame.empty:
        empty_breakdown = _build_type_breakdown(
            pred_frame,
            "event_id",
            config["pred_event_map"],
            config["labels"],
            outcome_column="pred_outcome")
        empty_bet_breakdown = _build_type_breakdown(
            bet_frame,
            "bet_event_id",
            config["bet_event_map"],
            config["labels"],
            outcome_column="bet_outcome",
            include_profit=True,
            apply_tax=apply_tax,
            tax_rate=tax_rate)
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
            "models": []
        }

    if pred_frame.empty:
        filtered_pred_frame = pred_frame
    else:
        filtered_pred_frame = pred_frame[
            pred_frame["event_id"].isin(config["pred_event_map"])]
    pred_breakdown = _build_type_breakdown(
        filtered_pred_frame,
        "event_id",
        config["pred_event_map"],
        config["labels"],
        outcome_column="pred_outcome")
    if bet_frame.empty:
        settled_bet_frame = bet_frame
    else:
        settled_bet_frame = bet_frame[
            bet_frame["bet_event_id"].isin(config["bet_event_map"])
            & bet_frame["bet_outcome"].notna()]
    bet_breakdown = _build_type_breakdown(
        settled_bet_frame,
        "bet_event_id",
        config["bet_event_map"],
        config["labels"],
        outcome_column="bet_outcome",
        include_profit=True,
        apply_tax=apply_tax,
        tax_rate=tax_rate)

    return {
        "predictions": {
            **pred_breakdown,
            "charts": _build_chart_data(pred_breakdown, display_labels),
        },
        "bets": {
            **bet_breakdown,
            "charts": _build_chart_data(bet_breakdown, display_labels),
        },
        "models": _build_category_model_rows(
            filtered_pred_frame,
            settled_bet_frame,
            apply_tax,
            tax_rate)
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


def _build_league_outcome_comparison(
    frame: pd.DataFrame) -> dict[str, Any] | None:
    """Build match-weighted league outcome comparison payload."""
    if frame.empty:
        return None

    leagues: list[dict[str, Any]] = []
    total_matches = 0
    total_over = 0
    total_btts = 0
    total_home = 0
    total_away = 0

    for _, row in frame.iterrows():
        played = int(row["played_matches"])
        if played <= 0:
            continue
        over_count = int(row["over_2_5_count"])
        btts_count = int(row["btts_yes_count"])
        home_count = int(row["home_win_count"])
        away_count = int(row["away_win_count"])
        leagues.append({
            "league_id": int(row["league_id"]),
            "league_name": str(row["league_name"]),
            "played_matches": played,
            "btts_yes_pct": _safe_pct(btts_count, played) or 0.0,
            "over_2_5_pct": _safe_pct(over_count, played) or 0.0,
            "home_win_pct": _safe_pct(home_count, played) or 0.0,
            "away_win_pct": _safe_pct(away_count, played) or 0.0,
        })
        total_matches += played
        total_over += over_count
        total_btts += btts_count
        total_home += home_count
        total_away += away_count

    if len(leagues) < 2 or total_matches == 0:
        return None

    return {
        "leagues": leagues,
        "averages": {
            "btts_yes_pct": _safe_pct(total_btts, total_matches) or 0.0,
            "over_2_5_pct": _safe_pct(total_over, total_matches) or 0.0,
            "home_win_pct": _safe_pct(total_home, total_matches) or 0.0,
            "away_win_pct": _safe_pct(total_away, total_matches) or 0.0
        }
    }


def get_league_outcome_comparisons(
    league_ids: list[int] | None,
    season_id: int | None) -> dict[str, Any] | None:
    """Return match-weighted outcome rates for selected leagues."""
    if not league_ids or len(league_ids) < 2:
        return None
    comparison_frame = analytics_repository.fetch_leagues_outcome_comparison(
        league_ids=league_ids,
        season_id=season_id)
    return _build_league_outcome_comparison(comparison_frame)


def _prepare_model_league_frame(
    frame: pd.DataFrame,
    required_columns: tuple[str, ...]) -> pd.DataFrame:
    """Return rows with model and league identifiers ready for grouping."""
    if frame.empty or not set(required_columns).issubset(frame.columns):
        return pd.DataFrame()
    working = frame.dropna(subset=["model_id", "league_id"]).copy()
    if working.empty:
        return working
    working["model_id"] = working["model_id"].astype(int)
    working["league_id"] = working["league_id"].astype(int)
    working["model_name"] = working["model_name"].fillna("").astype(str)
    working["league_name"] = working["league_name"].fillna("").astype(str)
    return working


def _sum_frame_bet_profit(
    frame: pd.DataFrame,
    apply_tax: bool,
    tax_rate: float) -> float:
    """Sum unit profit across all event types in a bet frame."""
    if frame.empty or "bet_event_id" not in frame.columns:
        return 0.0
    total = 0.0
    for event_id in frame["bet_event_id"].dropna().unique():
        total += _compute_bet_profit(frame, int(event_id), apply_tax, tax_rate)
    return round(total, 2)


def _frame_model_names(
    frame: pd.DataFrame,
    id_column: str) -> dict[int, str]:
    """Map model id to display name from a statistics frame."""
    if frame.empty or id_column not in frame.columns:
        return {}
    names: dict[int, str] = {}
    for _, row in frame.dropna(subset=[id_column]).iterrows():
        model_id = int(row[id_column])
        raw_name = row["model_name"] if "model_name" in frame.columns else None
        if raw_name is None or pd.isna(raw_name) or str(raw_name) == "":
            names.setdefault(model_id, str(model_id))
        else:
            names[model_id] = str(raw_name)
    return names


def _subset_for_model(
    frame: pd.DataFrame,
    model_id: int) -> pd.DataFrame:
    """Return rows of one model, or the whole frame when it has no model id."""
    if frame.empty or "model_id" not in frame.columns:
        return frame
    return frame[frame["model_id"] == model_id]


def _prediction_totals(frame: pd.DataFrame) -> tuple[int, int]:
    """Count predictions, treating a missing outcome as incorrect."""
    if frame.empty or "pred_outcome" not in frame.columns:
        return 0, 0
    total = int(len(frame))
    correct = int(frame["pred_outcome"].fillna(0).astype(int).sum())
    return total, correct


def _count_correct(frame: pd.DataFrame, outcome_column: str) -> tuple[int, int]:
    """Return total and correct counts for a settled outcome column."""
    if frame.empty or outcome_column not in frame.columns:
        return 0, 0
    settled = frame[frame[outcome_column].notna()]
    total = int(len(settled))
    if total == 0:
        return 0, 0
    correct = int(settled[outcome_column].fillna(0).astype(int).sum())
    return total, correct


def _build_category_model_rows(
    pred_frame: pd.DataFrame,
    bet_frame: pd.DataFrame,
    apply_tax: bool,
    tax_rate: float) -> list[dict[str, Any]]:
    """Split one family into per-model accuracy and unit profit."""
    names = _frame_model_names(pred_frame, "model_id")
    names.update(_frame_model_names(bet_frame, "model_id"))
    rows: list[dict[str, Any]] = []
    ordered_ids = sorted(names, key=lambda item: (names[item], item))
    for model_id in ordered_ids:
        model_pred = _subset_for_model(pred_frame, model_id)
        model_bets = _subset_for_model(bet_frame, model_id)
        pred_total, pred_correct = _prediction_totals(model_pred)
        bet_total, bet_correct = _count_correct(model_bets, "bet_outcome")
        rows.append({
            "model_id": model_id,
            "model_name": names[model_id],
            "prediction_total": pred_total,
            "prediction_correct": pred_correct,
            "prediction_accuracy_pct": _safe_pct(pred_correct, pred_total),
            "bet_total": bet_total,
            "bet_correct": bet_correct,
            "bet_accuracy_pct": _safe_pct(bet_correct, bet_total),
            "profit_total": _sum_frame_bet_profit(
                model_bets,
                apply_tax,
                tax_rate)
        })
    return rows


def _build_model_prediction_league_comparisons(
    frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Group prediction accuracy per model and league."""
    working = _prepare_model_league_frame(
        frame,
        _PREDICTION_COMPARISON_COLUMNS)
    if working.empty:
        return []

    working["pred_outcome"] = working["pred_outcome"].fillna(0).astype(int)
    comparisons: list[dict[str, Any]] = []
    model_groups = working.groupby(["model_id", "model_name"], sort=False)
    for (model_id, model_name), model_rows in model_groups:
        leagues: list[dict[str, Any]] = []
        total_all = 0
        correct_all = 0
        league_groups = model_rows.groupby(
            ["league_id", "league_name"],
            sort=False)
        for (league_id, league_name), league_rows in league_groups:
            total = int(len(league_rows))
            if total == 0:
                continue
            correct = int(league_rows["pred_outcome"].sum())
            leagues.append({
                "league_id": int(league_id),
                "league_name": str(league_name),
                "total": total,
                "correct": correct,
                "accuracy_pct": _safe_pct(correct, total) or 0.0
            })
            total_all += total
            correct_all += correct
        # porównanie ma sens dopiero przy co najmniej dwóch ligach
        if len(leagues) < 2:
            continue
        leagues.sort(key=lambda item: item["league_name"])
        comparisons.append({
            "model_id": int(model_id),
            "model_name": str(model_name),
            "leagues": leagues,
            "average_accuracy_pct": _safe_pct(correct_all, total_all) or 0.0
        })
    comparisons.sort(key=lambda item: (item["model_name"], item["model_id"]))
    return comparisons


def _build_model_bet_profit_league_comparisons(
    frame: pd.DataFrame,
    apply_tax: bool,
    tax_rate: float) -> list[dict[str, Any]]:
    """Group unit bet profit per model and league."""
    working = _prepare_model_league_frame(frame, _BET_COMPARISON_COLUMNS)
    if working.empty:
        return []

    comparisons: list[dict[str, Any]] = []
    model_groups = working.groupby(["model_id", "model_name"], sort=False)
    for (model_id, model_name), model_rows in model_groups:
        leagues: list[dict[str, Any]] = []
        for (league_id, league_name), league_rows in model_rows.groupby(
                ["league_id", "league_name"],
                sort=False):
            settled = league_rows[league_rows["bet_outcome"].notna()]
            total_bets = int(len(settled))
            if total_bets == 0:
                continue
            leagues.append({
                "league_id": int(league_id),
                "league_name": str(league_name),
                "total_bets": total_bets,
                "profit": _sum_frame_bet_profit(
                    settled,
                    apply_tax,
                    tax_rate)
            })
        # porównanie ma sens dopiero przy co najmniej dwóch ligach
        if len(leagues) < 2:
            continue
        leagues.sort(key=lambda item: item["league_name"])
        total_profit = round(sum(item["profit"] for item in leagues), 2)
        comparisons.append({
            "model_id": int(model_id),
            "model_name": str(model_name),
            "leagues": leagues,
            "total_profit": total_profit
        })
    comparisons.sort(key=lambda item: (item["model_name"], item["model_id"]))
    return comparisons


def _build_model_league_comparisons(
    family_frames: FamilyFrames,
    apply_tax: bool,
    tax_rate: float) -> dict[str, Any] | None:
    """Assemble per-family prediction and profit comparisons."""
    predictions: dict[str, list[dict[str, Any]]] = {}
    bet_profits: dict[str, list[dict[str, Any]]] = {}
    has_comparison = False
    empty = pd.DataFrame()
    for family in _STAT_FAMILIES:
        pred_frame, bet_frame = family_frames.get(family, (empty, empty))
        pred_items = _build_model_prediction_league_comparisons(pred_frame)
        profit_items = _build_model_bet_profit_league_comparisons(
            bet_frame,
            apply_tax,
            tax_rate)
        predictions[family] = pred_items
        bet_profits[family] = profit_items
        if pred_items or profit_items:
            has_comparison = True
    if not has_comparison:
        return None
    return {
        "predictions": predictions,
        "bet_profits": bet_profits
    }


def _fetch_family_statistics(
    stat_type: StatType,
    model_map: dict[str, list[int]],
    league_ids: list[int] | None,
    season_id: int | None,
    date_from: date | None,
    date_to: date | None,
    round_from: int | None,
    round_to: int | None,
    team_id: int | None,
    settled_only: bool,
    positive_ev_only: bool,
    apply_tax: bool,
    tax_rate: float) -> tuple[dict[str, Any], FamilyFrames]:
    """Fetch frames and category stats for requested families."""
    categories: dict[str, Any] = {}
    family_frames: FamilyFrames = {}
    for family in _resolve_stat_types(stat_type):
        model_ids = model_map[family]
        if not model_ids:
            continue
        pred_frame = analytics_repository.fetch_prediction_rows(
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
        bet_frame = analytics_repository.fetch_bet_rows(
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
        family_frames[family] = (pred_frame, bet_frame)
        categories[family] = _generate_category_statistics(
            pred_frame,
            bet_frame,
            family,
            apply_tax,
            tax_rate)
    return categories, family_frames


def _build_analytics_aggregations(
    stat_type: StatType,
    group_by: GroupBy,
    aggregation_metric: AggregationMetric,
    season_id: int | None,
    league_ids: list[int] | None,
    apply_tax: bool,
    tax_rate: float) -> dict[str, Any]:
    """Build optional team or league aggregation payloads."""
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
                    "result_profit")
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
                **by_league
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
            **by_team
        }
    return aggregations


def _fetch_scoped_family_frames(
    event_ids: tuple[int, ...],
    model_ids: list[int],
    sport_id: int,
    league_ids: list[int] | None,
    season_id: int | None,
    date_from: date | None,
    date_to: date | None,
    round_from: int | None,
    round_to: int | None,
    team_id: int | None,
    settled_only: bool,
    positive_ev_only: bool,
    apply_tax: bool,
    tax_rate: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load prediction and bet rows for one catalog family."""
    # stat_type jest ignorowany, gdy podane są event_ids rodziny
    pred_frame = analytics_repository.fetch_prediction_rows(
        stat_type="result",
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
        tax_rate=tax_rate,
        event_ids=event_ids,
        sport_id=sport_id)
    bet_frame = analytics_repository.fetch_bet_rows(
        stat_type="result",
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
        tax_rate=tax_rate,
        event_ids=event_ids,
        sport_id=sport_id)
    return pred_frame, bet_frame


def _get_hockey_family_statistics(
    model_ids: list[int] | None,
    league_ids: list[int] | None,
    season_id: int | None,
    date_from: date | None,
    date_to: date | None,
    round_from: int | None,
    round_to: int | None,
    team_id: int | None,
    settled_only: bool,
    positive_ev_only: bool,
    apply_tax: bool) -> dict[str, Any]:
    """Accuracy and unit profit for every hockey family in the catalog."""
    tax_rate = BETTING_TAX_RATE if apply_tax else 0.0
    selected_models = model_ids or []
    categories: dict[str, Any] = {}
    if selected_models:
        for family in get_sport_market_families(HOCKEY_SPORT_ID):
            config = _config_from_market_family(family)
            event_ids = config["event_ids"]
            if not event_ids:
                continue
            pred_frame, bet_frame = _fetch_scoped_family_frames(
                event_ids=event_ids,
                model_ids=selected_models,
                sport_id=HOCKEY_SPORT_ID,
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
            categories[str(family["name"])] = _generate_category_statistics(
                pred_frame,
                bet_frame,
                str(family["name"]),
                apply_tax,
                tax_rate,
                config=config)
    return {
        "categories": categories,
        "aggregations": {},
        "league_comparisons": None,
        "model_league_comparisons": None,
        "filters_applied": {
            "stat_type": "all",
            "sport_id": HOCKEY_SPORT_ID,
            "model_ids": selected_models,
            "model_result_ids": None,
            "model_ou_ids": None,
            "model_btts_ids": None,
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
            "group_by": "none",
            "aggregation_metric": "accuracy"
        }
    }


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
    sport_id: int | None = None,
    model_ids: list[int] | None = None) -> dict[str, Any]:
    """Return model effectiveness statistics ready for API responses."""
    if sport_id == HOCKEY_SPORT_ID:
        return _get_hockey_family_statistics(
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
            apply_tax=apply_tax)
    tax_rate = BETTING_TAX_RATE if apply_tax else 0.0
    model_map = {
        "ou": model_ou_ids or [],
        "btts": model_btts_ids or [],
        "result": model_result_ids or [],
    }
    categories, family_frames = _fetch_family_statistics(
        stat_type=stat_type,
        model_map=model_map,
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

    aggregations = _build_analytics_aggregations(
        stat_type=stat_type,
        group_by=group_by,
        aggregation_metric=aggregation_metric,
        season_id=season_id,
        league_ids=league_ids,
        apply_tax=apply_tax,
        tax_rate=tax_rate)

    league_comparisons = get_league_outcome_comparisons(
        league_ids,
        season_id)

    model_league_comparisons = _build_model_league_comparisons(
        family_frames,
        apply_tax,
        tax_rate)

    return {
        "categories": categories,
        "aggregations": aggregations,
        "league_comparisons": league_comparisons,
        "model_league_comparisons": model_league_comparisons,
        "filters_applied": {
            "stat_type": stat_type,
            "sport_id": sport_id,
            "model_ids": model_ids,
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
        },
    }
