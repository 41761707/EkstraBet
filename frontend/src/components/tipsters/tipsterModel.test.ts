import { describe, expect, it } from "vitest";

import {
  areTipsterDateFiltersValid,
  couponStakeFields,
  createDefaultTipsterLeaderboardFilters,
  formatCouponCombinedOdds,
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterRoi,
  isCombinedLeg,
  isOwnerBankroll,
  parseTipsterLeaderboardFilters,
  previewStakeMoney,
  tipsterLeaderboardPath,
  toTipsterLeaderboardQuery,
  type TipsterLeaderboardFilters,
} from "@/components/tipsters/tipsterModel";
import type {
  BankrollSettings,
  CouponSummary,
  PublicBankroll,
} from "@/types/api";

function baseFilters(
  overrides: Partial<TipsterLeaderboardFilters> = {},
): TipsterLeaderboardFilters {
  return createDefaultTipsterLeaderboardFilters(overrides);
}

describe("parseTipsterLeaderboardFilters", () => {
  it("defaults to unfiltered profit_total desc paging", () => {
    expect(parseTipsterLeaderboardFilters({})).toEqual(
      createDefaultTipsterLeaderboardFilters(),
    );
  });

  it("parses is_system, league ids, tier and event_family OTHER", () => {
    const filters = parseTipsterLeaderboardFilters({
      is_system: "1",
      league_ids: "48,2",
      tier: "1",
      event_family: "OTHER",
      date_from: "2026-09-01",
      date_to: "2026-09-30",
      sort_by: "roi_pct",
      sort_order: "asc",
      page: "2",
      page_size: "10",
    });
    expect(filters).toEqual({
      isSystem: 1,
      leagueIds: [48, 2],
      tier: 1,
      eventFamily: "OTHER",
      dateFrom: "2026-09-01",
      dateTo: "2026-09-30",
      sortBy: "roi_pct",
      sortOrder: "asc",
      page: 2,
      pageSize: 10,
    });
  });

  it("treats event_family 0 as the unmapped OTHER bucket", () => {
    expect(parseTipsterLeaderboardFilters({ event_family: "0" }).eventFamily).toBe(
      0,
    );
  });

  it("ignores invalid sort, is_system and event_family tokens", () => {
    const filters = parseTipsterLeaderboardFilters({
      is_system: "yes",
      event_family: "corners",
      sort_by: "username",
      sort_order: "sideways",
    });
    expect(filters.isSystem).toBeNull();
    expect(filters.eventFamily).toBeNull();
    expect(filters.sortBy).toBe("profit_total");
    expect(filters.sortOrder).toBe("desc");
  });
});

describe("tipsterLeaderboardPath", () => {
  it("omits default ranking params", () => {
    expect(tipsterLeaderboardPath(baseFilters())).toBe("/typers");
  });

  it("serializes ranking filters including OTHER and is_system 0", () => {
    const path = tipsterLeaderboardPath(
      baseFilters({
        isSystem: 0,
        leagueIds: [48],
        tier: 2,
        eventFamily: "OTHER",
        dateFrom: "2026-09-01",
        dateTo: "2026-09-20",
        sortBy: "avg_odds",
        sortOrder: "asc",
        page: 3,
        pageSize: 50,
      }),
    );
    expect(path).toContain("/typers?");
    expect(path).toContain("is_system=0");
    expect(path).toContain("league_ids=48");
    expect(path).toContain("tier=2");
    expect(path).toContain("event_family=OTHER");
    expect(path).toContain("date_from=2026-09-01");
    expect(path).toContain("date_to=2026-09-20");
    expect(path).toContain("sort_by=avg_odds");
    expect(path).toContain("sort_order=asc");
    expect(path).toContain("page=3");
    expect(path).toContain("page_size=50");
  });

  it("serializes event_family 0 without dropping it as empty", () => {
    const path = tipsterLeaderboardPath(baseFilters({ eventFamily: 0 }));
    expect(path).toContain("event_family=0");
  });
});

describe("toTipsterLeaderboardQuery", () => {
  it("drops null filters so the API omits them", () => {
    expect(toTipsterLeaderboardQuery(baseFilters())).toEqual({
      isSystem: undefined,
      leagueIds: [],
      tier: undefined,
      eventFamily: undefined,
      dateFrom: undefined,
      dateTo: undefined,
      sortBy: "profit_total",
      sortOrder: "desc",
      page: 1,
      pageSize: 20,
    });
  });

  it("keeps is_system 0 and event_family 0 for the API", () => {
    const query = toTipsterLeaderboardQuery(
      baseFilters({ isSystem: 0, eventFamily: 0 }),
    );
    expect(query.isSystem).toBe(0);
    expect(query.eventFamily).toBe(0);
  });
});

describe("areTipsterDateFiltersValid", () => {
  it("allows empty bounds and equal dates", () => {
    expect(areTipsterDateFiltersValid(baseFilters())).toBe(true);
    expect(
      areTipsterDateFiltersValid(
        baseFilters({ dateFrom: "2026-09-01", dateTo: "2026-09-01" }),
      ),
    ).toBe(true);
  });

  it("rejects a reversed date range", () => {
    expect(
      areTipsterDateFiltersValid(
        baseFilters({ dateFrom: "2026-09-20", dateTo: "2026-09-01" }),
      ),
    ).toBe(false);
  });
});

describe("couponStakeFields", () => {
  it("sends money amount and clears units", () => {
    expect(couponStakeFields("money", 25.5, 3)).toEqual({
      stake_input_mode: "money",
      stake_amount: 25.5,
      stake_units: null,
    });
  });

  it("sends units and clears money so the API resolves stake", () => {
    expect(couponStakeFields("units", 25.5, 2)).toEqual({
      stake_input_mode: "units",
      stake_amount: null,
      stake_units: 2,
    });
  });
});

describe("previewStakeMoney", () => {
  it("multiplies units by unit size for display only", () => {
    expect(previewStakeMoney("units", null, 2, 5)).toBe(10);
  });

  it("returns the money amount unchanged in money mode", () => {
    expect(previewStakeMoney("money", 12.5, 2, 5)).toBe(12.5);
  });
});

describe("formatTipsterRoi", () => {
  it("formats positive, negative and missing ROI from the API field", () => {
    expect(formatTipsterRoi(12.34)).toBe("+12.3%");
    expect(formatTipsterRoi(-4)).toBe("-4.0%");
    expect(formatTipsterRoi(null)).toBe("—");
  });
});

describe("formatTipsterAmount and formatTipsterProfit", () => {
  it("formats balance without a forced plus and profit with a sign", () => {
    expect(formatTipsterAmount(50, "PLN")).toBe("50.00 PLN");
    expect(formatTipsterProfit(12.5, "EUR")).toBe("+12.50 EUR");
    expect(formatTipsterProfit(-10, "USD")).toBe("-10.00 USD");
    expect(formatTipsterAmount(null, "PLN")).toBe("—");
  });
});

describe("formatCouponCombinedOdds", () => {
  it("uses the API combined_odds snapshot instead of multiplying legs", () => {
    const coupon: Pick<CouponSummary, "combined_odds"> = {
      combined_odds: 1.9,
    };
    expect(formatCouponCombinedOdds(coupon)).toBe("1.90");
  });
});

describe("isOwnerBankroll", () => {
  it("detects the full owner document vs public currency and balance", () => {
    const owner: BankrollSettings = {
      user_id: 7,
      currency: "PLN",
      initial_capital: 1000,
      unit_size: 10,
      current_balance: 850,
      open_stake: 20,
      realized_pnl: -150,
    };
    const publicRow: PublicBankroll = {
      currency: "PLN",
      current_balance: 850,
    };
    expect(isOwnerBankroll(owner)).toBe(true);
    expect(isOwnerBankroll(publicRow)).toBe(false);
    expect(isOwnerBankroll(null)).toBe(false);
  });
});

describe("isCombinedLeg", () => {
  it("treats two or more event ids as a combined leg", () => {
    expect(isCombinedLeg([6])).toBe(false);
    expect(isCombinedLeg([6, 12])).toBe(true);
  });
});
