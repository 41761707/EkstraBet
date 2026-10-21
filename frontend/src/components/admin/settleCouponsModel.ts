import { ApiError } from "@/lib/apiShared";
import type { SettlementResult } from "@/types/api";

export const SETTLE_COUPONS_TITLE = "Rozliczanie kuponów";
export const SETTLE_COUPONS_DESCRIPTION =
  "Zamyka otwarte kupony, których mecze mają już wynik i bramki. "
export const SETTLE_COUPONS_BUTTON = "Rozlicz zakłady";
export const SETTLE_COUPONS_BUSY = "Rozliczanie…";
export const SETTLE_COUPONS_ERROR_TITLE = "Nie udało się rozliczyć kuponów";

const GENERIC_SETTLE_ERROR =
  "Nie udało się rozliczyć kuponów. Spróbuj ponownie.";

const SETTLE_API_ERRORS: Record<string, string> = {
  "Administrator role required": "Wymagana rola administratora.",
  "Not authenticated": "Brak sesji. Zaloguj się ponownie.",
};

/** Polish summary of one settlement cycle. */
export function formatSettlementSummary(result: SettlementResult): string {
  return (
    `Zamknięte kupony: ${result.coupons_settled}. ` +
    `Rozliczone zdarzenia: ${result.legs_settled}. ` +
    `Pominięte zdarzenia: ${result.legs_skipped}.`
  );
}

/** Map a settlement failure to a Polish message. */
export function mapSettleCouponsError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return GENERIC_SETTLE_ERROR;
  }
  return SETTLE_API_ERRORS[error.message] ?? GENERIC_SETTLE_ERROR;
}
