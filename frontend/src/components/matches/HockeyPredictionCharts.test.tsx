import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyPredictionCharts } from "@/components/matches/HockeyPredictionCharts";
import type { MatchPredictionItem } from "@/types/api";

function prediction(
  eventId: number,
  modelId: number,
  modelName: string,
  value: number,
): MatchPredictionItem {
  return {
    prediction_id: eventId + modelId,
    event_id: eventId,
    event_name: "Rynek",
    event_family: { id: 1, name: "HOCKEY_ML" },
    model_id: modelId,
    model_name: modelName,
    value,
    outcome: null,
  };
}

describe("HockeyPredictionCharts", () => {
  it("renders a winner donut and both totals for each model", () => {
    const html = renderToStaticMarkup(
      <HockeyPredictionCharts
        homeTeamLabel="San Jose Sharks"
        awayTeamLabel="Boston Bruins"
        predictions={[
          prediction(234, 8, "HOCKEY_GOALS_GBM_V1", 0.516),
          prediction(236, 8, "HOCKEY_GOALS_GBM_V1", 0.54),
          prediction(238, 8, "HOCKEY_GOALS_GBM_V1", 0.41),
          prediction(235, 21, "HOCKEY_RATINGS_POISSON_V1", 0.607),
          prediction(237, 21, "HOCKEY_RATINGS_POISSON_V1", 0.48),
          prediction(239, 21, "HOCKEY_RATINGS_POISSON_V1", 0.63),
        ]}
      />,
    );

    expect(html).toContain("Analiza predykcji");
    expect(html).toContain("HOCKEY_GOALS_GBM_V1");
    expect(html).toContain("HOCKEY_RATINGS_POISSON_V1");
    expect(html).toContain("Zwycięzca (OT/SO)");
    expect(html).toContain("Suma 5,5 gola");
    expect(html).toContain("Suma 6,5 gola");
    expect(html).toContain("San Jose Sharks");
    expect(html).toContain("Boston Bruins");
    expect(html).toContain("51.6%");
    expect(html).toContain("60.7%");
    expect(html).toContain("Powyżej");
    expect(html).toContain("Poniżej");
  });

  it("renders nothing without hockey markets", () => {
    const html = renderToStaticMarkup(
      <HockeyPredictionCharts
        homeTeamLabel="Legia"
        awayTeamLabel="Lech"
        predictions={[]}
      />,
    );

    expect(html).toBe("");
  });
});
