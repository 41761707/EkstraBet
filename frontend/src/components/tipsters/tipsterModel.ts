/** Presentation helpers for tipster bankroll, coupons and ranking. */

import { ApiError } from "@/lib/apiShared";
import { addIsoCalendarDays, getWarsawDateIso, normalizeWarsawNaiveDateTime } from "@/lib/date";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import { parseBoolean, parseIdList, parsePositiveInt } from "@/lib/searchParams";
import type {
  AdviseStakeRequest,
  BankrollSettings,
  CatalogEvent,
  CatalogMatch,
  CouponCreateRequest,
  CouponLegCreate,
  CouponLegSummary,
  CouponSummary,
  CurrencyCode,
  LeaderboardSortBy,
  LeaderboardSortOrder,
  LegAdvice,
  PerformanceItem,
  PublicBankroll,
  StakeInputMode,
  TipsterCatalogQuery,
  TipsterEventFamilyFilter,
  TipsterLeaderboardQuery,
} from "@/types/api";

export const TYPERS_PATH = "/typers";
export const DEFAULT_TIPSTER_PAGE = 1;
export const DEFAULT_TIPSTER_PAGE_SIZE = 20;
export const DEFAULT_LEADERBOARD_SORT_BY: LeaderboardSortBy = "profit_total";
export const DEFAULT_LEADERBOARD_SORT_ORDER: LeaderboardSortOrder = "desc";
export const TIPSTER_EMPTY_VALUE = "—";
export const MAX_COUPON_LEGS = 8;
export const MIN_LEG_ODDS = 1.01;
export const TIPSTER_CURRENCIES: readonly CurrencyCode[] = ["PLN", "EUR", "USD"];
export const TIPSTER_BETTING_TAX_RATE = 0.12;
export const APPLY_TAX_LABEL = "Uwzględnij podatek 12%";
export const APPLY_TAX_HINT =
  "Zaznaczone: wygrana liczona od 88% stawki, przegrana od pełnej kwoty.";
export const ASK_STAKE_ADVICE_LABEL = "Poproś o sugestię dotyczącą stawki";
export const STAKE_ADVICE_CONFIDENCE_LABEL = "Twoja pewność kuponu wyrażona w procentach";
export const APPLY_STAKE_ADVICE_LABEL = "Zastosuj";
export const STAKE_ADVICE_NO_AGENT_LABEL =
  "Agent systemowy nie grał tych zdarzeń.";
export const STAKE_ADVICE_EMPTY_LEGS_HINT =
  "Dodaj zdarzenie, żeby przeliczyć podpowiedź.";
export const STAKE_ADVICE_LOADING_LABEL = "Przeliczanie podpowiedzi…";
export const DEFAULT_STAKE_CONFIDENCE = 50;
export const STAKE_ADVICE_DEBOUNCE_MS = 400;
export const STAKE_ADVICE_NETWORK_ERROR =
  "Nie udało się policzyć rady. Spróbuj ponownie.";

const GENERIC_TIPSTER_SAVE_ERROR =
  "Nie udało się zapisać. Spróbuj ponownie.";

export const COMBINED_SELECTION_LABEL = "Łączone";

const TIPSTER_API_MESSAGES: Record<string, string> = {
  "Bankroll not configured": "Najpierw skonfiguruj kapitał.",
  "Initial capital cannot be changed after onboarding":
    "Kapitał startowy można zwiększyć tylko doładowaniem.",
  "Currency cannot be changed after the first coupon":
    "Waluty nie można zmienić po pierwszym kuponie.",
  "Odds must be at least 1.01": "Kurs zdarzenia musi wynosić co najmniej 1.01.",
  "Stake must be greater than 0": "Stawka musi być większa od zera.",
  "Coupon must have between 1 and 8 legs":
    "Kupon musi mieć od 1 do 8 zdarzeń.",
  "Duplicate match on coupon":
    "Ten mecz jest już na kuponie. Dodatkowe typy dopisz do istniejącego zdarzenia.",
  "Duplicate event_id on a leg": "To samo zdarzenie nie może się powtórzyć.",
  "Event is not settleable": "Wybrane zdarzenie nie jest rozliczalne.",
  "Match is finished or not open for betting":
    "Mecz jest zakończony albo niedostępny.",
  "User account is inactive": "Konto użytkownika jest nieaktywne.",
  "Each leg must have at least one event":
    "Każde zdarzenie na kuponie musi zawierać co najmniej jeden typ.",
  "Invalid coupon leg": "Zdarzenie na kuponie jest nieprawidłowe.",
  "Unsupported currency": "Nieobsługiwana waluta.",
  "Invalid stake_input_mode": "Nieobsługiwany tryb stawki.",
  "unit_size must be greater than 0": "Jednostka musi być większa od zera.",
  "amount must be greater than 0": "Kwota musi być większa od zera.",
  "Invalid leg source": "Nieobsługiwane źródło kursu.",
  "Invalid event_id": "Nieprawidłowe zdarzenie.",
  "Invalid bookmaker_id": "Nieprawidłowy bukmacher.",
  "System accounts cannot use /me mutations":
    "Konto systemowe nie może zapisywać kuponów.",
  "User not found": "Nie znaleziono użytkownika.",
};

export interface DraftCouponLeg {
  matchId: number;
  eventIds: number[];
  odds: string;
  bookmakerId?: number | null;
}

export type DraftLegMutationError = "duplicate_event" | "max_legs";
export type PerformanceDimension = "family" | "league" | "country";

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
  eventIds: number[];
  eventFamily: TipsterEventFamilyFilter | null;
  dateFrom: string;
  dateTo: string;
  sortBy: LeaderboardSortBy;
  sortOrder: LeaderboardSortOrder;
  page: number;
  pageSize: number;
  applyTax: boolean;
}

export function createDefaultTipsterLeaderboardFilters(
  overrides: Partial<TipsterLeaderboardFilters> = {},
): TipsterLeaderboardFilters {
  return {
    isSystem: null,
    leagueIds: [],
    tier: null,
    eventIds: [],
    eventFamily: null,
    dateFrom: "",
    dateTo: "",
    sortBy: DEFAULT_LEADERBOARD_SORT_BY,
    sortOrder: DEFAULT_LEADERBOARD_SORT_ORDER,
    page: DEFAULT_TIPSTER_PAGE,
    pageSize: DEFAULT_TIPSTER_PAGE_SIZE,
    applyTax: false,
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
    eventIds: parseIdList(params.event_ids),
    eventFamily: parseEventFamilyFilter(params.event_family),
    dateFrom: params.date_from ?? "",
    dateTo: params.date_to ?? "",
    sortBy: parseLeaderboardSortBy(params.sort_by),
    sortOrder: parseLeaderboardSortOrder(params.sort_order),
    page: parsePositiveInt(params.page) ?? DEFAULT_TIPSTER_PAGE,
    pageSize: parsePositiveInt(params.page_size) ?? DEFAULT_TIPSTER_PAGE_SIZE,
    applyTax: parseBoolean(params.apply_tax),
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
  if (filters.eventIds.length > 0) {
    params.set("event_ids", filters.eventIds.join(","));
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
  if (filters.applyTax) {
    params.set("apply_tax", "true");
  }
  return params.toString();
}

export function tipsterLeaderboardPath(
  filters: TipsterLeaderboardFilters,
): string {
  const query = buildTipsterLeaderboardQuery(filters);
  return query ? `${TYPERS_PATH}?${query}` : TYPERS_PATH;
}

export function isMissingTipsterProfileError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** Coupon lists are owner-or-system; foreign humans stay at coupons: null. */
export function isPublicCouponHistoryVisible(
  isOwnProfile: boolean,
  isSystemProfile: boolean,
): boolean {
  return isOwnProfile || isSystemProfile;
}

export const TIPSTER_FILTER_CATALOG_ERROR_TITLE =
  "Nie udało się wczytać części filtrów";

export function tipsterFilterCatalogMessage(
  leaguesFailed: boolean,
  familiesFailed: boolean,
): string | null {
  if (!leaguesFailed && !familiesFailed) {
    return null;
  }
  if (leaguesFailed && familiesFailed) {
    return (
      "Listy lig i zdarzeń są niedostępne. Ranking poniżej jest bez tych filtrów."
    );
  }
  if (leaguesFailed) {
    return "Lista lig jest niedostępna. Ranking poniżej działa, ale bez filtra lig.";
  }
  return (
    "Lista zdarzeń jest niedostępna. Ranking poniżej działa, ale bez tego filtra."
  );
}

/** Maps URL filters to the GET /tipsters/leaderboard query. */
export function toTipsterLeaderboardQuery(
  filters: TipsterLeaderboardFilters,
): TipsterLeaderboardQuery {
  return {
    isSystem: filters.isSystem ?? undefined,
    leagueIds: filters.leagueIds,
    tier: filters.tier ?? undefined,
    eventIds: filters.eventIds,
    eventFamily: filters.eventFamily ?? undefined,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
    sortBy: filters.sortBy,
    sortOrder: filters.sortOrder,
    page: filters.page,
    pageSize: filters.pageSize,
    applyTax: filters.applyTax || undefined,
  };
}

/** Keeps the current query and toggles apply_tax. Default stays off the URL. */
export function tipsterApplyTaxPath(
  pathname: string,
  searchParams: Record<string, string | undefined>,
  applyTax: boolean,
  resetPage = false,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (value === undefined || key === "apply_tax") {
      continue;
    }
    if (resetPage && key === "page") {
      continue;
    }
    params.set(key, value);
  }
  if (applyTax) {
    params.set("apply_tax", "true");
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

/**
 * Default picker window: one calendar day.
 * Favorite leagues stay the default; empty leagueIds means the whole slate.
 */
export function toTipsterCatalogQuery(
  catalogDate: string,
  favoriteLeagueIds: number[],
  includeAllLeagues = false,
): TipsterCatalogQuery {
  return {
    dateFrom: catalogDate,
    dateTo: catalogDate,
    leagueIds: includeAllLeagues ? [] : favoriteLeagueIds,
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

/** Product of entered leg odds; events inside a combined leg are not multiplied. */
export function previewCouponCombinedOdds(
  legs: DraftCouponLeg[],
): number | null {
  if (legs.length === 0) {
    return null;
  }
  let product = 1;
  for (const leg of legs) {
    const odds = parseLegOdds(leg.odds);
    if (odds === null) {
      return null;
    }
    product *= odds;
  }
  return product;
}

export function previewPotentialWin(
  stakeMoney: number | null,
  combinedOdds: number | null,
  applyTax = false,
): number | null {
  if (stakeMoney === null || combinedOdds === null) {
    return null;
  }
  const netFactor = applyTax ? 1 - TIPSTER_BETTING_TAX_RATE : 1;
  return quantizeTipsterAmount(stakeMoney * combinedOdds * netFactor);
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

export function isCurrencyCode(value: string): value is CurrencyCode {
  return TIPSTER_CURRENCIES.some((code) => code === value);
}

export function isCombinedLeg(eventIds: number[]): boolean {
  return eventIds.length >= 2;
}

/** Same-match events share one odds field; a new match opens a new leg. */
export function addEventToDraftLegs(
  legs: DraftCouponLeg[],
  matchId: number,
  eventId: number,
): { legs: DraftCouponLeg[] } | { error: DraftLegMutationError } {
  const existing = legs.find((leg) => leg.matchId === matchId);
  if (existing) {
    if (existing.eventIds.includes(eventId)) {
      return { error: "duplicate_event" };
    }
    const nextEventIds = [...existing.eventIds, eventId];
    return {
      legs: legs.map((leg) =>
        leg.matchId === matchId
          ? { matchId: leg.matchId, eventIds: nextEventIds, odds: "" }
          : leg,
      ),
    };
  }
  if (legs.length >= MAX_COUPON_LEGS) {
    return { error: "max_legs" };
  }
  return {
    legs: [...legs, { matchId, eventIds: [eventId], odds: "" }],
  };
}

export function removeEventFromDraftLegs(
  legs: DraftCouponLeg[],
  matchId: number,
  eventId: number,
): DraftCouponLeg[] {
  return legs
    .map((leg) => {
      if (leg.matchId !== matchId) {
        return leg;
      }
      const eventIds = leg.eventIds.filter((id) => id !== eventId);
      if (eventIds.length === leg.eventIds.length) {
        return leg;
      }
      return { matchId: leg.matchId, eventIds, odds: "" };
    })
    .filter((leg) => leg.eventIds.length > 0);
}

export function updateDraftLegOdds(
  legs: DraftCouponLeg[],
  matchId: number,
  odds: string,
): DraftCouponLeg[] {
  return legs.map((leg) => {
    if (leg.matchId !== matchId) {
      return leg;
    }
    // własny kurs nie jest już wierszem podpowiedzi
    return { matchId: leg.matchId, eventIds: leg.eventIds, odds };
  });
}

/**
 * Fill an empty single-event leg. Typed odds and combined legs stay as they are
 * so a late suggestion cannot overwrite a price the user already set.
 */
export function applySuggestedLegOdds(
  legs: DraftCouponLeg[],
  matchId: number,
  eventId: number,
  odds: string,
  bookmakerId: number | null,
): DraftCouponLeg[] {
  return legs.map((leg) => {
    if (leg.matchId !== matchId || leg.odds.trim() !== "") {
      return leg;
    }
    if (isCombinedLeg(leg.eventIds) || leg.eventIds[0] !== eventId) {
      return leg;
    }
    if (bookmakerId === null) {
      return { matchId: leg.matchId, eventIds: leg.eventIds, odds };
    }
    return {
      matchId: leg.matchId,
      eventIds: leg.eventIds,
      odds,
      bookmakerId,
    };
  });
}

export function quantizeTipsterAmount(value: number): number {
  return Math.round(value * 100) / 100;
}

export function parsePositiveAmount(raw: string): number | null {
  const value = Number(raw.trim().replace(",", "."));
  if (!Number.isFinite(value)) {
    return null;
  }
  const quantized = quantizeTipsterAmount(value);
  if (quantized <= 0) {
    return null;
  }
  return quantized;
}

export function parseLegOdds(raw: string): number | null {
  const value = Number(raw.trim().replace(",", "."));
  if (!Number.isFinite(value) || value < MIN_LEG_ODDS) {
    return null;
  }
  return value;
}

export function buildCouponCreateRequest(
  legs: DraftCouponLeg[],
  mode: StakeInputMode,
  stakeRaw: string,
): CouponCreateRequest | { error: string } {
  if (legs.length < 1 || legs.length > MAX_COUPON_LEGS) {
    return { error: "Kupon musi mieć od 1 do 8 zdarzeń." };
  }
  const parsedLegs = parseDraftLegs(legs);
  if (!Array.isArray(parsedLegs)) {
    return parsedLegs;
  }
  const stake = parsePositiveAmount(stakeRaw);
  if (stake === null) {
    return {
      error: "Stawka musi być większa od zera po zaokrągleniu do 0.01.",
    };
  }
  return {
    ...couponStakeFields(
      mode,
      mode === "money" ? stake : null,
      mode === "units" ? stake : null,
    ),
    legs: parsedLegs,
  };
}

const STAKE_ADVICE_REASONS = [
  "no_bet_low_edge",
  "no_prediction",
  "model_not_ready",
  "ok",
] as const;

type StakeAdviceReason = (typeof STAKE_ADVICE_REASONS)[number];

const STAKE_ADVICE_REASON_LABELS: Record<StakeAdviceReason, string> = {
  no_bet_low_edge:
    "Werdykt modeli nie wskazuje na przewagę nad kursem " +
    "(wyższy kurs od przewidywanego prawdopodobieństwa). " +
    "Sugerowana stawka to 0.",
  no_prediction:
    "Żadne zdarzenie nie ma opublikowanego modelu. " +
    "Sugestia opiera się tylko i wyłącznie na wprowadzonej pewności i kursie.",
  model_not_ready:
    "UWAGA: Model jest w fazie testów i nie spełnia wszystkich kryteriów. " +
    "Sugestia bazuje na zwykłej predykcji.",
  ok: "Jest dodatnia rada stawki.",
};

const UNKNOWN_STAKE_ADVICE_REASON = "Nieznana odpowiedź systemu.";

export const AKO_STAKE_ASSUMPTION =
  "Kupon AKO: pewność kuponu to iloczyn pewności poszczególnych zdarzeń.";

export const COMBINED_LEG_ASSUMPTION =
  "Zdarzenie łączone: prawdopodobieństwo modelu to iloczyn zdarzeń z meczu.";

export interface StakeAdviceAgentLine {
  key: string;
  label: string;
}

/** Polish copy for the advisor reason code. Unknown codes stay non-blocking. */
export function stakeAdviceReasonLabel(reason: string): string {
  if (isStakeAdviceReason(reason)) {
    return STAKE_ADVICE_REASON_LABELS[reason];
  }
  return UNKNOWN_STAKE_ADVICE_REASON;
}

/**
 * Body for POST /tipsters/me/advise-stake.
 * Legs match coupon create; stake fields stay out of this payload.
 */
export function buildAdviseStakeRequest(
  legs: DraftCouponLeg[],
  confidence: number,
): AdviseStakeRequest | { error: string } {
  if (!Number.isInteger(confidence) || confidence < 0 || confidence > 100) {
    return { error: "Pewność musi być liczbą całkowitą od 0 do 100." };
  }
  if (legs.length < 1 || legs.length > MAX_COUPON_LEGS) {
    return { error: "Kupon musi mieć od 1 do 8 zdarzeń." };
  }
  const parsedLegs = parseDraftLegs(legs);
  if (!Array.isArray(parsedLegs)) {
    return parsedLegs;
  }
  return { confidence, legs: parsedLegs };
}

/** Gate for the debounced POST. A disabled checkbox never builds a body. */
export function stakeAdviceRequestOrNull(
  enabled: boolean,
  legs: DraftCouponLeg[],
  confidence: number,
): AdviseStakeRequest | null {
  // wyłączony checkbox nie może wysłać rady, nawet gdy zdarzenia są kompletne
  if (!enabled) {
    return null;
  }
  const request = buildAdviseStakeRequest(legs, confidence);
  if ("error" in request) {
    return null;
  }
  return request;
}

/** Combined legs and AKO coupons use a product the panel should say out loud. */
export function stakeAdviceAssumptions(legs: DraftCouponLeg[]): string[] {
  const notes: string[] = [];
  if (legs.some((leg) => isCombinedLeg(leg.eventIds))) {
    notes.push(COMBINED_LEG_ASSUMPTION);
  }
  if (legs.length > 1) {
    notes.push(AKO_STAKE_ASSUMPTION);
  }
  return notes;
}

/** Joint blended probability shown as a percent with one decimal. */
export function formatStakeAdviceProbability(pBlend: number): string {
  return `${(pBlend * 100).toFixed(1)}%`;
}

/** Suggested units, two decimals, same width as money. */
export function formatStakeAdviceUnits(units: number): string {
  return units.toFixed(2);
}

/** Money field text after Zastosuj. The coupon save still uses this string. */
export function formatAppliedAdviceStake(stake: number): string {
  return quantizeTipsterAmount(stake).toFixed(2);
}

function isStakeAdviceReason(reason: string): reason is StakeAdviceReason {
  return STAKE_ADVICE_REASONS.some((code) => code === reason);
}

export function catalogEventName(
  events: CatalogEvent[],
  eventId: number,
): string {
  return events.find((event) => event.id === eventId)?.name ?? `#${eventId}`;
}

/** Labels of legs a system account also played. */
export function stakeAdviceAgentLines(
  legs: LegAdvice[],
  matches: CatalogMatch[],
  events: CatalogEvent[],
): StakeAdviceAgentLine[] {
  return legs.filter((leg) => leg.agent_liked).map((leg) => ({
    key: `${leg.match_id}:${leg.event_ids.join(",")}`,
    label: formatStakeAdviceAgentLabel(leg, matches, events),
  }));
}

function formatStakeAdviceAgentLabel(
  leg: LegAdvice,
  matches: CatalogMatch[],
  events: CatalogEvent[],
): string {
  const title = catalogMatchTitle(matches, leg.match_id);
  const names = leg.event_ids
    .map((eventId) => catalogEventName(events, eventId))
    .join(", ");
  return `${title}: ${names}`;
}

/** History labels come from the coupon DTO, never the upcoming picker catalog. */
export function historyMatchLabel(
  leg: Pick<CouponLegSummary, "match_id" | "home_name" | "away_name">,
): string {
  if (leg.home_name && leg.away_name) {
    return `${leg.home_name} – ${leg.away_name}`;
  }
  return `Mecz ${leg.match_id}`;
}

const FINISHED_MATCH_RESULTS = new Set(["1", "X", "2"]);

/** Played match reads as "Home 2 : 1 Away"; an open match keeps the dash. */
export function historyMatchLine(
  leg: Pick<
    CouponLegSummary,
    | "match_id"
    | "home_name"
    | "away_name"
    | "match_result"
    | "home_goals"
    | "away_goals"
  >,
): string {
  const names = historyMatchLabel(leg);
  if (
    !FINISHED_MATCH_RESULTS.has(leg.match_result ?? "") ||
    typeof leg.home_goals !== "number" ||
    typeof leg.away_goals !== "number"
  ) {
    return names;
  }
  const score = `${leg.home_goals} : ${leg.away_goals}`;
  if (leg.home_name && leg.away_name) {
    return `${leg.home_name} ${score} ${leg.away_name}`;
  }
  return `${names} ${score}`;
}

export function couponShapeLabel(legCount: number): string {
  if (legCount <= 1) {
    return "Singiel";
  }
  return `AKO ${legCount}`;
}

export function historyEventLabel(
  leg: Pick<CouponLegSummary, "event_ids" | "event_names">,
): string {
  if (leg.event_names.length > 0) {
    return leg.event_names.join(" + ");
  }
  return leg.event_ids.map((eventId) => `#${eventId}`).join(" + ");
}

export interface CatalogEventGroup {
  label: string;
  events: CatalogEvent[];
}

const CATALOG_EVENT_GROUP_ORDER = [
  "Wynik meczu",
  "BTTS",
  "Handicap",
  "Gole",
  "Rożne",
  "Faule",
  "Kartki",
  "Spalone",
  "Dokładna liczba goli",
  "Dokładny wynik",
  "Inne",
] as const;

export function catalogEventGroupLabel(event: CatalogEvent): string {
  const { id, name } = event;
  if (id >= 1 && id <= 5) {
    return "Wynik meczu";
  }
  if (id === 6 || id === 172) {
    return "BTTS";
  }
  if (id === 8 || id === 12) {
    return "Gole";
  }
  if (id >= 49 && id <= 52) {
    return "Handicap";
  }
  if (id >= 174 && id <= 180) {
    return "Dokładna liczba goli";
  }
  if (id >= 198 && id <= 233) {
    return "Dokładny wynik";
  }
  return catalogEventGroupFromName(name);
}

export function groupCatalogEvents(events: CatalogEvent[]): CatalogEventGroup[] {
  const buckets = new Map<string, CatalogEvent[]>();
  for (const event of events) {
    const label = catalogEventGroupLabel(event);
    const bucket = buckets.get(label);
    if (bucket) {
      bucket.push(event);
    } else {
      buckets.set(label, [event]);
    }
  }
  return CATALOG_EVENT_GROUP_ORDER.filter((label) => buckets.has(label)).map(
    (label) => ({ label, events: buckets.get(label) ?? [] }),
  );
}

function catalogEventGroupFromName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("rożn")) {
    return "Rożne";
  }
  if (lower.includes("faul")) {
    return "Faule";
  }
  if (lower.includes("żółt") || lower.includes("kartk")) {
    return "Kartki";
  }
  if (lower.includes("spalon")) {
    return "Spalone";
  }
  if (lower.includes("gola") || lower.includes("goli") || lower.includes("gol")) {
    return "Gole";
  }
  return "Inne";
}

export function catalogMatchTitle(
  matches: CatalogMatch[],
  matchId: number,
): string {
  const match = matches.find((item) => item.id === matchId);
  if (!match) {
    return `Mecz ${matchId}`;
  }
  return `${match.home_name} – ${match.away_name}`;
}

export interface SlipKickoffParts {
  dayLabel: string;
  timeLabel: string;
}

/**
 * Kick-off split for a slip card. Day is relative in Europe/Warsaw;
 * the clock stays the naive match time from the API.
 */
export function slipKickoffParts(
  gameDate: string | null,
  now: Date = new Date(),
): SlipKickoffParts | null {
  if (!gameDate) {
    return null;
  }
  const normalized = normalizeWarsawNaiveDateTime(gameDate);
  if (!normalized) {
    return null;
  }
  const datePart = normalized.slice(0, 10);
  const timeLabel = normalized.slice(11, 16);
  const today = getWarsawDateIso(now);
  if (datePart === today) {
    return { dayLabel: "Dzisiaj", timeLabel };
  }
  if (datePart === addIsoCalendarDays(today, 1)) {
    return { dayLabel: "Jutro", timeLabel };
  }
  const [, month, day] = datePart.split("-");
  return { dayLabel: `${day}.${month}`, timeLabel };
}

/** Option text without league — the select groups matches by league. */
export function catalogMatchOptionLabel(match: CatalogMatch): string {
  const kickoff = match.game_date
    ? ` (${formatMatchDateTime(match.game_date)})`
    : "";
  return `${match.home_name} – ${match.away_name}${kickoff}`;
}

export function filterCatalogMatches(
  matches: CatalogMatch[],
  query: string,
): CatalogMatch[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return matches;
  }
  return matches.filter((match) =>
    catalogMatchSearchText(match).includes(needle),
  );
}

/**
 * Match id that stays valid for the filtered select.
 * A selection outside the query is dropped so the closed control cannot
 * keep showing a match the search did not find.
 */
export function resolveCatalogMatchId(
  matches: CatalogMatch[],
  query: string,
  selectedId: number,
): number {
  const visible = filterCatalogMatches(matches, query);
  if (visible.some((match) => match.id === selectedId)) {
    return selectedId;
  }
  return visible[0]?.id ?? 0;
}

export function filterCatalogEvents(
  events: CatalogEvent[],
  query: string,
): CatalogEvent[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return events;
  }
  return events.filter((event) => event.name.toLowerCase().includes(needle));
}

/**
 * Event id that stays valid for the filtered select.
 * A selection outside the query is dropped so the closed control cannot
 * keep showing an event the search did not find.
 */
export function resolveCatalogEventId(
  events: CatalogEvent[],
  query: string,
  selectedId: number,
): number {
  const visible = filterCatalogEvents(events, query);
  if (visible.some((event) => event.id === selectedId)) {
    return selectedId;
  }
  return visible[0]?.id ?? 0;
}

export interface CatalogMatchGroup {
  label: string;
  matches: CatalogMatch[];
}

export function groupCatalogMatches(
  matches: CatalogMatch[],
): CatalogMatchGroup[] {
  const groups: CatalogMatchGroup[] = [];
  const index = new Map<string, CatalogMatchGroup>();
  for (const match of matches) {
    const label = match.league_name?.trim() || "Inne";
    const existing = index.get(label);
    if (existing) {
      existing.matches.push(match);
    } else {
      const group = { label, matches: [match] };
      index.set(label, group);
      groups.push(group);
    }
  }
  return groups;
}

export function mergeCatalogMatches(
  current: CatalogMatch[],
  incoming: CatalogMatch[],
): CatalogMatch[] {
  const byId = new Map<number, CatalogMatch>();
  for (const match of current) {
    byId.set(match.id, match);
  }
  for (const match of incoming) {
    byId.set(match.id, match);
  }
  return [...byId.values()];
}

function catalogMatchSearchText(match: CatalogMatch): string {
  return [
    match.home_name,
    match.away_name,
    match.home_shortcut,
    match.away_shortcut,
    match.league_name,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();
}

export function formatEventFamilyName(name: string | null): string {
  if (!name || name === "OTHER") {
    return "Inne";
  }
  return name;
}

export function performanceItemLabel(
  item: PerformanceItem,
  dimension: PerformanceDimension,
): string {
  if (dimension === "family") {
    return formatEventFamilyName(item.event_family_name);
  }
  if (dimension === "league") {
    return item.league_name?.trim() || TIPSTER_EMPTY_VALUE;
  }
  const name = item.country_name?.trim() || TIPSTER_EMPTY_VALUE;
  const emoji = item.country_emoji?.trim();
  return emoji ? `${emoji} ${name}` : name;
}

/** Hit rate of legs in a bucket, independent of the coupon result. */
export function formatPerformanceLegHits(won: number, count: number): string {
  if (count <= 0) {
    return TIPSTER_EMPTY_VALUE;
  }
  return `${won}/${count}`;
}

export function couponOutcomeLabel(
  settled: number,
  outcome: number | null,
): string {
  if (!settled) {
    return "Otwarty";
  }
  return legOutcomeLabel(outcome);
}

export function legOutcomeLabel(outcome: number | null): string {
  if (outcome === null) {
    return "Otwarty";
  }
  return outcome === 1 ? "Wygrany" : "Przegrany";
}

export function couponHistoryStatusLabel(
  settled: number,
  outcome: number | null,
  legs: Array<Pick<CouponLegSummary, "outcome">>,
): string {
  if (!settled && legs.some((leg) => leg.outcome !== null)) {
    return "W rozliczeniu";
  }
  return couponOutcomeLabel(settled, outcome);
}

export function couponStatusPillClassName(
  settled: number,
  outcome: number | null,
  legs: Array<Pick<CouponLegSummary, "outcome">>,
): string {
  const label = couponHistoryStatusLabel(settled, outcome, legs);
  if (label === "Wygrany") {
    return "border-success-border bg-success-bg text-success-text";
  }
  if (label === "Przegrany") {
    return "border-danger-border bg-danger-bg text-danger-text";
  }
  if (label === "W rozliczeniu") {
    return "border-warning-border bg-warning-bg text-warning-text";
  }
  return "border-border bg-surface-muted text-muted";
}

export function legOutcomeDotClassName(outcome: number | null): string {
  if (outcome === 1) {
    return "bg-success";
  }
  if (outcome === 0) {
    return "bg-danger";
  }
  return "bg-border-strong";
}

export function signedAmountClassName(value: number | null): string {
  if (value === null || value === 0) {
    return "text-text";
  }
  return value > 0 ? "text-success" : "text-danger";
}

export function tipsterMutationMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return TIPSTER_API_MESSAGES[error.message] ?? error.message;
  }
  return GENERIC_TIPSTER_SAVE_ERROR;
}

/** Advice failures stay distinct from a failed coupon save. */
export function stakeAdviceErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return TIPSTER_API_MESSAGES[error.message] ?? error.message;
  }
  return STAKE_ADVICE_NETWORK_ERROR;
}

function catalogBookmakerId(leg: DraftCouponLeg): number | null {
  const bookmakerId = leg.bookmakerId;
  if (typeof bookmakerId !== "number" || !Number.isInteger(bookmakerId)) {
    return null;
  }
  if (bookmakerId < 1) {
    return null;
  }
  return bookmakerId;
}

function parseDraftLegs(
  legs: DraftCouponLeg[],
): CouponLegCreate[] | { error: string } {
  const parsed: CouponLegCreate[] = [];
  for (const leg of legs) {
    const odds = parseLegOdds(leg.odds);
    if (odds === null) {
      return { error: "Każde zdarzenie musi mieć kurs co najmniej 1.01." };
    }
    const combined = isCombinedLeg(leg.eventIds);
    parsed.push({
      match_id: leg.matchId,
      event_ids: leg.eventIds,
      odds,
      source: combined ? "custom_odds" : "catalog",
      bookmaker_id: combined ? null : catalogBookmakerId(leg),
    });
  }
  return parsed;
}

export function parseIsSystemFilter(value: string | undefined): 0 | 1 | null {
  if (value === "0") {
    return 0;
  }
  if (value === "1") {
    return 1;
  }
  return null;
}

export function parseEventFamilyFilter(
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

export function parseLeaderboardSortBy(value: string | undefined): LeaderboardSortBy {
  if (value !== undefined && isLeaderboardSortBy(value)) {
    return value;
  }
  return DEFAULT_LEADERBOARD_SORT_BY;
}

function isLeaderboardSortBy(value: string): value is LeaderboardSortBy {
  return LEADERBOARD_SORT_BY_VALUES.some((item) => item === value);
}

export function parseLeaderboardSortOrder(
  value: string | undefined,
): LeaderboardSortOrder {
  if (value === "asc" || value === "desc") {
    return value;
  }
  return DEFAULT_LEADERBOARD_SORT_ORDER;
}
