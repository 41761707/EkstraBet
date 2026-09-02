import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AppNav } from "@/components/AppNav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("AppNav overflow", () => {
  it("keeps core links in the desktop bar and hides extras behind Więcej", () => {
    const html = renderToStaticMarkup(
      <AppNav showLogout={false} showLinks={true} showProfile={false} />,
    );

    expect(html).toContain("Typer LM");
    expect(html).toContain("Kącik statystyczny");
    expect(html).toContain("Więcej");
    expect(html).not.toContain("Symulacja");
    expect(html).not.toContain("O modelach");
    expect(html).not.toContain("Asystent");
  });

  it("keeps Panel admina behind Więcej even when the admin link is enabled", () => {
    const html = renderToStaticMarkup(
      <AppNav
        showLogout={false}
        showLinks={true}
        showProfile={false}
        showAdmin={true}
      />,
    );

    expect(html).toContain("Więcej");
    expect(html).not.toContain("Panel admina");
  });
});
