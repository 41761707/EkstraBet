/** Presentation helpers for tipster bankroll, coupons and ranking. */

import { formatOdds } from "@/lib/format";
import { parseIdList, parsePositiveInt } from "@/lib/searchParams";
import type {
  BankrollSettings,
  CouponCreateRequest,
  CouponSummary,
  CurrencyCode,
  LeaderboardSortBy,
  LeaderboardSortOrder,
  PublicBankroll,
  StakeInputMode,
  TipsterEventFamilyFilter,
  TipsterLeaderboardQuery,
} from "@/types/api";

export const TYPERS_PATH = "/typers";
export const DEFAULT_TIPSTER_PAGE = 1;
export const DEFAULT_TIPSTER_PAGE_SIZE = 20;
export const DEFAULT_LEADERBOARD_SORT_BY: LeaderboardSortBy = "profit_total";
export const DEFAULT_LEADERBOARD_SORT_ORDER: LeaderboardSortOrder = "desc";
export const TIPSTER_EMPTY_VALUE = "—";

const LEADERBOARD_SORT_BY_VALUES: readonly LeaderboardSortBy[] = [
  "profit_total",
  "roi_pct",
  "accuracy_pct",
  "avg_odds",
  "avg_profit",
  "bets_count",
  "current_balance",
];

export interface TipsterLeaderboardFilters {
  isSystem: 0 | 1 | null;
  leagueIds: number[];
  tier: number | null;
  eventFamily: TipsterEventFamilyFilter | null;
  dateFrom: string;
  dateTo: string;
  sortBy: LeaderboardSortBy;
  sortOrder: LeaderboardSortOrder;
  page: number;
  pageSize: number;
}

export function createDefaultTipsterLeaderboardFilters(
  overrides: Partial<TipsterLeaderboardFilters> = {},
): TipsterLeaderboardFilters {
  return {
    isSystem: null,
    leagueIds: [],
    tier: null,
    eventFamily: null,
    dateFrom: "",
    dateTo: "",
    sortBy: DEFAULT_LEADERBOARD_SORT_BY,
    sortOrder: DEFAULT_LEADERBOARD_SORT_ORDER,
    page: DEFAULT_TIPSTER_PAGE,
    pageSize: DEFAULT_TIPSTER_PAGE_SIZE,
    ...overrides,
  };
}

export function parseTipsterLeaderboardFilters(
  params: Record<string, string | undefined>,
): TipsterLeaderboardFilters {
  return createDefaultTipsterLeaderboardFilters({
    isSystem: parseIsSystemFilter(params.is_system),
    leagueIds: parseIdList(params.league_ids),
    tier: parsePositiveInt(params.tier),
    eventFamily: parseEventFamilyFilter(params.event_family),
    dateFrom: params.date_from ?? "",
    dateTo: params.date_to ?? "",
    sortBy: parseLeaderboardSortBy(params.sort_by),
    sortOrder: parseLeaderboardSortOrder(params.sort_order),
    page: parsePositiveInt(params.page) ?? DEFAULT_TIPSTER_PAGE,
    pageSize: parsePositiveInt(params.page_size) ?? DEFAULT_TIPSTER_PAGE_SIZE,
  });
}

export function areTipsterDateFiltersValid(
  filters: TipsterLeaderboardFilters,
): boolean {
  if (!filters.dateFrom || !filters.dateTo) {
    return true;
  }
  return filters.dateFrom <= filters.dateTo;
}

export function buildTipsterLeaderboardQuery(
  filters: TipsterLeaderboardFilters,
): string {
  const params = new URLSearchParams();
  if (filters.isSystem !== null) {
    params.set("is_system", String(filters.isSystem));
  }
  if (filters.leagueIds.length > 0) {
    params.set("league_ids", filters.leagueIds.join(","));
  }
  if (filters.tier !== null) {
    params.set("tier", String(filters.tier));
  }
  if (filters.eventFamily !== null) {
    params.set("event_family", String(filters.eventFamily));
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.sortBy !== DEFAULT_LEADERBOARD_SORT_BY) {
    params.set("sort_by", filters.sortBy);
  }
  if (filters.sortOrder !== DEFAULT_LEADERBOARD_SORT_ORDER) {
    params.set("sort_order", filters.sortOrder);
  }
  if (filters.page > DEFAULT_TIPSTER_PAGE) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize !== DEFAULT_TIPSTER_PAGE_SIZE) {
    params.set("page_size", String(filters.pageSize));
  }
  return params.toString();
}

export function tipsterLeaderboardPath(
  filters: TipsterLeaderboardFilters,
): string {
  const query = buildTipsterLeaderboardQuery(filters);
  return query ? `${TYPERS_PATH}?${query}` : TYPERS_PATH;
}

/** Maps URL filters to the GET /tipsters/leaderboard query. */
export function toTipsterLeaderboardQuery(
  filters: TipsterLeaderboardFilters,
): TipsterLeaderboardQuery {
  return {
    isSystem: filters.isSystem ?? undefined,
    leagueIds: filters.leagueIds,
    tier: filters.tier ?? undefined,
    eventFamily: filters.eventFamily ?? undefined,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
    sortBy: filters.sortBy,
    sortOrder: filters.sortOrder,
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function couponStakeFields(
  mode: StakeInputMode,
  moneyAmount: number | null,
  unitCount: number | null,
): Pick<
  CouponCreateRequest,
  "stake_input_mode" | "stake_amount" | "stake_units"
> {
  if (mode === "units") {
    return {
      stake_input_mode: "units",
      stake_amount: null,
      stake_units: unitCount,
    };
  }
  return {
    stake_input_mode: "money",
    stake_amount: moneyAmount,
    stake_units: null,
  };
}

/**
 * Display-only money equivalent of a units stake.
 * The API still resolves and quantizes; do not send this as stake_amount.
 */
export function previewStakeMoney(
  mode: StakeInputMode,
  moneyAmount: number | null,
  unitCount: number | null,
  unitSize: number,
): number | null {
  if (mode === "units") {
    if (unitCount === null) {
      return null;
    }
    return unitCount * unitSize;
  }
  return moneyAmount;
}

export function formatTipsterRoi(roiPct: number | null): string {
  if (roiPct === null || Number.isNaN(roiPct)) {
    return TIPSTER_EMPTY_VALUE;
  }
  const sign = roiPct > 0 ? "+" : "";
  return `${sign}${roiPct.toFixed(1)}%`;
}

export function formatTipsterAmount(
  value: number | null,
  currency: CurrencyCode,
): string {
  if (value === null || Number.isNaN(value)) {
    return TIPSTER_EMPTY_VALUE;
  }
  return `${value.toFixed(2)} ${currency}`;
}

export function formatTipsterProfit(
  value: number | null,
  currency: CurrencyCode,
): string {
  if (value === null || Number.isNaN(value)) {
    return TIPSTER_EMPTY_VALUE;
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} ${currency}`;
}

/** Renders API combined_odds; never multiplies leg odds in the UI. */
export function formatCouponCombinedOdds(
  coupon: Pick<CouponSummary, "combined_odds">,
): string {
  return formatOdds(coupon.combined_odds);
}

export function isOwnerBankroll(
  bankroll: BankrollSettings | PublicBankroll | null,
): bankroll is BankrollSettings {
  return (
    bankroll !== null &&
    "initial_capital" in bankroll &&
    "unit_size" in bankroll
  );
}

export function isCombinedLeg(eventIds: number[]): boolean {
  return eventIds.length >= 2;
}

function parseIsSystemFilter(value: string | undefined): 0 | 1 | null {
  if (value === "0") {
    return 0;
  }
  if (value === "1") {
    return 1;
  }
  return null;
}

function parseEventFamilyFilter(
  value: string | undefined,
): TipsterEventFamilyFilter | null {
  if (!value?.trim()) {
    return null;
  }
  const token = value.trim();
  if (token.toUpperCase() === "OTHER") {
    return "OTHER";
  }
  if (token === "0") {
    return 0;
  }
  const parsed = Number(token);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function parseLeaderboardSortBy(value: string | undefined): LeaderboardSortBy {
  if (value !== undefined && isLeaderboardSortBy(value)) {
    return value;
  }
  return DEFAULT_LEADERBOARD_SORT_BY;
}

function isLeaderboardSortBy(value: string): value is LeaderboardSortBy {
  return LEADERBOARD_SORT_BY_VALUES.some((item) => item === value);
}

function parseLeaderboardSortOrder(
  value: string | undefined,
): LeaderboardSortOrder {
  if (value === "asc" || value === "desc") {
    return value;
  }
  return DEFAULT_LEADERBOARD_SORT_ORDER;
}
