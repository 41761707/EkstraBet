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
});
