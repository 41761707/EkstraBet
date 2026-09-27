import { toTipsterCatalogQuery } from "@/components/tipsters/tipsterModel";
import {
  ApiError,
  getFavoriteLeagueIds,
  getMyBankroll,
  getMyCoupons,
  getMyPerformance,
  getTipsterCatalog,
} from "@/lib/api";
import { getWarsawDateIso } from "@/lib/date";
import type {
  BankrollSettings,
  CatalogMatchesResponse,
  CouponPage,
  PerformanceBreakdown,
} from "@/types/api";

export interface OwnTipsterBundle {
  bankroll: BankrollSettings | null;
  bankrollError?: string;
  coupons: CouponPage | null;
  couponsError?: string;
  performance: PerformanceBreakdown | null;
  performanceError?: string;
  catalog: CatalogMatchesResponse | null;
  catalogError?: string;
  favoriteLeagueIds: number[];
  favoritesUnavailable: boolean;
}

/** Loads the signed-in user's bankroll, coupons, performance and picker catalog. */
export async function loadOwnTipsterBundle(
  page: number,
  pageSize: number,
  applyTax = false,
): Promise<OwnTipsterBundle> {
  const [bankrollResult, couponsResult, performanceResult, favoritesResult] =
    await Promise.allSettled([
      getMyBankroll({ applyTax }),
      getMyCoupons({ page, pageSize, applyTax }),
      getMyPerformance({ applyTax }),
      getFavoriteLeagueIds(),
    ]);
  const favoriteLeagueIds =
    favoritesResult.status === "fulfilled"
      ? favoritesResult.value.league_ids
      : [];
  const favoritesUnavailable = favoritesResult.status !== "fulfilled";
  const catalogResult = await loadTipsterCatalog(
    favoriteLeagueIds,
    favoritesUnavailable,
  );

  return {
    bankroll: readOptionalBankroll(bankrollResult),
    bankrollError: readBankrollError(bankrollResult),
    coupons: fulfilledOrNull(couponsResult),
    couponsError: rejectedMessage(
      couponsResult,
      "Nie udało się wczytać kuponów.",
    ),
    performance: fulfilledOrNull(performanceResult),
    performanceError: rejectedMessage(
      performanceResult,
      "Nie udało się wczytać analityki.",
    ),
    catalog: fulfilledOrNull(catalogResult),
    catalogError: rejectedMessage(
      catalogResult,
      "Nie udało się wczytać katalogu zdarzeń.",
    ),
    favoriteLeagueIds,
    favoritesUnavailable,
  };
}

async function loadTipsterCatalog(
  favoriteLeagueIds: number[],
  includeAllLeagues = false,
): Promise<PromiseSettledResult<CatalogMatchesResponse>> {
  try {
    const catalog = await getTipsterCatalog(
      toTipsterCatalogQuery(
        getWarsawDateIso(),
        favoriteLeagueIds,
        includeAllLeagues,
      ),
    );
    return { status: "fulfilled", value: catalog };
  } catch (reason) {
    return { status: "rejected", reason };
  }
}

function readOptionalBankroll(
  result: PromiseSettledResult<BankrollSettings>,
): BankrollSettings | null {
  if (result.status === "fulfilled") {
    return result.value;
  }
  return null;
}

function readBankrollError(
  result: PromiseSettledResult<BankrollSettings>,
): string | undefined {
  if (result.status === "fulfilled") {
    return undefined;
  }
  if (result.reason instanceof ApiError && result.reason.status === 404) {
    return undefined;
  }
  return resolveLoadErrorMessage(
    result.reason,
    "Nie udało się wczytać kapitału.",
  );
}

function fulfilledOrNull<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function rejectedMessage(
  result: PromiseSettledResult<unknown>,
  fallback: string,
): string | undefined {
  if (result.status === "fulfilled") {
    return undefined;
  }
  return resolveLoadErrorMessage(result.reason, fallback);
}

function resolveLoadErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}
