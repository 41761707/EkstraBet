import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  EMPTY_FAVORITE_LEAGUES_TITLE,
  FAVORITE_LEAGUES_DESCRIPTION,
  FAVORITE_LEAGUES_LOAD_ERROR_TITLE,
  FAVORITE_LEAGUES_TITLE,
  FAVORITE_TOGGLE_ERROR_MESSAGE,
  FAVORITES_UNAVAILABLE_TITLE,
  FavoriteLeaguesSection,
} from "@/components/profile/FavoriteLeaguesSection";
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

describe("FavoriteLeaguesSection", () => {
  it("renders the section title and a grid of active leagues with stars", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeaguesSection
        leagues={[
          sampleLeague(),
          sampleLeague({
            id: 2,
            name: "Premier League",
            slug: "premier-league",
            country_emoji: "🇬🇧",
          }),
        ]}
        initialFavoriteIds={[2]}
      />,
    );

    expect(html).toContain(FAVORITE_LEAGUES_TITLE);
    expect(html).toContain(FAVORITE_LEAGUES_DESCRIPTION);
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("Premier League");
    expect(html).toContain('aria-pressed="false"');
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain('aria-live="polite"');
  });

  it("renders an empty state when the catalog has no leagues", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeaguesSection leagues={[]} initialFavoriteIds={[]} />,
    );

    expect(html).toContain(EMPTY_FAVORITE_LEAGUES_TITLE);
    expect(html).not.toContain("aria-pressed");
  });

  it("renders a load error instead of the grid", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeaguesSection
        leagues={[sampleLeague()]}
        initialFavoriteIds={[]}
        leaguesError="Połączenie odrzucone."
      />,
    );

    expect(html).toContain(FAVORITE_LEAGUES_LOAD_ERROR_TITLE);
    expect(html).toContain("Połączenie odrzucone.");
    expect(html).not.toContain("Ekstraklasa");
  });

  it("keeps the catalog visible without favorite stars when favorites are unavailable", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeaguesSection
        leagues={[sampleLeague()]}
        initialFavoriteIds={[]}
        favoritesUnavailable={true}
      />,
    );

    expect(html).toContain(FAVORITES_UNAVAILABLE_TITLE);
    expect(html).toContain("Ekstraklasa");
    expect(html).not.toContain("aria-pressed");
    expect(html).not.toContain("Dodaj Ekstraklasa do ulubionych");
  });

  it("exposes the toggle error copy for rollback announcements", () => {
    expect(FAVORITE_TOGGLE_ERROR_MESSAGE).toContain("Nie udało się zapisać");
  });
});
