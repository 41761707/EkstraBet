import type { GetModelAnalyticsOptions } from "@/lib/apiClient";
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

/** First expander open loads models + analytics; later Apply refetches in the hook. */
export function shouldFetchScopedPredictionStats(
  isOpen: boolean,
  hasLoadedOnce: boolean,
): boolean {
  return isOpen && !hasLoadedOnce;
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
