import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  FavoriteLeagueButton,
  favoriteLeagueButtonLabel,
} from "@/components/favorites/FavoriteLeagueButton";

describe("favoriteLeagueButtonLabel", () => {
  it("describes add and remove actions with the league name", () => {
    expect(favoriteLeagueButtonLabel("Ekstraklasa", false)).toBe(
      "Dodaj Ekstraklasa do ulubionych",
    );
    expect(favoriteLeagueButtonLabel("Ekstraklasa", true)).toBe(
      "Usuń Ekstraklasa z ulubionych",
    );
  });
});

describe("FavoriteLeagueButton", () => {
  it("exposes aria-pressed and aria-label for an inactive star", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeagueButton
        leagueId={1}
        leagueName="Ekstraklasa"
        isFavorite={false}
        onToggle={() => undefined}
      />,
    );

    expect(html).toContain('aria-pressed="false"');
    expect(html).toContain('aria-label="Dodaj Ekstraklasa do ulubionych"');
    expect(html).not.toContain('disabled=""');
  });

  it("exposes aria-pressed for an active star", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeagueButton
        leagueId={1}
        leagueName="Ekstraklasa"
        isFavorite={true}
        onToggle={() => undefined}
      />,
    );

    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain('aria-label="Usuń Ekstraklasa z ulubionych"');
  });

  it("disables the control while a request is pending", () => {
    const html = renderToStaticMarkup(
      <FavoriteLeagueButton
        leagueId={1}
        leagueName="Ekstraklasa"
        isFavorite={false}
        isPending={true}
        onToggle={() => undefined}
      />,
    );

    expect(html).toContain('disabled=""');
  });
});
