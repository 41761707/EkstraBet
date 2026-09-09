import type { GetModelAnalyticsOptions } from "@/lib/apiClient";
import type { ModelsByFamily } from "@/lib/modelsByFamily";
import type { ModelAnalyticsResponse } from "@/types/api";

export interface ScopedPredictionStatsScope {
  leagueId: number;
  seasonId: number;
  teamId?: number;
  heading: string;
  description: string;
}

export interface ScopedPredictionStatsFiltersState {
  modelResultIds: number[];
  modelOuIds: number[];
  modelBttsIds: number[];
  dateFrom: string;
  dateTo: string;
  applyTax: boolean;
}

export const EMPTY_SCOPED_PREDICTION_STATS_MESSAGE =
  "Brak rozliczonych predykcji w wybranym zakresie.";

const SCOPED_ANALYTICS_STAT_TYPE = "all" as const;
const SCOPED_SETTLED_ONLY = true;

export function createDefaultScopedPredictionStatsFilters(): ScopedPredictionStatsFiltersState {
  return {
    modelResultIds: [],
    modelOuIds: [],
    modelBttsIds: [],
    dateFrom: "",
    dateTo: "",
    applyTax: false,
  };
}

/** Content identity of filters — ignores object/array references. */
export function scopedPredictionStatsFiltersKey(
  filters: ScopedPredictionStatsFiltersState,
): string {
  return [
    filters.dateFrom,
    filters.dateTo,
    filters.applyTax ? "1" : "0",
    filters.modelResultIds.join(","),
    filters.modelOuIds.join(","),
    filters.modelBttsIds.join(","),
  ].join("|");
}

/** Like /stats: keep a selection, otherwise the first family id, else omit the family. */
export function pickDefaultModelIds(
  selected: number[],
  available: { id: number }[],
): number[] | undefined {
  if (selected.length > 0) {
    return selected;
  }
  const first = available[0];
  return first ? [first.id] : undefined;
}

/** Empty or one-sided dates are valid; both set and Od > Do is not. */
export function areScopedDateFiltersValid(
  dateFrom: string,
  dateTo: string,
): boolean {
  if (!dateFrom || !dateTo) {
    return true;
  }
  return dateFrom <= dateTo;
}

export function toModelAnalyticsQuery(
  scope: ScopedPredictionStatsScope,
  filters: ScopedPredictionStatsFiltersState,
): GetModelAnalyticsOptions {
  return {
    statType: SCOPED_ANALYTICS_STAT_TYPE,
    settledOnly: SCOPED_SETTLED_ONLY,
    leagueIds: [scope.leagueId],
    seasonId: scope.seasonId,
    applyTax: filters.applyTax,
    ...optionalIdList("modelResultIds", filters.modelResultIds),
    ...optionalIdList("modelOuIds", filters.modelOuIds),
    ...optionalIdList("modelBttsIds", filters.modelBttsIds),
    ...optionalDate("dateFrom", filters.dateFrom),
    ...optionalDate("dateTo", filters.dateTo),
    ...(scope.teamId !== undefined ? { teamId: scope.teamId } : {}),
  };
}

export function isAnalyticsEmpty(analytics: ModelAnalyticsResponse): boolean {
  const categories = Object.values(analytics.categories);
  if (categories.length === 0) {
    return true;
  }
  return categories.every(
    (category) =>
      category.predictions.total === 0 && category.bets.total === 0,
  );
}

/** First expander open loads models; skip once that stage has returned. */
export function shouldFetchScopedPredictionStats(
  isOpen: boolean,
  hasLoadedModels: boolean,
): boolean {
  return isOpen && !hasLoadedModels;
}

/** After models, load analytics unless already loaded or the expander is closed. */
export function shouldFetchScopedPredictionAnalytics(
  isOpen: boolean,
  hasLoadedModels: boolean,
  hasLoadedOnce: boolean,
): boolean {
  return isOpen && hasLoadedModels && !hasLoadedOnce;
}

/** Fills empty family selections with the first available model id. */
export function withDefaultScopedModelIds(
  filters: ScopedPredictionStatsFiltersState,
  models: ModelsByFamily,
): ScopedPredictionStatsFiltersState {
  return {
    ...filters,
    modelResultIds:
      pickDefaultModelIds(filters.modelResultIds, models.result) ?? [],
    modelOuIds: pickDefaultModelIds(filters.modelOuIds, models.ou) ?? [],
    modelBttsIds: pickDefaultModelIds(filters.modelBttsIds, models.btts) ?? [],
  };
}

/** Clears dates and tax, then selects the first model of each family. */
export function resetScopedPredictionStatsFilters(
  models: ModelsByFamily,
): ScopedPredictionStatsFiltersState {
  return withDefaultScopedModelIds(
    createDefaultScopedPredictionStatsFilters(),
    models,
  );
}

export function hasScopedModelOptions(models: ModelsByFamily): boolean {
  return (
    models.result.length > 0 ||
    models.ou.length > 0 ||
    models.btts.length > 0
  );
}

function optionalIdList(
  key: "modelResultIds" | "modelOuIds" | "modelBttsIds",
  ids: number[],
): Pick<GetModelAnalyticsOptions, typeof key> {
  if (ids.length === 0) {
    return {};
  }
  return { [key]: ids };
}

function optionalDate(
  key: "dateFrom" | "dateTo",
  value: string,
): Pick<GetModelAnalyticsOptions, typeof key> {
  if (!value) {
    return {};
  }
  return { [key]: value };
}
