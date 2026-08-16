import type {
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
} from "@/types/api";

export interface StatsFilterValues {
  leagueIds: number[];
  seasonId: number | null;
  modelResultIds: number[];
  modelOuIds: number[];
  modelBttsIds: number[];
  dateFrom: string;
  dateTo: string;
  roundFrom: string;
  roundTo: string;
  statType: AnalyticsStatType;
  settledOnly: boolean;
  positiveEvOnly: boolean;
  applyTax: boolean;
  groupBy: AnalyticsGroupBy;
  aggregationMetric: AnalyticsAggregationMetric;
}

export function areAllOptionsSelected(
  selectedIds: number[],
  availableIds: number[],
): boolean {
  if (availableIds.length === 0) {
    return selectedIds.length === 0;
  }
  if (selectedIds.length !== availableIds.length) {
    return false;
  }
  const selected = new Set(selectedIds);
  return availableIds.every((id) => selected.has(id));
}

export function isDefaultLeagueFilter(
  selectedIds: number[],
  availableIds: number[],
): boolean {
  return (
    selectedIds.length === 0 ||
    areAllOptionsSelected(selectedIds, availableIds)
  );
}

export function visibleLeagueFilterIds(
  selectedIds: number[],
  availableIds: number[],
): number[] {
  // puste checkboxy oznaczają „wszystkie ligi”, tak jak w kąciku bukmacherskim
  if (isDefaultLeagueFilter(selectedIds, availableIds)) {
    return [];
  }
  return selectedIds;
}

export function resolveAnalyticsLeagueIds(
  selectedIds: number[],
  footballLeagueIds: number[],
): number[] {
  if (isDefaultLeagueFilter(selectedIds, footballLeagueIds)) {
    return footballLeagueIds;
  }
  return selectedIds;
}

export function serializeLeagueFilter(
  selectedIds: number[],
  availableIds: number[],
): string | undefined {
  if (isDefaultLeagueFilter(selectedIds, availableIds)) {
    return undefined;
  }
  return selectedIds.join(",");
}

export function buildStatsFilterQuery(
  nextState: StatsFilterValues,
  availableLeagueIds: number[],
): string {
  const params = new URLSearchParams();
  const leagueFilter = serializeLeagueFilter(
    nextState.leagueIds,
    availableLeagueIds,
  );
  if (leagueFilter) {
    params.set("league_ids", leagueFilter);
  }
  if (nextState.seasonId) {
    params.set("season_id", String(nextState.seasonId));
  }
  if (nextState.modelResultIds.length > 0) {
    params.set("model_result_ids", nextState.modelResultIds.join(","));
  }
  if (nextState.modelOuIds.length > 0) {
    params.set("model_ou_ids", nextState.modelOuIds.join(","));
  }
  if (nextState.modelBttsIds.length > 0) {
    params.set("model_btts_ids", nextState.modelBttsIds.join(","));
  }
  if (nextState.dateFrom) {
    params.set("date_from", nextState.dateFrom);
  }
  if (nextState.dateTo) {
    params.set("date_to", nextState.dateTo);
  }
  if (nextState.roundFrom) {
    params.set("round_from", nextState.roundFrom);
  }
  if (nextState.roundTo) {
    params.set("round_to", nextState.roundTo);
  }
  if (nextState.statType !== "all") {
    params.set("stat_type", nextState.statType);
  }
  if (!nextState.settledOnly) {
    params.set("settled_only", "false");
  }
  if (nextState.positiveEvOnly) {
    params.set("positive_ev_only", "true");
  }
  if (nextState.applyTax) {
    params.set("apply_tax", "true");
  }
  if (nextState.groupBy !== "none") {
    params.set("group_by", nextState.groupBy);
  }
  if (nextState.aggregationMetric !== "accuracy") {
    params.set("aggregation_metric", nextState.aggregationMetric);
  }
  return params.toString();
}

export function statsFilterPath(
  nextState: StatsFilterValues,
  availableLeagueIds: number[],
): string {
  const query = buildStatsFilterQuery(nextState, availableLeagueIds);
  return query ? `/stats?${query}` : "/stats";
}
