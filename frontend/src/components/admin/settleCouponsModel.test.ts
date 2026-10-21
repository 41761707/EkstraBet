import { describe, expect, it } from "vitest";

import {
  formatSettlementSummary,
  mapSettleCouponsError,
} from "@/components/admin/settleCouponsModel";
import { ApiError } from "@/lib/apiShared";

describe("settle coupon copy", () => {
  it("formats the three settlement counters", () => {
    expect(
      formatSettlementSummary({
        coupons_settled: 1,
        legs_settled: 3,
        legs_skipped: 0,
      }),
    ).toBe(
      "Zamknięte kupony: 1. Rozliczone zdarzenia: 3. Pominięte zdarzenia: 0.",
    );
  });

  it("maps auth failures and hides unknown details", () => {
    expect(
      mapSettleCouponsError(new ApiError(403, "Administrator role required")),
    ).toBe("Wymagana rola administratora.");
    expect(mapSettleCouponsError(new ApiError(401, "Not authenticated"))).toBe(
      "Brak sesji. Zaloguj się ponownie.",
    );
    expect(mapSettleCouponsError(new ApiError(500, "boom"))).toBe(
      "Nie udało się rozliczyć kuponów. Spróbuj ponownie.",
    );
    expect(mapSettleCouponsError(new Error("network"))).toBe(
      "Nie udało się rozliczyć kuponów. Spróbuj ponownie.",
    );
  });
});
