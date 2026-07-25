import { describe, expect, it } from "vitest";

import {
  CURRENT_MODEL_NAMES,
  getModelDocumentation,
  getModelsByPhase,
  hasCompleteDocumentation,
  MODEL_CONCEPT_GLOSSARY,
  MODEL_DOCUMENTATION,
  RATING_GLOSSARY,
  toDocumentedModelView,
  type CurrentModelName,
} from "@/lib/modelDocumentation";
import type { ModelDetailsResponse } from "@/types/api";

const EXPECTED_NAMES: CurrentModelName[] = [
  "FOOTBALL_RESULT_V2",
  "FOOTBALL_BTTS_V2",
  "FOOTBALL_GOALS_POISSON_V1",
  "FOOTBALL_PLAYED_BETTER_V1",
  "FOOTBALL_PLAYED_BETTER_NOXG_V1",
];

const EXPECTED_VERSIONS: Record<CurrentModelName, string> = {
  FOOTBALL_RESULT_V2: "2.0.0",
  FOOTBALL_BTTS_V2: "2.0.0",
  FOOTBALL_GOALS_POISSON_V1: "1.0.0",
  FOOTBALL_PLAYED_BETTER_V1: "1.0.0",
  FOOTBALL_PLAYED_BETTER_NOXG_V1: "1.0.0",
};

function sampleApiDetails(
  overrides: Partial<ModelDetailsResponse> = {},
): ModelDetailsResponse {
  return {
    id: 1,
    name: "FOOTBALL_RESULT_V2",
    active: 1,
    sport_id: 1,
    sport_name: "Football",
    event_families: [],
    supported_events: [],
    total_events: 0,
    ...overrides,
  };
}

describe("MODEL_DOCUMENTATION", () => {
  it("contains exactly five unique current models", () => {
    expect(MODEL_DOCUMENTATION).toHaveLength(5);
    expect(CURRENT_MODEL_NAMES).toEqual(EXPECTED_NAMES);
    expect(new Set(CURRENT_MODEL_NAMES).size).toBe(5);
  });

  it("provides all required sections for every entry", () => {
    for (const entry of MODEL_DOCUMENTATION) {
      expect(hasCompleteDocumentation(entry)).toBe(true);
      expect(entry.inputs.length).toBeGreaterThan(0);
      expect(entry.featureEngineering.length).toBeGreaterThan(0);
      expect(entry.predictionSteps.length).toBeGreaterThan(0);
      expect(entry.outputs.length).toBeGreaterThan(0);
      expect(entry.metrics.length).toBeGreaterThan(0);
      expect(entry.limitations.length).toBeGreaterThan(0);
    }
  });

  it("matches config versions for each model", () => {
    for (const name of EXPECTED_NAMES) {
      expect(getModelDocumentation(name).version).toBe(
        EXPECTED_VERSIONS[name],
      );
    }
  });

  it("separates pre-match and post-match phases correctly", () => {
    const preMatch = getModelsByPhase("pre_match").map((entry) => entry.name);
    const postMatch = getModelsByPhase("post_match").map(
      (entry) => entry.name,
    );

    expect(preMatch).toEqual([
      "FOOTBALL_RESULT_V2",
      "FOOTBALL_BTTS_V2",
      "FOOTBALL_GOALS_POISSON_V1",
    ]);
    expect(postMatch).toEqual([
      "FOOTBALL_PLAYED_BETTER_V1",
      "FOOTBALL_PLAYED_BETTER_NOXG_V1",
    ]);
  });

  it("marks PLAYED_BETTER metrics as unpublished instead of inventing values", () => {
    for (const name of [
      "FOOTBALL_PLAYED_BETTER_V1",
      "FOOTBALL_PLAYED_BETTER_NOXG_V1",
    ] as const) {
      const metrics = getModelDocumentation(name).metrics;
      expect(metrics.every((metric) => metric.value === null)).toBe(true);
      expect(
        metrics.every((metric) => metric.artifactVersion === null),
      ).toBe(true);
    }
  });

  it("keeps offline validation metrics for pre-match release artifacts", () => {
    const result = getModelDocumentation("FOOTBALL_RESULT_V2");
    const btts = getModelDocumentation("FOOTBALL_BTTS_V2");
    const goals = getModelDocumentation("FOOTBALL_GOALS_POISSON_V1");

    expect(result.metrics.some((metric) => metric.key === "accuracy")).toBe(
      true,
    );
    expect(btts.metrics.some((metric) => metric.key === "log_loss")).toBe(
      true,
    );
    expect(
      goals.metrics.some((metric) => metric.key === "poisson_nll"),
    ).toBe(true);
    expect(
      result.metrics.every((metric) => metric.value !== null),
    ).toBe(true);
  });

  it("documents LSTM, logit, Softmax, Elo, GAP and Czech for transparency", () => {
    expect(MODEL_CONCEPT_GLOSSARY.map((entry) => entry.id)).toEqual([
      "lstm",
      "logit",
      "softmax",
      "elo",
      "gap",
      "czech",
    ]);
    expect(RATING_GLOSSARY.map((entry) => entry.id)).toEqual([
      "elo",
      "gap",
      "czech",
    ]);
    for (const entry of MODEL_CONCEPT_GLOSSARY) {
      expect(entry.title.length).toBeGreaterThan(0);
      expect(entry.summary.length).toBeGreaterThan(0);
      expect(entry.details.length).toBeGreaterThan(0);
    }
  });
});

describe("toDocumentedModelView", () => {
  it("preserves documentation when API details are missing", () => {
    const documentation = getModelDocumentation("FOOTBALL_RESULT_V2");
    const view = toDocumentedModelView(documentation, null);

    expect(view.name).toBe(documentation.name);
    expect(view.purpose).toBe(documentation.purpose);
    expect(view.apiDetails).toBeNull();
    expect(view.availabilityNote).toBe(
      "Status dostępności nie został pobrany",
    );
  });

  it("marks inactive API models without dropping documentation", () => {
    const documentation = getModelDocumentation("FOOTBALL_BTTS_V2");
    const view = toDocumentedModelView(
      documentation,
      sampleApiDetails({ name: documentation.name, active: 0 }),
    );

    expect(view.apiDetails?.active).toBe(0);
    expect(view.availabilityNote).toBe("Model nieaktywny w API");
    expect(view.algorithm).toBe(documentation.algorithm);
  });
});
