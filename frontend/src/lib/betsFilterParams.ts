import type {
  BetSortBy,
  BetSortOrder,
  SettlementStatus,
} from "@/types/api";

export interface BetsFilterValues {
  leagueIds: number[];
  eventIds: number[];
  modelIds: number[];
  matchDate: string;
  fromNow: boolean;
  minOdds: number;
  positiveEvOnly: boolean;
  applyTax: boolean;
  settlementStatus: SettlementStatus | "";
  sortBy: BetSortBy;
  sortOrder: BetSortOrder;
  page: number;
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
  if (nextState.matchDate) {
    params.set("match_date", nextState.matchDate);
  }
  if (nextState.fromNow) {
    params.set("from_now", "true");
  }
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
