import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { PlayersFilters } from "@/components/players/PlayersFilters";
import { FOOTBALL_SPORT_ID } from "@/lib/playerFilterParams";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: () => undefined,
    refresh: () => undefined,
  }),
}));

describe("PlayersFilters", () => {
  it("lists only teams that belong to the selected country", () => {
    const html = renderToStaticMarkup(
      createElement(PlayersFilters, {
        countries: [
          { id: 1, name: "Anglia", emoji: null },
          { id: 2, name: "Niemcy", emoji: null },
        ],
        teams: [
          { id: 10, name: "Arsenal", country_id: 1 },
          { id: 11, name: "Liverpool", country_id: 1 },
          { id: 20, name: "Bayern Monachium", country_id: 2 },
          { id: 21, name: "Borussia Dortmund", country_id: 2 },
        ],
        seasons: [{ season_id: 13, years: "2026/27" }],
        values: {
          sportId: FOOTBALL_SPORT_ID,
          countryId: 2,
          teamId: 20,
          seasonId: 13,
          matchLimit: 50,
          search: "",
        },
      }),
    );

    expect(html).toContain("Bayern Monachium");
    expect(html).toContain("Borussia Dortmund");
    expect(html).not.toContain("Arsenal");
    expect(html).not.toContain("Liverpool");
  });
});
