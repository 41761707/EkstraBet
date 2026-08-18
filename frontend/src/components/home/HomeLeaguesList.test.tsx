import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HomeLeaguesList } from "@/components/home/HomeLeaguesList";
import { FAVORITES_UNAVAILABLE_TITLE } from "@/lib/favoriteLeagues";
import type { LeagueSummary } from "@/types/api";

function sampleLeague(
  overrides: Partial<LeagueSummary> = {},
): LeagueSummary {
  return {
    id: 1,
    name: "Ekstraklasa",
    country_id: 1,
    country_name: "Poland",
    country_emoji: "🇵🇱",
    sport_id: 1,
    sport_name: "Football",
    active: true,
    last_update: null,
    slug: "ekstraklasa",
    ...overrides,
  };
}

describe("HomeLeaguesList", () => {
  it("renders league links without stars when favorites are disabled", () => {
    const html = renderToStaticMarkup(
      <HomeLeaguesList
        leagues={[
          sampleLeague(),
          sampleLeague({
            id: 2,
            name: "Premier League",
            slug: "premier-league",
          }),
        ]}
      />,
    );

    expect(html).toContain("href=\"/leagues/ekstraklasa\"");
    expect(html).toContain("href=\"/leagues/premier-league\"");
    expect(html).not.toContain("aria-pressed");
    expect(html).not.toContain("Dodaj Ekstraklasa do ulubionych");
  });

  it("renders a star next to each league link when favorites are enabled", () => {
    const html = renderToStaticMarkup(
      <HomeLeaguesList
        leagues={[sampleLeague()]}
        initialFavoriteIds={[1]}
        favoritesEnabled={true}
      />,
    );

    expect(html).toContain("href=\"/leagues/ekstraklasa\"");
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("Usuń Ekstraklasa z ulubionych");
    expect(html).toContain('aria-live="polite"');
  });

  it("lifts favorite leagues to the front of the markup", () => {
    const html = renderToStaticMarkup(
      <HomeLeaguesList
        leagues={[
          sampleLeague(),
          sampleLeague({
            id: 2,
            name: "Premier League",
            slug: "premier-league",
          }),
        ]}
        initialFavoriteIds={[2]}
        favoritesEnabled={true}
      />,
    );

    const premierIndex = html.indexOf("Premier League");
    const ekstraklasaIndex = html.indexOf("Ekstraklasa");
    expect(premierIndex).toBeGreaterThan(-1);
    expect(ekstraklasaIndex).toBeGreaterThan(premierIndex);
  });

  it("keeps catalog links and hides stars when favorites are unavailable", () => {
    const html = renderToStaticMarkup(
      <HomeLeaguesList
        leagues={[sampleLeague()]}
        favoritesEnabled={true}
        favoritesUnavailable={true}
      />,
    );

    expect(html).toContain(FAVORITES_UNAVAILABLE_TITLE);
    expect(html).toContain("href=\"/leagues/ekstraklasa\"");
    expect(html).toContain("Ekstraklasa");
    expect(html).not.toContain("aria-pressed");
  });

  it("renders an empty state when the catalog has no leagues", () => {
    const html = renderToStaticMarkup(<HomeLeaguesList leagues={[]} />);

    expect(html).toContain("Brak aktywnych lig");
    expect(html).not.toContain("aria-pressed");
  });
});
