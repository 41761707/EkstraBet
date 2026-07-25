import { describe, expect, it } from "vitest";

import { MathText } from "@/components/models/MathText";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

describe("MathText", () => {
  it("renders plain text without math markers", () => {
    const html = renderToStaticMarkup(
      createElement(MathText, { text: "Zwykły opis bez wzoru" }),
    );
    expect(html).toContain("Zwykły opis bez wzoru");
    expect(html).not.toContain("katex");
  });

  it("renders inline KaTeX for $...$ fragments", () => {
    const html = renderToStaticMarkup(
      createElement(MathText, {
        text: "Softmax: $P(i) = e^{z_i}$ działa tak.",
      }),
    );
    expect(html).toContain("katex");
    expect(html).toContain("Softmax:");
    expect(html).toContain("działa tak.");
  });

  it("renders display KaTeX for $$...$$ fragments", () => {
    const html = renderToStaticMarkup(
      createElement(MathText, {
        text: "Wzór: $$P(i)=\\dfrac{e^{z_i}}{\\sum_j e^{z_j}}$$ koniec.",
      }),
    );
    expect(html).toContain("katex-display");
    expect(html).toContain("Wzór:");
    expect(html).toContain("koniec.");
  });
});
