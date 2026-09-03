import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";

const OPTIONS = [
  { id: 1, label: "Ekstraklasa" },
  { id: 2, label: "Premier League" },
];

function hasDisabledClearButton(html: string): boolean {
  return /<button[^>]*\sdisabled(?:=""|\s|>)/.test(html);
}

describe("MultiSelectCheckboxGroup", () => {
  it("shows Odznacz wszystkie under the list when clearing is enabled", () => {
    const html = renderToStaticMarkup(
      createElement(MultiSelectCheckboxGroup, {
        label: "Ligi",
        name: "leagues",
        options: OPTIONS,
        selectedIds: [],
        showClearAll: true,
        onChange: () => undefined,
      }),
    );
    expect(html).toContain("Odznacz wszystkie");
    expect(hasDisabledClearButton(html)).toBe(true);
  });

  it("enables Odznacz wszystkie when items are selected", () => {
    const html = renderToStaticMarkup(
      createElement(MultiSelectCheckboxGroup, {
        label: "Ligi",
        name: "leagues",
        options: OPTIONS,
        selectedIds: [1, 2],
        showClearAll: true,
        onChange: () => undefined,
      }),
    );
    expect(html).toContain("Odznacz wszystkie");
    expect(hasDisabledClearButton(html)).toBe(false);
  });

  it("renders popular events above niche sections without renaming options", () => {
    const html = renderToStaticMarkup(
      createElement(MultiSelectCheckboxGroup, {
        label: "Wydarzenia",
        name: "events",
        sections: [
          {
            title: "Najpopularniejsze",
            options: [{ id: 8, label: "Powyżej 2.5 gola" }],
          },
          {
            title: "Pozostałe",
            options: [{ id: 201, label: "0:3" }],
          },
        ],
        selectedIds: [],
        onChange: () => undefined,
      }),
    );
    expect(html).toContain("Najpopularniejsze");
    expect(html).toContain("Pozostałe");
    expect(html).toContain("Powyżej 2.5 gola");
    expect(html).toContain("0:3");
    expect(html.indexOf("Powyżej 2.5 gola")).toBeLessThan(html.indexOf("0:3"));
  });
});
