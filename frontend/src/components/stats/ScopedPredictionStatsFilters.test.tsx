import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  INVALID_SCOPED_DATE_RANGE_MESSAGE,
  ScopedPredictionStatsFilters,
} from "@/components/stats/ScopedPredictionStatsFilters";
import { createDefaultScopedPredictionStatsFilters } from "@/components/stats/scopedPredictionStatsModel";
import type { FilterOption } from "@/types/api";

const RESULT_MODELS: FilterOption[] = [{ id: 4, label: "Model 1X2" }];
const OU_MODELS: FilterOption[] = [{ id: 7, label: "Model OU" }];
const BTTS_MODELS: FilterOption[] = [{ id: 9, label: "Model BTTS" }];

function renderFilters(
  overrides: Partial<Parameters<typeof ScopedPredictionStatsFilters>[0]> = {},
): string {
  return renderToStaticMarkup(
    createElement(ScopedPredictionStatsFilters, {
      resultModels: RESULT_MODELS,
      ouModels: OU_MODELS,
      bttsModels: BTTS_MODELS,
      values: {
        ...createDefaultScopedPredictionStatsFilters(),
        modelResultIds: [4],
        modelOuIds: [7],
        modelBttsIds: [9],
      },
      onApply: () => undefined,
      ...overrides,
    }),
  );
}

describe("ScopedPredictionStatsFilters", () => {
  it("renders Od/Do date labels, model families and tax without round filters", () => {
    const html = renderFilters();

    expect(html).toContain(">Od<");
    expect(html).toContain(">Do<");
    expect(html).toContain("Od: dd.mm.rrrr");
    expect(html).toContain("Do: dd.mm.rrrr");
    expect(html).toContain("Modele rezultatu");
    expect(html).toContain("Modele OU");
    expect(html).toContain("Modele BTTS");
    expect(html).toContain("Uwzględnij podatek 12%");
    expect(html).toContain("Zastosuj filtry");
    expect(html).toContain("Resetuj");
    expect(html.toLowerCase()).not.toContain("kolejka");
  });

  it("blocks Apply and shows a message when Od is later than Do", () => {
    const html = renderFilters({
      values: {
        ...createDefaultScopedPredictionStatsFilters(),
        modelResultIds: [4],
        modelOuIds: [7],
        modelBttsIds: [9],
        dateFrom: "2026-05-31",
        dateTo: "2025-08-01",
      },
    });

    expect(html).toContain(INVALID_SCOPED_DATE_RANGE_MESSAGE);
    expect(html).toContain('<button type="submit" disabled=""');
    expect(html).not.toContain('<button type="button" disabled=""');
  });

  it("keeps Apply enabled when dates are empty or ordered", () => {
    const html = renderFilters();

    expect(html).not.toContain(INVALID_SCOPED_DATE_RANGE_MESSAGE);
    expect(html).not.toContain('<button type="submit" disabled=""');
    expect(html).toContain('<button type="submit" class=');
  });

  it("disables Apply and Reset while loading", () => {
    const html = renderFilters({ isLoading: true });

    expect(html).toContain('<button type="submit" disabled=""');
    expect(html).toContain('<button type="button" disabled=""');
  });

  it("disables Apply and Reset when no model options are available", () => {
    const html = renderFilters({
      resultModels: [],
      ouModels: [],
      bttsModels: [],
    });

    expect(html).toContain('<button type="submit" disabled=""');
    expect(html).toContain('<button type="button" disabled=""');
  });
});
