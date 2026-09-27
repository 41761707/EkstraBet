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
      },
      {
        id: 72,
        match_id: 99,
        home_name: "Wisła",
        away_name: "Śląsk",
        event_ids: [1],
        event_names: ["Gospodarz wygrywa"],
        odds: 1.97,
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

    expect(html).toContain("Legia – Lech");
    expect(html).toContain('href="/matches/12345"');
    expect(html).toContain("BTTS tak + Poniżej 2.5 goli");
    expect(html).toContain("1.55");
    expect(html).toContain("Przegrany");
    expect(html).toContain("1.97");
    expect(html).toContain("W rozliczeniu");
    expect(html).toContain("text-warning");
    expect(html).toContain("text-danger");
    expect(html).not.toContain("Mecz 12345");
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
