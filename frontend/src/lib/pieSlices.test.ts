import { describe, expect, it } from "vitest";

import {
  buildPieSlicesFromSegments,
  normalizeProbabilitiesToPercents,
} from "@/lib/pieSlices";
import { getSemanticBarColor, CHART_COLOR_NEGATIVE } from "@/lib/chartColors";

describe("normalizeProbabilitiesToPercents", () => {
  it("returns integers that sum to 100", () => {
    const percents = normalizeProbabilitiesToPercents([0.444, 0.287, 0.269]);
    expect(percents.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(percents.every((value) => Number.isInteger(value))).toBe(true);
  });

  it("handles all zeros", () => {
    expect(normalizeProbabilitiesToPercents([0, 0, 0])).toEqual([0, 0, 0]);
  });
});

describe("buildPieSlicesFromSegments", () => {
  it("builds paths for non-zero slices", () => {
    const slices = buildPieSlicesFromSegments([
      { id: "a", percent: 55 },
      { id: "b", percent: 25 },
      { id: "c", percent: 20 },
    ]);
    expect(slices).toHaveLength(3);
    expect(slices[0]?.path).toContain("A 42 42");
    expect(slices.every((slice) => slice.percent > 0 && slice.path)).toBe(true);
  });

  it("marks a full circle when one segment is 100%", () => {
    const slices = buildPieSlicesFromSegments([
      { id: "a", percent: 100 },
      { id: "b", percent: 0 },
    ]);
    expect(slices[0]?.isFullCircle).toBe(true);
    expect(slices[0]?.path).toBeNull();
    expect(slices[1]?.path).toBeNull();
  });
});

describe("getSemanticBarColor away", () => {
  it("maps guest/away labels to red", () => {
    expect(getSemanticBarColor("Gość")).toBe(CHART_COLOR_NEGATIVE);
    expect(getSemanticBarColor("away")).toBe(CHART_COLOR_NEGATIVE);
    expect(getSemanticBarColor("Wygrana gościa")).toBe(CHART_COLOR_NEGATIVE);
  });
});
