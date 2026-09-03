import {
  parseBoolean,
  parseIdList,
  parsePositiveInt,
  todayIsoDate,
} from "@/lib/searchParams";
import type {
  BetSortBy,
  BetSortOrder,
  SettlementStatus,
} from "@/types/api";

export interface BetsFilterValues {
  leagueIds: number[];
  eventIds: number[];
  modelIds: number[];
  dateFrom: string;
  dateTo: string;
  fromNow: boolean;
  minOdds: number;
  positiveEvOnly: boolean;
  applyTax: boolean;
  settlementStatus: SettlementStatus | "";
  sortBy: BetSortBy;
  sortOrder: BetSortOrder;
  page: number;
}

export function createDefaultBetsFilterValues(
  overrides: Partial<BetsFilterValues> = {},
): BetsFilterValues {
  const today = todayIsoDate();
  return {
    leagueIds: [],
    eventIds: [],
    modelIds: [],
    dateFrom: today,
    dateTo: today,
    fromNow: false,
    minOdds: 1.5,
    positiveEvOnly: false,
    applyTax: false,
    settlementStatus: "",
    sortBy: "ev",
    sortOrder: "desc",
    page: 1,
    ...overrides,
  };
}

export function parseBetsDateRange(
  params: Record<string, string | undefined>,
): Pick<BetsFilterValues, "dateFrom" | "dateTo"> {
  if (parseBoolean(params.all_dates)) {
    return { dateFrom: "", dateTo: "" };
  }
  if (params.date_from !== undefined || params.date_to !== undefined) {
    return {
      dateFrom: params.date_from ?? "",
      dateTo: params.date_to ?? "",
    };
  }
  if (params.match_date) {
    return { dateFrom: params.match_date, dateTo: params.match_date };
  }
  const today = todayIsoDate();
  return { dateFrom: today, dateTo: today };
}

export function parseBetsFilterValues(
  params: Record<string, string | undefined>,
): BetsFilterValues {
  return createDefaultBetsFilterValues({
    leagueIds: parseIdList(params.league_ids),
    eventIds: parseIdList(params.event_ids),
    modelIds: parseIdList(params.model_ids),
    ...parseBetsDateRange(params),
    fromNow: parseBoolean(params.from_now),
    minOdds: params.min_odds ? Number(params.min_odds) : 1.5,
    positiveEvOnly: parseBoolean(params.positive_ev_only),
    applyTax: parseBoolean(params.apply_tax),
    settlementStatus: (params.settlement_status ?? "") as SettlementStatus | "",
    sortBy: (params.sort_by as BetSortBy | undefined) ?? "ev",
    sortOrder: (params.sort_order as BetSortOrder | undefined) ?? "desc",
    page: parsePositiveInt(params.page) ?? 1,
  });
}

export function areBetsDateFiltersValid(filters: BetsFilterValues): boolean {
  if (!filters.dateFrom || !filters.dateTo) {
    return true;
  }
  return filters.dateFrom <= filters.dateTo;
}

export function betsDateQueryParams(filters: BetsFilterValues): {
  dateFrom?: string;
  dateTo?: string;
  fromNow: boolean;
} {
  if (filters.fromNow) {
    return { fromNow: true };
  }
  return {
    fromNow: false,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
  };
}

export function buildBetsFilterQuery(nextState: BetsFilterValues): string {
  const params = new URLSearchParams();
  if (nextState.leagueIds.length > 0) {
    params.set("league_ids", nextState.leagueIds.join(","));
  }
  if (nextState.eventIds.length > 0) {
    params.set("event_ids", nextState.eventIds.join(","));
  }
  if (nextState.modelIds.length > 0) {
    params.set("model_ids", nextState.modelIds.join(","));
  }
  appendBetsDateQueryParams(params, nextState);
  if (nextState.minOdds > 1) {
    params.set("min_odds", String(nextState.minOdds));
  }
  if (nextState.positiveEvOnly) {
    params.set("positive_ev_only", "true");
  }
  if (nextState.applyTax) {
    params.set("apply_tax", "true");
  }
  if (nextState.settlementStatus) {
    params.set("settlement_status", nextState.settlementStatus);
  }
  if (nextState.sortBy !== "ev") {
    params.set("sort_by", nextState.sortBy);
  }
  if (nextState.sortOrder !== "desc") {
    params.set("sort_order", nextState.sortOrder);
  }
  if (nextState.page > 1) {
    params.set("page", String(nextState.page));
  }
  return params.toString();
}

export function betsFilterPath(nextState: BetsFilterValues): string {
  const query = buildBetsFilterQuery(nextState);
  return query ? `/bets?${query}` : "/bets";
}

function appendBetsDateQueryParams(
  params: URLSearchParams,
  nextState: BetsFilterValues,
): void {
  if (nextState.fromNow) {
    params.set("from_now", "true");
    return;
  }
  if (!nextState.dateFrom && !nextState.dateTo) {
    params.set("all_dates", "true");
    return;
  }
  if (nextState.dateFrom) {
    params.set("date_from", nextState.dateFrom);
  }
  if (nextState.dateTo) {
    params.set("date_to", nextState.dateTo);
  }
}
