import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AddLeagueForm, ADD_LEAGUE_FORM_TITLE } from "@/components/admin/AddLeagueForm";
import type { AdminCountry, AdminSeason, AdminSport } from "@/types/api";

const COUNTRIES: AdminCountry[] = [
  { id: 1, name: "Polska", short_name: "POL", emoji: "🇵🇱" },
];
const SPORTS: AdminSport[] = [{ id: 1, name: "Piłka nożna" }];
const SEASONS: AdminSeason[] = [{ id: 13, years: "2026/27" }];

describe("AddLeagueForm", () => {
  it("renders name, country, sport, season, tier and player-stats fields", () => {
    const html = renderToStaticMarkup(
      <AddLeagueForm
        isSubmitting={false}
        countries={COUNTRIES}
        sports={SPORTS}
        seasons={SEASONS}
        onSubmit={async () => undefined}
      />,
    );

    expect(html).toContain(ADD_LEAGUE_FORM_TITLE);
    expect(html).toContain('name="name"');
    expect(html).toContain('name="country_id"');
    expect(html).toContain('name="sport_id"');
    expect(html).toContain('name="current_season_id"');
    expect(html).toContain('name="tier"');
    expect(html).toContain('name="has_player_stats"');
    expect(html).toContain("Polska");
    expect(html).toContain("Piłka nożna");
    expect(html).toContain("2026/27");
    expect(html).toContain("Utwórz ligę");
  });

  it("shows a creating label while the request is in flight", () => {
    const html = renderToStaticMarkup(
      <AddLeagueForm
        isSubmitting={true}
        countries={COUNTRIES}
        sports={SPORTS}
        seasons={SEASONS}
        onSubmit={async () => undefined}
      />,
    );

    expect(html).toContain("Tworzenie…");
    expect(html).toContain("disabled");
  });

  it("hides dropdowns and disables submit when dictionaries fail to load", () => {
    const html = renderToStaticMarkup(
      <AddLeagueForm
        isSubmitting={false}
        countries={[]}
        sports={[]}
        seasons={[]}
        dictionariesError="Połączenie odrzucone."
        onSubmit={async () => undefined}
      />,
    );

    expect(html).toContain("Nie udało się wczytać list krajów lub sportów");
    expect(html).toContain("Połączenie odrzucone.");
    expect(html).not.toContain('name="country_id"');
    expect(html).toContain("disabled");
  });

  it("warns about seasons without blocking the rest of the form", () => {
    const html = renderToStaticMarkup(
      <AddLeagueForm
        isSubmitting={false}
        countries={COUNTRIES}
        sports={SPORTS}
        seasons={[]}
        seasonsError="Błąd sezonów"
        onSubmit={async () => undefined}
      />,
    );

    expect(html).toContain("Nie udało się wczytać listy sezonów");
    expect(html).toContain("Błąd sezonów");
    expect(html).toContain('name="country_id"');
    expect(html).toContain('name="current_season_id"');
    expect(html).toContain("Utwórz ligę");
    expect(html).not.toContain("Nie udało się wczytać list krajów lub sportów");
  });
});
