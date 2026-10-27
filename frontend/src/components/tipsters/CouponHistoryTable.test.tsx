import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  CouponHistoryTable,
  COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE,
} from "@/components/tipsters/CouponHistoryTable";
import type { CouponPage, CouponSummary } from "@/types/api";

function sampleCoupon(overrides: Partial<CouponSummary> = {}): CouponSummary {
  return {
    id: 7,
    user_id: 1,
    stake_amount: 10,
    stake_units: null,
    stake_input_mode: "money",
    combined_odds: 3.06,
    settled: 0,
    outcome: null,
    profit: -10,
    created_at: "2026-09-01T12:00:00Z",
    legs: [
      {
        id: 71,
        match_id: 12345,
        home_name: "Legia",
        away_name: "Lech",
        event_ids: [6, 12],
        event_names: ["BTTS tak", "Poniżej 2.5 goli"],
        odds: 1.55,
        bookmaker_id: null,
        source: "custom_odds",
        outcome: 0,
        home_goals: 2,
        away_goals: 1,
        match_result: "1",
      },
      {
        id: 72,
        match_id: 99,
        home_name: "Wisła",
        away_name: "Śląsk",
        event_ids: [1],
        event_names: ["Gospodarz wygrywa"],
        odds: 1.97,
        home_goals: 0,
        away_goals: 0,
        match_result: "0",
        bookmaker_id: null,
        source: "catalog",
        outcome: null,
      },
    ],
    ...overrides,
  };
}

function samplePage(overrides: Partial<CouponPage> = {}): CouponPage {
  return {
    items: [sampleCoupon()],
    total: 21,
    page: 1,
    page_size: 20,
    ...overrides,
  };
}

describe("CouponHistoryTable", () => {
  it("renders match and event names from the coupon DTO", () => {
    const html = renderToStaticMarkup(
      <CouponHistoryTable
        coupons={samplePage()}
        currency="PLN"
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain("AKO 2");
    expect(html).toContain("Legia 2 : 1 Lech");
    expect(html).toContain("Wisła – Śląsk");
    expect(html).toContain('href="/matches/12345"');
    expect(html).toContain("BTTS tak + Poniżej 2.5 goli");
    expect(html).toContain("1.55");
    expect(html).toContain("Przegrany");
    expect(html).toContain("1.97");
    expect(html).toContain("W rozliczeniu");
    expect(html).toContain("bg-warning-bg");
    expect(html).toContain("bg-danger");
    expect(html).toContain("3.06");
    expect(html).not.toContain("Mecz 12345");
    expect(html).not.toContain("<table");
  });

  it("paginates from coupons.total and page_size", () => {
    const html = renderToStaticMarkup(
      <CouponHistoryTable
        coupons={samplePage()}
        currency="PLN"
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain("Strona 1 z 2 (21 wyników)");
  });

  it("uses public copy for an empty system profile history", () => {
    const html = renderToStaticMarkup(
      <CouponHistoryTable
        coupons={samplePage({ items: [], total: 0 })}
        currency="PLN"
        profilePath="/profile/agent"
        searchParams={{}}
        isOwnProfile={false}
        isSystemProfile
      />,
    );

    expect(html).toContain(COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE);
    expect(html).not.toContain("po dodaniu pierwszego kuponu");
  });
});
