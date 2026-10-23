import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VerticalStatChart } from "@/components/charts/VerticalStatChart";

describe("VerticalStatChart", () => {
  it("grows a positive rating up from zero and a negative one down", () => {
    const html = renderToStaticMarkup(
      <VerticalStatChart
        title="Ocena"
        playerName="Greer"
        thresholdLine={0}
        points={[
          { label: "plus", value: 3.3 },
          { label: "minus", value: -1.4 },
        ]}
      />,
    );
    const [positive, negative] = barStyles(html);

    expect(positive?.bottom).toBeGreaterThan(0);
    expect(negative?.bottom).toBe(0);
    expect(positive?.bottom).toBeCloseTo(29.787, 2);
    expect(positive?.height).toBeCloseTo(70.213, 2);
    expect(negative?.height).toBeCloseTo(29.787, 2);
    expect((negative?.bottom ?? 0) + (negative?.height ?? 0)).toBeCloseTo(
      positive?.bottom ?? 0,
      2,
    );
  });

  it("keeps a non-negative series anchored to the bottom of the track", () => {
    const html = renderToStaticMarkup(
      <VerticalStatChart
        title="Bramki"
        playerName="Greer"
        thresholdLine={0.5}
        points={[
          { label: "two", value: 2 },
          { label: "none", value: 0 },
        ]}
      />,
    );
    const [two, none] = barStyles(html);

    expect(two?.bottom).toBeNull();
    expect(none?.bottom).toBeNull();
    expect(two?.height).toBe(100);
    expect(none?.height).toBe(4);
  });
});

function barStyles(
  html: string,
): { height: number; bottom: number | null }[] {
  return [...html.matchAll(/style="([^"]*height:[^"]*)"/g)].map((match) => {
    const style = match[1] ?? "";
    const height = Number(style.match(/height:([^;%]+)%/)?.[1]);
    const bottomText = style.match(/bottom:([^;%]+)%/)?.[1];
    return {
      height,
      bottom: bottomText === undefined ? null : Number(bottomText),
    };
  });
}
