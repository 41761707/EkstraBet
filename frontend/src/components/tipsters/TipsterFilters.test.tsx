import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
}));

import { TipsterFilters } from "@/components/tipsters/TipsterFilters";
import { createDefaultTipsterLeaderboardFilters } from "@/components/tipsters/tipsterModel";

describe("TipsterFilters", () => {
  it("renders ranking filter controls including the OTHER family bucket", () => {
    const html = renderToStaticMarkup(
      <TipsterFilters
        values={createDefaultTipsterLeaderboardFilters()}
        leagues={[{ id: 1, label: "Ekstraklasa" }]}
        eventFamilies={[{ id: 4, label: "BTTS" }]}
      />,
    );

    expect(html).toContain("Konto");
    expect(html).toContain("Konta systemowe");
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("Inne");
    expect(html).toContain("BTTS");
    expect(html).toContain("Liga Mistrzów");
    expect(html).toContain("Zastosuj filtry");
  });
});
