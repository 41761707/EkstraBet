import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: () => undefined }),
}));

import { BANKROLL_ONBOARDING_TITLE } from "@/components/tipsters/BankrollSetupForm";
import {
  ADD_CATALOG_EVENT_LABEL,
  ALL_LEAGUES_LABEL,
  CATALOG_DATE_LABEL,
  CATALOG_UPCOMING_HINT,
  COUPON_BUILDER_TITLE,
  FAVORITES_UNAVAILABLE_HINT,
  MATCH_SEARCH_LABEL,
} from "@/components/tipsters/CouponBuilder";
import {
  COUPON_HISTORY_EMPTY_MESSAGE,
  COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE,
  COUPON_HISTORY_TITLE,
} from "@/components/tipsters/CouponHistoryTable";
import {
  MY_BETS_DESCRIPTION,
  MY_BETS_TITLE,
  MyBetsContent,
  MyBetsSection,
  PUBLIC_BANKROLL_DESCRIPTION,
  PUBLIC_BANKROLL_TITLE,
  PUBLIC_COUPONS_TITLE,
  SYSTEM_COUPONS_DESCRIPTION,
} from "@/components/tipsters/MyBetsSection";
import { TOP_UP_TITLE } from "@/components/tipsters/TopUpForm";
import type {
  BankrollSettings,
  CatalogMatchesResponse,
  CouponPage,
} from "@/types/api";

const EMPTY_COUPONS: CouponPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
};

const OWNER_BANKROLL: BankrollSettings = {
  user_id: 1,
  currency: "PLN",
  initial_capital: 1000,
  unit_size: 10,
  current_balance: 850,
  open_stake: 20,
  realized_pnl: -150,
};

const CATALOG: CatalogMatchesResponse = {
  matches: [
    {
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
    },
  ],
  events: [
    { id: 1, name: "Gospodarz wygrywa" },
    { id: 6, name: "BTTS tak" },
    { id: 12, name: "Poniżej 2.5 goli" },
  ],
};

describe("MyBetsSection", () => {
  it("shows onboarding without the coupon builder before bankroll exists", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={null}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={null}
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain(MY_BETS_TITLE);
    expect(html).toContain(MY_BETS_DESCRIPTION);
    expect(html).toContain(BANKROLL_ONBOARDING_TITLE);
    expect(html).not.toContain(COUPON_BUILDER_TITLE);
  });

  it("shows the creator and top-up on the own profile after onboarding", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={OWNER_BANKROLL}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={CATALOG}
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain(COUPON_BUILDER_TITLE);
    expect(html).toContain(ADD_CATALOG_EVENT_LABEL);
    expect(html).toContain(MATCH_SEARCH_LABEL);
    expect(html).toContain(CATALOG_DATE_LABEL);
    expect(html).toContain(CATALOG_UPCOMING_HINT);
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain(TOP_UP_TITLE);
    expect(html.indexOf(COUPON_HISTORY_TITLE)).toBeLessThan(
      html.indexOf(TOP_UP_TITLE),
    );
    expect(html).toContain("Wynik meczu");
    expect(html).not.toContain(ALL_LEAGUES_LABEL);
    expect(html).not.toContain("Dodaj nogę");
  });

  it("renders own bets without profile-card chrome", () => {
    const html = renderToStaticMarkup(
      <MyBetsContent
        isOwnProfile
        isSystemProfile={false}
        bankroll={null}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={null}
        profilePath="/moje-zaklady"
        searchParams={{}}
      />,
    );

    expect(html).toContain(BANKROLL_ONBOARDING_TITLE);
    expect(html).not.toContain(MY_BETS_TITLE);
    expect(html).not.toContain(MY_BETS_DESCRIPTION);
  });

  it("offers all-leagues toggle when favorite leagues are set", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={OWNER_BANKROLL}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={CATALOG}
        favoriteLeagueIds={[1]}
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain(ALL_LEAGUES_LABEL);
    expect(html).toContain("Domyślnie ulubione ligi z wybranej daty.");
  });

  it("hides the creator on a public system profile", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile={false}
        isSystemProfile
        bankroll={{ currency: "PLN", current_balance: 1000 }}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={CATALOG}
        profilePath="/profile/agent"
        searchParams={{}}
      />,
    );

    expect(html).toContain(PUBLIC_COUPONS_TITLE);
    expect(html).toContain(SYSTEM_COUPONS_DESCRIPTION);
    expect(html).not.toContain(PUBLIC_BANKROLL_DESCRIPTION);
    expect(html).not.toContain(COUPON_BUILDER_TITLE);
    expect(html).not.toContain(BANKROLL_ONBOARDING_TITLE);
    expect(html).not.toContain(TOP_UP_TITLE);
    expect(html).toContain(COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE);
    expect(html).not.toContain(COUPON_HISTORY_EMPTY_MESSAGE);
  });

  it("hides coupon history on a public human profile when coupons are null", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile={false}
        isSystemProfile={false}
        bankroll={{ currency: "PLN", current_balance: 1000 }}
        coupons={null}
        performance={null}
        catalog={null}
        profilePath="/profile/bob"
        searchParams={{}}
      />,
    );

    expect(html).toContain(PUBLIC_BANKROLL_TITLE);
    expect(html).toContain(PUBLIC_BANKROLL_DESCRIPTION);
    expect(html).not.toContain(PUBLIC_COUPONS_TITLE);
    expect(html).not.toContain(SYSTEM_COUPONS_DESCRIPTION);
    expect(html).not.toContain(COUPON_HISTORY_TITLE);
    expect(html).not.toContain(COUPON_HISTORY_EMPTY_MESSAGE);
    expect(html).not.toContain(COUPON_BUILDER_TITLE);
  });

  it("does not treat a picker catalog error as a public portfolio failure", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile={false}
        isSystemProfile
        bankroll={{ currency: "PLN", current_balance: 1000 }}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={null}
        catalogError="Połączenie odrzucone."
        profilePath="/profile/agent"
        searchParams={{}}
      />,
    );

    expect(html).not.toContain("Nie udało się wczytać katalogu");
    expect(html).not.toContain("Połączenie odrzucone.");
    expect(html).not.toContain(COUPON_BUILDER_TITLE);
  });

  it("keeps coupon history when the bankroll endpoint fails", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={null}
        bankrollError="Serwer kapitału niedostępny."
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={CATALOG}
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain("Nie udało się wczytać kapitału");
    expect(html).toContain(COUPON_HISTORY_TITLE);
    expect(html).toContain(COUPON_HISTORY_EMPTY_MESSAGE);
    expect(html).not.toContain(COUPON_BUILDER_TITLE);
    expect(html).not.toContain(TOP_UP_TITLE);
    expect(html).not.toContain(BANKROLL_ONBOARDING_TITLE);
  });

  it("does not treat unavailable favorites as an empty favorites list", () => {
    const html = renderToStaticMarkup(
      <MyBetsSection
        isOwnProfile
        isSystemProfile={false}
        bankroll={OWNER_BANKROLL}
        coupons={EMPTY_COUPONS}
        performance={null}
        catalog={CATALOG}
        favoriteLeagueIds={[]}
        favoritesUnavailable
        profilePath="/profile/alice"
        searchParams={{}}
      />,
    );

    expect(html).toContain(FAVORITES_UNAVAILABLE_HINT);
    expect(html).not.toContain("Brak ulubionych lig");
    expect(html).not.toContain(ALL_LEAGUES_LABEL);
  });
});
