import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PlayerSummaryTiles } from "@/components/players/PlayerSummaryTiles";
import { HOCKEY_SPORT_ID } from "@/types/api";
import type { HockeyPlayerStatsSummary } from "@/types/api";

const summary: HockeyPlayerStatsSummary = {
  is_goalie: false,
  points: 3,
  goals: 1,
  assists: 2,
  plus_minus: -3,
  penalty_minutes: 11,
  average_penalty_minutes: 1.5,
  average_sog: 2,
  average_toi: "12:16",
  shots_against: null,
  shots_saved: null,
  saves_acc: null,
};

describe("PlayerSummaryTiles", () => {
  it("shows the mean rating and a dash when no game was rated", () => {
    const rated = renderToStaticMarkup(
      <PlayerSummaryTiles
        sportId={HOCKEY_SPORT_ID}
        playerRole="skater"
        summary={summary}
        averageRating={1.24}
      />,
    );
    const empty = renderToStaticMarkup(
      <PlayerSummaryTiles
        sportId={HOCKEY_SPORT_ID}
        playerRole="skater"
        summary={summary}
        averageRating={null}
      />,
    );

    expect(rated).toContain("Średnia ocena");
    expect(rated).toContain("6.2");
    expect(empty).toContain("Średnia ocena");
    expect(empty).toContain("—");
    expect(empty).not.toContain("+0.0");
  });
});
