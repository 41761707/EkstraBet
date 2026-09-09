import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ExpandableSection } from "@/components/ExpandableSection";

function detailsTag(html: string): string {
  const match = html.match(/<details\b[^>]*>/);
  if (!match) {
    throw new Error("Expected a <details> tag in ExpandableSection markup.");
  }
  return match[0];
}

describe("ExpandableSection", () => {
  it("keeps the open attribute when defaultOpen is set without onToggle", () => {
    const html = renderToStaticMarkup(
      createElement(
        ExpandableSection,
        {
          title: "Sekcja",
          defaultOpen: true,
        },
        "treść",
      ),
    );

    expect(detailsTag(html)).toMatch(/\sopen(=|>|\s)/);
  });

  it("omits the open attribute when onToggle is provided", () => {
    const html = renderToStaticMarkup(
      createElement(
        ExpandableSection,
        {
          title: "Sekcja",
          defaultOpen: true,
          onToggle: () => undefined,
        },
        "treść",
      ),
    );

    expect(detailsTag(html)).not.toMatch(/\sopen(=|>|\s)/);
  });
});
