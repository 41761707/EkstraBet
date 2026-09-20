import { describe, expect, it } from "vitest";

import {
  addEventToDraftLegs,
  areTipsterDateFiltersValid,
  buildCouponCreateRequest,
  couponStakeFields,
  createDefaultTipsterLeaderboardFilters,
  filterCatalogEvents,
  filterCatalogMatches,
  formatCouponCombinedOdds,
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterRoi,
  groupCatalogEvents,
  groupCatalogMatches,
  historyEventLabel,
  historyMatchLabel,
  isCombinedLeg,
  isMissingTipsterProfileError,
  isOwnerBankroll,
  isPublicCouponHistoryVisible,
  couponHistoryStatusLabel,
  legOutcomeLabel,
  mergeCatalogMatches,
  parseEventFamilyFilter,
  parseIsSystemFilter,
  parseLeaderboardSortBy,
  parseLeaderboardSortOrder,
  parsePositiveAmount,
  parseTipsterLeaderboardFilters,
  previewCouponCombinedOdds,
  previewPotentialWin,
  previewStakeMoney,
  removeEventFromDraftLegs,
  tipsterFilterCatalogMessage,
  tipsterLeaderboardPath,
  tipsterMutationMessage,
  toTipsterCatalogQuery,
  toTipsterLeaderboardQuery,
  updateDraftLegOdds,
  type DraftCouponLeg,
  type TipsterLeaderboardFilters,
} from "@/components/tipsters/tipsterModel";
import { ApiError } from "@/lib/apiShared";
import type {
  BankrollSettings,
  CatalogMatch,
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

describe("leaderboard filter parsers", () => {
  it("maps ranking select values the same way as the URL query", () => {
    expect(parseIsSystemFilter("")).toBeNull();
    expect(parseIsSystemFilter("0")).toBe(0);
    expect(parseIsSystemFilter("1")).toBe(1);
    expect(parseEventFamilyFilter("")).toBeNull();
    expect(parseEventFamilyFilter("OTHER")).toBe("OTHER");
    expect(parseEventFamilyFilter("4")).toBe(4);
    expect(parseLeaderboardSortBy("avg_profit")).toBe("avg_profit");
    expect(parseLeaderboardSortBy("username")).toBe("profit_total");
    expect(parseLeaderboardSortOrder("asc")).toBe("asc");
    expect(parseLeaderboardSortOrder("sideways")).toBe("desc");
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

describe("public profile visibility", () => {
  it("404s only when the profile API says the user is missing", () => {
    expect(
      isMissingTipsterProfileError(new ApiError(404, "User not found")),
    ).toBe(true);
    expect(isMissingTipsterProfileError(new ApiError(500, "boom"))).toBe(false);
    expect(isMissingTipsterProfileError(new Error("User not found"))).toBe(
      false,
    );
  });

  it("keeps coupon history owner-or-system only", () => {
    expect(isPublicCouponHistoryVisible(true, false)).toBe(true);
    expect(isPublicCouponHistoryVisible(false, true)).toBe(true);
    expect(isPublicCouponHistoryVisible(false, false)).toBe(false);
  });
});

describe("tipsterFilterCatalogMessage", () => {
  it("stays silent when both catalogs loaded", () => {
    expect(tipsterFilterCatalogMessage(false, false)).toBeNull();
  });

  it("warns without blocking when a catalog reject empties the options", () => {
    expect(tipsterFilterCatalogMessage(true, false)).toContain("lig");
    expect(tipsterFilterCatalogMessage(false, true)).toContain("rodzin");
    expect(tipsterFilterCatalogMessage(true, true)).toContain("lig i rodzin");
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

describe("addEventToDraftLegs", () => {
  it("groups a second event of the same match into one odds field", () => {
    const first = addEventToDraftLegs([], 10, 6);
    expect("legs" in first).toBe(true);
    if (!("legs" in first)) {
      return;
    }
    const combined = addEventToDraftLegs(first.legs, 10, 12);
    expect(combined).toEqual({
      legs: [{ matchId: 10, eventIds: [6, 12], odds: "" }],
    });
  });

  it("opens a new leg for a different match", () => {
    const first = addEventToDraftLegs([], 10, 6);
    if (!("legs" in first)) {
      return;
    }
    const ako = addEventToDraftLegs(first.legs, 11, 6);
    expect("legs" in ako && ako.legs).toHaveLength(2);
  });

  it("clears single-leg odds when the same match becomes combined", () => {
    const first = addEventToDraftLegs([], 10, 6);
    expect("legs" in first).toBe(true);
    if (!("legs" in first)) {
      return;
    }
    const withOdds = updateDraftLegOdds(first.legs, 10, "1.80");
    const combined = addEventToDraftLegs(withOdds, 10, 12);
    expect(combined).toEqual({
      legs: [{ matchId: 10, eventIds: [6, 12], odds: "" }],
    });
  });

  it("clears odds whenever the combined selection changes", () => {
    const first = addEventToDraftLegs([], 10, 6);
    if (!("legs" in first)) {
      return;
    }
    const withOdds = updateDraftLegOdds(first.legs, 10, "1.80");
    const combined = addEventToDraftLegs(withOdds, 10, 12);
    if (!("legs" in combined)) {
      return;
    }
    const priced = updateDraftLegOdds(combined.legs, 10, "1.55");
    const third = addEventToDraftLegs(priced, 10, 8);
    expect(third).toEqual({
      legs: [{ matchId: 10, eventIds: [6, 12, 8], odds: "" }],
    });
    if (!("legs" in third)) {
      return;
    }
    const repriced = updateDraftLegOdds(third.legs, 10, "1.40");
    expect(removeEventFromDraftLegs(repriced, 10, 8)).toEqual([
      { matchId: 10, eventIds: [6, 12], odds: "" },
    ]);
  });

  it("rejects a duplicate event on the same combined leg", () => {
    const first = addEventToDraftLegs([], 10, 6);
    if (!("legs" in first)) {
      return;
    }
    expect(addEventToDraftLegs(first.legs, 10, 6)).toEqual({
      error: "duplicate_event",
    });
  });

  it("rejects a ninth distinct match", () => {
    let legs: DraftCouponLeg[] = [];
    for (let matchId = 1; matchId <= 8; matchId += 1) {
      const result = addEventToDraftLegs(legs, matchId, 6);
      expect("legs" in result).toBe(true);
      if ("legs" in result) {
        legs = result.legs;
      }
    }
    expect(addEventToDraftLegs(legs, 9, 6)).toEqual({ error: "max_legs" });
  });
});

describe("parsePositiveAmount and buildCouponCreateRequest", () => {
  it("rejects money that quantizes to 0.00", () => {
    expect(parsePositiveAmount("0.001")).toBeNull();
    expect(parsePositiveAmount("10,5")).toBe(10.5);
  });

  it("sends custom_odds for combined and catalog for a single event", () => {
    const request = buildCouponCreateRequest(
      [
        { matchId: 10, eventIds: [6, 12], odds: "1.85" },
        { matchId: 11, eventIds: [1], odds: "2.00" },
      ],
      "units",
      "2",
    );
    expect("legs" in request).toBe(true);
    if (!("legs" in request)) {
      return;
    }
    expect(request.stake_input_mode).toBe("units");
    expect(request.stake_units).toBe(2);
    expect(request.legs[0]).toMatchObject({
      match_id: 10,
      event_ids: [6, 12],
      odds: 1.85,
      source: "custom_odds",
      bookmaker_id: null,
    });
    expect(request.legs[1]?.source).toBe("catalog");
  });
});

describe("historyMatchLabel and groupCatalogEvents", () => {
  it("uses home and away names from the coupon DTO", () => {
    expect(
      historyMatchLabel({
        match_id: 12345,
        home_name: "Legia",
        away_name: "Lech",
      }),
    ).toBe("Legia – Lech");
    expect(
      historyMatchLabel({
        match_id: 99,
        home_name: null,
        away_name: null,
      }),
    ).toBe("Mecz 99");
    expect(
      historyEventLabel({
        event_ids: [6, 12],
        event_names: ["BTTS tak", "Poniżej 2.5 goli"],
      }),
    ).toBe("BTTS tak + Poniżej 2.5 goli");
  });

  it("groups settleable events by market family", () => {
    const groups = groupCatalogEvents([
      { id: 1, name: "Gospodarz wygrywa" },
      { id: 6, name: "Obie drużyny strzelą tak" },
      { id: 12, name: "Poniżej 2.5 goli" },
      { id: 50, name: "Handicap gospodarza -1.5" },
      { id: 210, name: "Dokładny wynik 1:0" },
      { id: 40, name: "Gospodarz powyżej 8.5 rożnych" },
    ]);
    expect(groups.map((group) => group.label)).toEqual([
      "Wynik meczu",
      "BTTS",
      "Handicap",
      "Gole",
      "Rożne",
      "Dokładny wynik",
    ]);
  });

  it("treats a settled losing leg as lost while the coupon can stay open", () => {
    expect(legOutcomeLabel(0)).toBe("Przegrany");
    expect(legOutcomeLabel(null)).toBe("Otwarty");
    expect(
      couponHistoryStatusLabel(0, null, [{ outcome: 0 }, { outcome: null }]),
    ).toBe("W rozliczeniu");
    expect(couponHistoryStatusLabel(0, null, [{ outcome: null }])).toBe(
      "Otwarty",
    );
  });
});

describe("catalog match picker helpers", () => {
  const legia: CatalogMatch = {
    id: 10,
    league_id: 1,
    league_name: "Ekstraklasa",
    league_tier: 1,
    game_date: "2026-09-21T18:00:00Z",
    result: null,
    home_id: 1,
    home_name: "Legia",
    home_shortcut: "LEG",
    away_id: 2,
    away_name: "Lech",
    away_shortcut: "LPO",
  };
  const arsenal: CatalogMatch = {
    id: 11,
    league_id: 2,
    league_name: "Premier League",
    league_tier: 1,
    game_date: "2026-09-21T16:00:00Z",
    result: null,
    home_id: 3,
    home_name: "Arsenal",
    home_shortcut: "ARS",
    away_id: 4,
    away_name: "Chelsea",
    away_shortcut: "CHE",
  };

  it("filters by team or league text and groups by league", () => {
    expect(filterCatalogMatches([legia, arsenal], "legia")).toEqual([legia]);
    expect(filterCatalogMatches([legia, arsenal], "premier")).toEqual([arsenal]);
    expect(
      groupCatalogMatches([legia, arsenal]).map((group) => group.label),
    ).toEqual(["Ekstraklasa", "Premier League"]);
  });

  it("filters settleable events by name", () => {
    const events = [
      { id: 1, name: "Gospodarz wygrywa" },
      { id: 6, name: "BTTS tak" },
      { id: 198, name: "Dokładny wynik 1-0" },
    ];
    expect(filterCatalogEvents(events, "btts")).toEqual([events[1]]);
    expect(filterCatalogEvents(events, "1-0")).toEqual([events[2]]);
  });

  it("keeps previously selected matches when the day changes", () => {
    expect(mergeCatalogMatches([legia], [arsenal])).toEqual([legia, arsenal]);
  });

  it("sends one calendar day and favorite league ids to the catalog", () => {
    expect(toTipsterCatalogQuery("2026-09-20", [48, 2])).toEqual({
      dateFrom: "2026-09-20",
      dateTo: "2026-09-20",
      leagueIds: [48, 2],
    });
  });

  it("omits league ids when the picker includes all leagues", () => {
    expect(toTipsterCatalogQuery("2026-09-20", [48, 2], true)).toEqual({
      dateFrom: "2026-09-20",
      dateTo: "2026-09-20",
      leagueIds: [],
    });
  });
});

describe("previewCouponCombinedOdds", () => {
  it("multiplies leg odds and ignores events inside a combined leg", () => {
    expect(
      previewCouponCombinedOdds([
        { matchId: 10, eventIds: [6, 12], odds: "1.55" },
        { matchId: 11, eventIds: [1], odds: "2.00" },
      ]),
    ).toBeCloseTo(3.1);
    expect(
      previewCouponCombinedOdds([
        { matchId: 10, eventIds: [6], odds: "" },
      ]),
    ).toBeNull();
    expect(previewPotentialWin(10, 3.1)).toBe(31);
  });
});

describe("tipsterMutationMessage", () => {
  it("translates known service errors", () => {
    expect(
      tipsterMutationMessage(new ApiError(403, "User account is inactive")),
    ).toBe("Konto użytkownika jest nieaktywne.");
    expect(
      tipsterMutationMessage(new ApiError(422, "Invalid coupon leg")),
    ).toBe("Noga kuponu jest nieprawidłowa.");
    expect(
      tipsterMutationMessage(new ApiError(422, "Unsupported currency")),
    ).toBe("Nieobsługiwana waluta.");
    expect(
      tipsterMutationMessage(
        new ApiError(422, "Each leg must have at least one event"),
      ),
    ).toBe("Każda noga musi mieć co najmniej jeden event.");
  });

  it("falls back to the API message for unmapped errors", () => {
    expect(
      tipsterMutationMessage(new ApiError(422, "Unexpected coupon rule")),
    ).toBe("Unexpected coupon rule");
  });

  it("uses the generic copy for non-API failures", () => {
    expect(tipsterMutationMessage(new Error("network down"))).toBe(
      "Nie udało się zapisać. Spróbuj ponownie.",
    );
  });
});
