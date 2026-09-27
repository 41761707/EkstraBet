import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DraftLegsList } from "@/components/tipsters/DraftLegsList";
import type { CatalogEvent, CatalogMatch } from "@/types/api";
import type { DraftCouponLeg } from "@/components/tipsters/tipsterModel";

const MATCH: CatalogMatch = {
  id: 10,
  league_id: 1,
  league_name: "Segunda División",
  league_tier: 2,
  game_date: "2026-09-26T20:45:00",
  result: null,
  home_id: 1,
  home_name: "Tenerife",
  home_shortcut: "TEN",
  away_id: 2,
  away_name: "Cadiz",
  away_shortcut: "CAD",
};

const EVENTS: CatalogEvent[] = [
  { id: 1, name: "Zwycięstwo gospodarza" },
  { id: 8, name: "Powyżej 2.5 gola" },
];

function renderLegs(legs: DraftCouponLeg[]) {
  return renderToStaticMarkup(
    <DraftLegsList
      legs={legs}
      matches={[MATCH]}
      events={EVENTS}
      isSubmitting={false}
      onOddsChange={() => undefined}
      onRemove={() => undefined}
    />,
  );
}

describe("DraftLegsList", () => {
  it("renders an empty slip", () => {
    expect(renderLegs([])).toContain("Na kuponie nie ma jeszcze zdarzeń.");
  });

  it("shows the match, market and editable odds on one card", () => {
    const html = renderLegs([
      { matchId: 10, eventIds: [1], odds: "1.97" },
    ]);

    expect(html).toContain("Tenerife – Cadiz");
    expect(html).toContain("Segunda División");
    expect(html).toContain("20:45");
    expect(html).toContain("Zwycięstwo gospodarza");
    expect(html).toContain("Wynik meczu");
    expect(html).toContain('value="1.97"');
    expect(html).toContain('aria-label="Kurs"');
    expect(html).toContain('aria-label="Usuń Zwycięstwo gospodarza z kuponu"');
    expect(html).not.toContain("Kurs łączony");
  });

  it("keeps one combined price for several events of the same match", () => {
    const html = renderLegs([
      { matchId: 10, eventIds: [1, 8], odds: "2.40" },
    ]);

    expect(html).toContain("Zwycięstwo gospodarza");
    expect(html).toContain("Powyżej 2.5 gola");
    expect(html).toContain("Gole");
    expect(html).toContain("Łączone");
    expect(html).toContain("Kurs łączony");
    expect(html).toContain('aria-label="Kurs łączony"');
    expect(html).toContain('value="2.40"');
    expect(html.match(/aria-label="Kurs"/g)).toBeNull();
    expect(html).toContain('aria-label="Usuń Powyżej 2.5 gola z kuponu"');
  });
});
