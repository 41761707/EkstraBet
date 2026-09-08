import { describe, expect, it, vi } from "vitest";

import {
  groupActiveModelsByFamily,
  loadModelsGroupedByFamily,
} from "@/lib/modelsByFamily";
import {
  BASKETBALL_SPORT_ID,
  FOOTBALL_SPORT_ID,
  type ModelDetailsResponse,
  type ModelEventFamily,
  type ModelSummary,
} from "@/types/api";

function modelSummary(
  overrides: Partial<ModelSummary> & Pick<ModelSummary, "id" | "name">,
): ModelSummary {
  return {
    active: 1,
    sport_id: FOOTBALL_SPORT_ID,
    sport_name: "Football",
    ...overrides,
  };
}

function modelDetails(
  overrides: Partial<ModelDetailsResponse> &
    Pick<ModelDetailsResponse, "id" | "name">,
): ModelDetailsResponse {
  return {
    active: 1,
    sport_id: FOOTBALL_SPORT_ID,
    sport_name: "Football",
    event_families: [],
    supported_events: [],
    total_events: 0,
    ...overrides,
  };
}

function family(name: string, id = 1): ModelEventFamily {
  return { id, sport_id: FOOTBALL_SPORT_ID, name };
}

describe("groupActiveModelsByFamily", () => {
  it("assigns models to REZULTAT, OU and BTTS families", () => {
    const models = [
      modelSummary({ id: 4, name: "Result model" }),
      modelSummary({ id: 7, name: "OU model" }),
      modelSummary({ id: 9, name: "BTTS model" }),
    ];
    const details = [
      modelDetails({
        id: 4,
        name: "Result model",
        event_families: [family("REZULTAT")],
      }),
      modelDetails({
        id: 7,
        name: "OU model",
        event_families: [family("ou", 2)],
      }),
      modelDetails({
        id: 9,
        name: "BTTS model",
        event_families: [family("Btts", 3)],
      }),
    ];

    expect(groupActiveModelsByFamily(models, details, FOOTBALL_SPORT_ID)).toEqual({
      result: [{ id: 4, label: "Result model" }],
      ou: [{ id: 7, label: "OU model" }],
      btts: [{ id: 9, label: "BTTS model" }],
    });
  });

  it("places a model in every matching family", () => {
    const models = [modelSummary({ id: 1, name: "Combo" })];
    const details = [
      modelDetails({
        id: 1,
        name: "Combo",
        event_families: [
          family("REZULTAT"),
          family("OU", 2),
          family("BTTS", 3),
        ],
      }),
    ];

    expect(groupActiveModelsByFamily(models, details, FOOTBALL_SPORT_ID)).toEqual({
      result: [{ id: 1, label: "Combo" }],
      ou: [{ id: 1, label: "Combo" }],
      btts: [{ id: 1, label: "Combo" }],
    });
  });

  it("skips inactive models and other sports", () => {
    const models = [
      modelSummary({ id: 1, name: "Inactive", active: 0 }),
      modelSummary({
        id: 2,
        name: "Basketball",
        sport_id: BASKETBALL_SPORT_ID,
      }),
      modelSummary({ id: 3, name: "Active football" }),
    ];
    const details = [
      modelDetails({
        id: 1,
        name: "Inactive",
        active: 0,
        event_families: [family("OU")],
      }),
      modelDetails({
        id: 2,
        name: "Basketball",
        sport_id: BASKETBALL_SPORT_ID,
        event_families: [family("OU")],
      }),
      modelDetails({
        id: 3,
        name: "Active football",
        event_families: [family("OU")],
      }),
    ];

    expect(groupActiveModelsByFamily(models, details, FOOTBALL_SPORT_ID)).toEqual({
      result: [],
      ou: [{ id: 3, label: "Active football" }],
      btts: [],
    });
  });

  it("skips models without details and sorts labels in Polish locale", () => {
    const models = [
      modelSummary({ id: 1, name: "Żubr" }),
      modelSummary({ id: 2, name: "Missing details" }),
      modelSummary({ id: 3, name: "Alfa" }),
    ];
    const details = [
      modelDetails({
        id: 1,
        name: "Żubr",
        event_families: [family("REZULTAT")],
      }),
      null,
      modelDetails({
        id: 3,
        name: "Alfa",
        event_families: [family("REZULTAT")],
      }),
    ];

    expect(groupActiveModelsByFamily(models, details, FOOTBALL_SPORT_ID).result).toEqual([
      { id: 3, label: "Alfa" },
      { id: 1, label: "Żubr" },
    ]);
  });
});

describe("loadModelsGroupedByFamily", () => {
  it("fetches details only for active models of the requested sport", async () => {
    const getModels = vi.fn().mockResolvedValue({
      models: [
        modelSummary({ id: 4, name: "Result model" }),
        modelSummary({ id: 8, name: "Inactive", active: 0 }),
        modelSummary({
          id: 11,
          name: "Other sport",
          sport_id: BASKETBALL_SPORT_ID,
        }),
      ],
      total_models: 3,
    });
    const getModelDetails = vi.fn().mockImplementation(async (modelId: number) => {
      if (modelId === 4) {
        return modelDetails({
          id: 4,
          name: "Result model",
          event_families: [family("REZULTAT")],
        });
      }
      throw new Error("unexpected details fetch");
    });

    const grouped = await loadModelsGroupedByFamily(FOOTBALL_SPORT_ID, {
      getModels,
      getModelDetails,
    });

    expect(getModelDetails).toHaveBeenCalledTimes(1);
    expect(getModelDetails).toHaveBeenCalledWith(4);
    expect(grouped.result).toEqual([{ id: 4, label: "Result model" }]);
  });

  it("skips a model when details fetch fails", async () => {
    const getModels = vi.fn().mockResolvedValue({
      models: [
        modelSummary({ id: 4, name: "Broken" }),
        modelSummary({ id: 7, name: "OU model" }),
      ],
      total_models: 2,
    });
    const getModelDetails = vi.fn().mockImplementation(async (modelId: number) => {
      if (modelId === 4) {
        throw new Error("details unavailable");
      }
      return modelDetails({
        id: 7,
        name: "OU model",
        event_families: [family("OU")],
      });
    });

    const grouped = await loadModelsGroupedByFamily(FOOTBALL_SPORT_ID, {
      getModels,
      getModelDetails,
    });

    expect(grouped.ou).toEqual([{ id: 7, label: "OU model" }]);
    expect(grouped.result).toEqual([]);
  });
});
