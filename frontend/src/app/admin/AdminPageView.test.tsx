import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminPageView } from "@/app/admin/AdminPageView";

describe("AdminPageView", () => {
  it("renders the protected admin chrome for an administrator", () => {
    const html = renderToStaticMarkup(<AdminPageView />);

    expect(html).toContain("Panel administratora");
    expect(html).toContain("Zarządzaj kontami użytkowników i ligami.");
    expect(html).not.toContain("<h2");
    expect(html).not.toContain("password");
    expect(html).not.toContain("password_hash");
  });
});
