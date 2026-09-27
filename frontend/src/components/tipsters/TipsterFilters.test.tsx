import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
}));

import { TipsterFilters } from "@/components/tipsters/TipsterFilters";
import { createDefaultTipsterLeaderboardFilters } from "@/components/tipsters/tipsterModel";

describe("TipsterFilters", () => {
  it("renders ranking events like the bookmaker event list", () => {
    const html = renderToStaticMarkup(
      <TipsterFilters
        values={createDefaultTipsterLeaderboardFilters()}
        leagues={[{ id: 1, label: "Ekstraklasa" }]}
        events={[
          {
            id: 12,
            label: "Poniżej 2.5 gola",
            familyName: "OU",
          },
          {
            id: 6,
            label: "Obie drużyny strzelą",
            familyName: "BTTS",
          },
          {
            id: 198,
            label: "1:0",
            familyName: "EXACT",
          },
        ]}
      />,
    );

    expect(html).toContain("Konto");
    expect(html).toContain("Konta systemowe");
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("Zdarzenia");
    expect(html).toContain("Najpopularniejsze");
    expect(html).toContain("Poniżej 2.5 gola");
    expect(html).toContain("Obie drużyny strzelą");
    expect(html).toContain("Pozostałe");
    expect(html).toContain("1:0");
    expect(html).not.toContain("Rodzina zdarzeń");
    expect(html).toContain("Liga Mistrzów");
    expect(html).toContain("Zastosuj filtry");
  });
});
