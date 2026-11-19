"""Business logic for bet recommendation endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import pandas as pd

from backend.betting_tax import BETTING_TAX_RATE
from backend.repositories import bet_repository
from backend.repositories.team_bet_history_repository import (
    fetch_team_recent_matches)
from backend.services.probability_service import to_unit_probability
from backend.sports.history_window import (
    DEFAULT_HISTORY_WINDOW,
    HISTORY_WINDOWS,
    page_by_history_rate)
from backend.sports.team_bet_history import (
    PastMatch,
    TeamHistoryRule,
    history_rule,
    history_stat_filter,
    is_history_hit,
    names_sampled_team,
    sampled_teams,
    stat_value)

_MAX_OPPORTUNITIES_LIMIT = 20
_DEFAULT_OPPORTUNITIES_LIMIT = 10

SettlementStatus = Literal["pending", "won", "lost"]
SortBy = Literal["ev", "probability", "game_date", "history"]
SortOrder = Literal["asc", "desc"]
OpportunitySource = Literal["bet", "prediction"]
RankingBasis = Literal["ev_after_tax", "ev", "probability"]


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    """Convert nullable numeric values to floats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _optional_str(value: object) -> str | None:
    """Convert nullable values to strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def _compute_ev(probability: float, odds: float) -> float:
    """Return raw expected value from unit probability and decimal odds."""
    return probability * odds - 1


def _compute_ev_after_tax(
    probability: float,
    odds: float,
    apply_tax: bool,
    tax_rate: float) -> float | None:
    """Return EV adjusted for Polish betting tax when requested."""
    if not apply_tax:
        return None
    return probability * odds * (1 - tax_rate) - 1


def _map_settlement_status(outcome: object) -> SettlementStatus:
    """Map database outcome to API settlement status."""
    if outcome is None or (isinstance(outcome, float) and pd.isna(outcome)):
        return "pending"
    return "won" if int(outcome) == 1 else "lost"


def _map_event_family(row: pd.Series) -> dict[str, Any] | None:
    """Map event family columns when present on a dataframe row."""
    family_id = _optional_int(row.get("event_family_id"))
    family_name = row.get("event_family_name")
    if family_id is None or family_name is None or pd.isna(family_name):
        return None
    return {
        "id": family_id,
        "name": str(family_name)
    }


def _map_bet_row(
        row: pd.Series,
        apply_tax: bool,
        history_window: int,
        history_index: dict[tuple[int, int, str], list[PastMatch]]
        ) -> dict[str, Any]:
    """Map a raw bet recommendation dataframe row."""
    # p.value w DB jest w skali 0-100 — normalizujemy do 0-1
    probability = to_unit_probability(float(row["probability"]))
    odds = float(row["odds"])
    ev = _compute_ev(probability, odds)
    ev_after_tax = _compute_ev_after_tax(
        probability,
        odds,
        apply_tax,
        BETTING_TAX_RATE)
    home_shortcut = _optional_str(row.get("home_team_shortcut"))
    away_shortcut = _optional_str(row.get("away_team_shortcut"))
    return {
        "bet_id": int(row["bet_id"]),
        "match_id": int(row["match_id"]),
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "season_id": int(row["season_id"]),
        "game_date": row["game_date"],
        "home_team": {
            "id": int(row["home_team_id"]),
            "name": str(row["home_team_name"]),
            "shortcut": home_shortcut
        },
        "away_team": {
            "id": int(row["away_team_id"]),
            "name": str(row["away_team_name"]),
            "shortcut": away_shortcut
        },
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "event_family": _map_event_family(row),
        "odds": odds,
        "probability": probability,
        "probability_pct": round(probability * 100, 2),
        "ev": ev,
        "ev_after_tax": ev_after_tax,
        "bookmaker_id": _optional_int(row.get("bookmaker_id")),
        "bookmaker_name": _optional_str(row.get("bookmaker_name")),
        "model_id": int(row["model_id"]),
        "model_name": str(row["model_name"]),
        "settlement_status": _map_settlement_status(row.get("bet_outcome")),
        "custom_bet": bool(int(row.get("custom_bet", 0) or 0)),
        "history": _history_for_row(row, history_window, history_index)
    }


def get_bet_recommendations(
    league_ids: list[int] | None = None,
    season_id: int | None = None,
    event_ids: list[int] | None = None,
    model_ids: list[int] | None = None,
    bookmaker_ids: list[int] | None = None,
    match_id: int | None = None,
    match_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    from_now: bool = False,
    min_odds: float | None = None,
    positive_ev_only: bool = False,
    apply_tax: bool = False,
    settlement_status: str | None = None,
    sort_by: SortBy = "ev",
    sort_order: SortOrder = "desc",
    page: int = 1,
    page_size: int = 50,
    history_window: int = DEFAULT_HISTORY_WINDOW) -> dict[str, Any]:
    """Return paginated bet recommendations with applied filters."""
    _require_history_window(history_window)
    by_history = sort_by == "history"
    frame, total = bet_repository.search_bet_recommendations(
        league_ids=league_ids,
        season_id=season_id,
        event_ids=event_ids,
        model_ids=model_ids,
        bookmaker_ids=bookmaker_ids,
        match_id=match_id,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        min_odds=min_odds,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=BETTING_TAX_RATE,
        settlement_status=settlement_status,
        sort_by="ev" if by_history else sort_by,
        sort_order=sort_order,
        page=1 if by_history else page,
        page_size=page_size,
        unbounded=by_history)
    history_index = _load_history_index(frame, history_window)
    recommendations = [
        _map_bet_row(row, apply_tax, history_window, history_index)
        for _, row in frame.iterrows()
    ]
    if by_history:
        recommendations = page_by_history_rate(
            recommendations, sort_order, page, page_size, "bet_id")
    return {
        "recommendations": recommendations,
        "total_count": total,
        "filters_applied": {
            "league_ids": league_ids,
            "season_id": season_id,
            "event_ids": event_ids,
            "model_ids": model_ids,
            "bookmaker_ids": bookmaker_ids,
            "match_id": match_id,
            "match_date": (
                match_date.isoformat() if match_date else None),
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "from_now": from_now,
            "min_odds": min_odds,
            "positive_ev_only": positive_ev_only,
            "apply_tax": apply_tax,
            "tax_rate": BETTING_TAX_RATE if apply_tax else None,
            "settlement_status": settlement_status,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size,
            "history_window": history_window
        }
    }


def _require_history_window(history_window: int) -> None:
    """Reject a window the strip does not draw."""
    if history_window in HISTORY_WINDOWS:
        return
    raise ValueError("history_window must be 5 or 10")


def _load_history_index(
        frame: pd.DataFrame,
        history_window: int
        ) -> dict[tuple[int, int, str], list[PastMatch]]:
    """Load past matches once per team, fixture and stat filter."""
    anchors = _history_anchors(frame)
    raw = fetch_team_recent_matches(anchors, history_window)
    return _index_past_matches(raw)


def _history_anchors(
        frame: pd.DataFrame
        ) -> list[tuple[int, int, datetime, int, str]]:
    """Build unique team anchors for events that have a strip rule."""
    seen: set[tuple[int, int, str]] = set()
    anchors: list[tuple[int, int, datetime, int, str]] = []
    for _, row in frame.iterrows():
        for anchor in _row_anchors(row):
            key = (anchor[0], anchor[1], anchor[4])
            if key in seen:
                continue
            seen.add(key)
            anchors.append(anchor)
    return anchors


def _row_anchors(
        row: pd.Series) -> list[tuple[int, int, datetime, int, str]]:
    """Return one anchor per sampled team, or none when no rule exists."""
    resolved = _row_rule(row)
    if resolved is None:
        return []
    rule, sport_id = resolved
    stat_filter = history_stat_filter(rule)
    match_id = int(row["match_id"])
    kickoff = pd.Timestamp(row["game_date"]).to_pydatetime()
    anchors: list[tuple[int, int, datetime, int, str]] = []
    for _sample, team_id in sampled_teams(
            rule,
            int(row["home_team_id"]),
            int(row["away_team_id"])):
        anchors.append((
            team_id,
            match_id,
            kickoff,
            sport_id,
            stat_filter))
    return anchors


def _row_rule(row: pd.Series) -> tuple[TeamHistoryRule, int] | None:
    """Return the strip rule and sport, or None when the event has none."""
    sport_id = _optional_int(row.get("sport_id"))
    if sport_id is None:
        return None
    rule = history_rule(
        sport_id, int(row["event_id"]), str(row["event_name"]))
    if rule is None:
        return None
    return rule, sport_id


def _index_past_matches(
        frame: pd.DataFrame
        ) -> dict[tuple[int, int, str], list[PastMatch]]:
    """Group past matches oldest-first by team, fixture and filter."""
    if frame.empty:
        return {}
    ordered = frame.sort_values(
        ["team_id", "anchor_match_id", "stat_filter", "game_date", "match_id"])
    grouped: dict[tuple[int, int, str], list[PastMatch]] = {}
    for _, row in ordered.iterrows():
        key = (
            int(row["team_id"]),
            int(row["anchor_match_id"]),
            str(row["stat_filter"]))
        grouped.setdefault(key, []).append(_past_match(row))
    return grouped


def _past_match(row: pd.Series) -> PastMatch:
    """Map one history query row. Goal columns are filtered in SQL."""
    return PastMatch(
        home_team_id=int(row["home_team_id"]),
        away_team_id=int(row["away_team_id"]),
        home_goals=int(row["home_goals"]),
        away_goals=int(row["away_goals"]),
        result=str(row["result"]),
        home_corners=_optional_int(row.get("home_corners")),
        away_corners=_optional_int(row.get("away_corners")),
        home_fouls=_optional_int(row.get("home_fouls")),
        away_fouls=_optional_int(row.get("away_fouls")),
        home_yellows=_optional_int(row.get("home_yellows")),
        away_yellows=_optional_int(row.get("away_yellows")),
        home_offsides=_optional_int(row.get("home_offsides")),
        away_offsides=_optional_int(row.get("away_offsides")),
        ot_winner=_optional_int(row.get("ot_winner")),
        so_winner=_optional_int(row.get("so_winner")))


def _history_for_row(
        row: pd.Series,
        history_window: int,
        history_index: dict[tuple[int, int, str], list[PastMatch]]
        ) -> dict[str, Any] | None:
    """Build the strip payload, or None when the event has no series."""
    resolved = _row_rule(row)
    if resolved is None:
        return None
    rule, _sport_id = resolved
    return {
        "window": history_window,
        "line": rule.line,
        "side": rule.comparator,
        "series": _history_series(row, rule, history_index)}


def _history_series(
        row: pd.Series,
        rule: TeamHistoryRule,
        history_index: dict[tuple[int, int, str], list[PastMatch]]
        ) -> list[dict[str, Any]]:
    """Build home-then-away strips. A named side stays a single strip."""
    stat_filter = history_stat_filter(rule)
    match_id = int(row["match_id"])
    series: list[dict[str, Any]] = []
    for sample, team_id in sampled_teams(
            rule,
            int(row["home_team_id"]),
            int(row["away_team_id"])):
        matches = history_index.get((team_id, match_id, stat_filter), [])
        values = _series_values(rule, team_id, matches)
        name, shortcut = _subject_label(rule, row, sample)
        series.append(_series_payload(
            sample, values, rule, name, shortcut))
    return series


def _subject_label(
        rule: TeamHistoryRule,
        row: pd.Series,
        sample: str) -> tuple[str | None, str | None]:
    """Name a match-level strip. A side named by the event stays blank."""
    if not names_sampled_team(rule):
        return None, None
    if sample == "away":
        return (
            str(row["away_team_name"]),
            _optional_str(row.get("away_team_shortcut")))
    return (
        str(row["home_team_name"]),
        _optional_str(row.get("home_team_shortcut")))


def _series_payload(
        sample: str,
        values: list[float],
        rule: TeamHistoryRule,
        subject_name: str | None,
        subject_shortcut: str | None) -> dict[str, Any]:
    """Count hits on one team's already oldest-first series."""
    hits = sum(
        1 for value in values
        if is_history_hit(value, rule.line, rule.comparator))
    return {
        "sample": sample,
        "played": len(values),
        "hits": hits,
        "points": [{"value": value} for value in values],
        "subject_name": subject_name,
        "subject_shortcut": subject_shortcut}


def _series_values(
        rule: TeamHistoryRule,
        team_id: int,
        matches: list[PastMatch]) -> list[float]:
    """Drop a row that still has no readable stat after the SQL filter."""
    values: list[float] = []
    for match in matches:
        value = stat_value(rule, team_id, match)
        if value is None:
            continue
        values.append(value)
    return values


def _map_opportunity_row(row: pd.Series) -> dict[str, Any]:
    """Map a market opportunity dataframe row to the API contract."""
    probability = _optional_float(row.get("probability"))
    if probability is None:
        raw_pct = _optional_float(row.get("probability_pct"))
        probability = (
            to_unit_probability(raw_pct) if raw_pct is not None else None)
    probability_pct = _optional_float(row.get("probability_pct"))
    if probability_pct is None and probability is not None:
        probability_pct = round(probability * 100, 2)

    odds = _optional_float(row.get("odds"))
    implied = (1.0 / odds) if odds is not None and odds > 0 else None
    ev = _optional_float(row.get("ev"))
    ev_after_tax = _optional_float(row.get("ev_after_tax"))
    if (
        probability is not None
        and odds is not None
        and ev is None
    ):
        ev = _compute_ev(probability, odds)
    if (
        probability is not None
        and odds is not None
        and ev_after_tax is None
        and str(row.get("ranking_basis")) == "ev_after_tax"
    ):
        ev_after_tax = _compute_ev_after_tax(
            probability, odds, True, BETTING_TAX_RATE)

    return {
        "match_id": int(row["match_id"]),
        "sport_id": int(row["sport_id"]),
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "game_date": row["game_date"],
        "home_team": str(row["home_team"]),
        "away_team": str(row["away_team"]),
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "model_id": _optional_int(row.get("model_id")),
        "model_name": _optional_str(row.get("model_name")),
        "probability": probability,
        "probability_pct": probability_pct,
        "odds": odds,
        "bookmaker_id": _optional_int(row.get("bookmaker_id")),
        "bookmaker_name": _optional_str(row.get("bookmaker_name")),
        "implied_probability": implied,
        "ev": ev,
        "ev_after_tax": ev_after_tax,
        "source": str(row["source"]),
        "ranking_basis": str(row["ranking_basis"])
    }


def get_market_opportunities(
    sport_id: int,
    match_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    from_now: bool = True,
    apply_tax: bool = True,
    positive_ev_only: bool = True,
    include_prediction_fallback: bool = True,
    one_per_match: bool = True,
    limit: int = _DEFAULT_OPPORTUNITIES_LIMIT) -> dict[str, Any]:
    """Return a fixed-size global ranking for one sport and date window."""
    resolved_limit = max(1, min(limit, _MAX_OPPORTUNITIES_LIMIT))
    frame, total, source_counts = bet_repository.search_market_opportunities(
        sport_id=sport_id,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        apply_tax=apply_tax,
        tax_rate=BETTING_TAX_RATE,
        positive_ev_only=positive_ev_only,
        include_prediction_fallback=include_prediction_fallback,
        one_per_match=one_per_match,
        limit=resolved_limit)

    opportunities = [
        _map_opportunity_row(row)
        for _, row in frame.iterrows()
    ] if not frame.empty else []

    warnings: list[str] = []
    prediction_count = int(source_counts.get("prediction", 0))
    if prediction_count > 0:
        no_odds = any(
            item["odds"] is None and item["source"] == "prediction"
            for item in opportunities)
        if no_odds:
            warnings.append(
                "Ranking was topped up with predictions that have no odds; "
                "those rows use probability ranking and are not value bets.")
        else:
            warnings.append(
                "Ranking was topped up with prediction-only candidates.")

    return {
        "opportunities": opportunities,
        "total_count": total,
        "filters_applied": {
            "sport_id": sport_id,
            "match_date": (
                match_date.isoformat() if match_date else None),
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "from_now": from_now,
            "apply_tax": apply_tax,
            "tax_rate": BETTING_TAX_RATE if apply_tax else None,
            "positive_ev_only": positive_ev_only,
            "include_prediction_fallback": include_prediction_fallback,
            "one_per_match": one_per_match,
            "limit": resolved_limit
        },
        "source_counts": source_counts,
        "warnings": warnings
    }
