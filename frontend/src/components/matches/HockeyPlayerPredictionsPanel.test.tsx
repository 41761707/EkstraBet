import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyPlayerPredictionsPanel } from "@/components/matches/HockeyPlayerPredictionsPanel";
import type { HockeyPlayerPredictions } from "@/types/api";

const HOME_TEAM_NAME = "Columbus Blue Jackets";
const AWAY_TEAM_NAME = "Philadelphia Flyers";

function predictions(): HockeyPlayerPredictions {
  return {
    home: [
      {
        player_id: 1898,
        player_name: "Fantilli A.",
        team_id: 10,
        lines: [
          { event_id: 190, line: 2.5, expected_value: 2.4, probability: 46 },
          { event_id: 196, line: 0.5, expected_value: 0.3, probability: 26 },
          { event_id: 194, line: 0.5, expected_value: 0.4, probability: 33 },
          { event_id: 192, line: 0.5, expected_value: 0.7, probability: 50 },
          { event_id: 192, line: 1.5, expected_value: 0.7, probability: 18 },
        ],
      },
    ],
    away: [],
  };
}

function renderPanel(
  value: HockeyPlayerPredictions | null,
  stage: "initial" | "final" | null = "final",
): string {
  return renderToStaticMarkup(
    <HockeyPlayerPredictionsPanel
      predictions={value}
      homeTeamName={HOME_TEAM_NAME}
      awayTeamName={AWAY_TEAM_NAME}
      predictionStage={stage}
    />,
  );
}

describe("HockeyPlayerPredictionsPanel", () => {
  it("renders the beta columns for a skater", () => {
    const html = renderPanel(predictions());

    expect(html).toContain(HOME_TEAM_NAME);
    expect(html).toContain("Fantilli A.");
    expect(html).toContain("E[SOG]");
    expect(html).toContain("P(SOG &gt; 2.5)");
    expect(html).toContain("P(gol)");
    expect(html).toContain("P(asysta)");
    expect(html).toContain("P(punkt)");
    expect(html).toContain("P(2+ pkt)");
    expect(html).toContain("2.40");
    expect(html).toContain("46.0%");
    expect(html).toContain("26.0%");
    expect(html).toContain("33.0%");
    expect(html).toContain("50.0%");
    expect(html).toContain("18.0%");
    expect(html).toContain("Predykcja ostateczna");
    expect(html).toContain("Beta:");
    expect(html).toContain("Brak predykcji");
  });

  it("shows an empty state when predictions are missing", () => {
    const html = renderPanel(null, null);

    expect(html).toContain("Brak predykcji zawodników");
    expect(html).not.toContain("Predykcja pierwotna");
    expect(html).not.toContain("E[SOG]");
  });
});
