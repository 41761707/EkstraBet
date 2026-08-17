import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DateInput } from "@/components/filters/DateInput";

describe("DateInput", () => {
  it("shows the selected date in Polish format", () => {
    const html = renderToStaticMarkup(
      createElement(DateInput, {
        value: "2026-06-20",
        onChange: () => undefined,
        ariaLabel: "Data od",
      }),
    );
    expect(html).toContain("20.06.2026");
    expect(html).toContain('aria-haspopup="dialog"');
  });

  it("shows a placeholder when the value is empty", () => {
    const html = renderToStaticMarkup(
      createElement(DateInput, {
        value: "",
        onChange: () => undefined,
        ariaLabel: "Data od",
      }),
    );
    expect(html).toContain("dd.mm.rrrr");
  });
});
