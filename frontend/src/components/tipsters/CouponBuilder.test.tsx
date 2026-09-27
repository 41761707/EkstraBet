import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: () => undefined }),
}));

import {
  CATALOG_UPCOMING_HINT,
  EVENT_SEARCH_LABEL,
  CouponBuilder,
} from "@/components/tipsters/CouponBuilder";
import { getWarsawDateIso } from "@/lib/date";
import type { CatalogMatchesResponse } from "@/types/api";

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
  ],
};

describe("CouponBuilder", () => {
  it("keeps the picker outside the stake form and saves only via button", () => {
    const html = renderToStaticMarkup(
      <CouponBuilder
        catalog={CATALOG}
        favoriteLeagueIds={[1]}
        draftStorageKey="/profile/alice"
        unitSize={10}
        currency="PLN"
      />,
    );

    const searchAt = html.indexOf('type="search"');
    const dateAt = html.indexOf('type="date"');
    const formAt = html.indexOf("<form");
    expect(searchAt).toBeGreaterThan(-1);
    expect(dateAt).toBeGreaterThan(-1);
    expect(formAt).toBeGreaterThan(searchAt);
    expect(formAt).toBeGreaterThan(dateAt);
    expect(html).toContain('type="button"');
    expect(html).not.toContain('type="submit"');
    expect(html).toContain(`min="${getWarsawDateIso()}"`);
    expect(html).toContain(CATALOG_UPCOMING_HINT);
    expect(html).toContain(EVENT_SEARCH_LABEL);
  });
});
