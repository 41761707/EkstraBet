import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  HockeyLeagueRatingBoard,
  HockeyRatingBoardCharts,
} from "@/components/hockey/HockeyLeagueRatingBoard";
import type { HockeyRatingBoard } from "@/types/api";

describe("HockeyLeagueRatingBoard", () => {
  it("shows the season window and the worst-games heading before data loads", () => {
    const html = renderToStaticMarkup(
      <HockeyLeagueRatingBoard seasonId={12} />,
    );

    expect(html).toContain("Oceny meczowe");
    expect(html).toContain("Ostatnie 5 meczów");
    expect(html).toContain("Najgorsze mecze");
  });

  it("draws a positive night to the right of zero and a negative one to the left", () => {
    const html = renderToStaticMarkup(
      <HockeyRatingBoardCharts board={sampleBoard} />,
    );

    expect(html).toContain("Edmonton Oilers · 9 meczów");
    expect(html).toContain('href="/matches/10"');
    expect(html).toContain("left:50%");
    expect(html).toContain("right:50%");
    expect(html).toContain("+5.5");
    expect(html).toContain("\u22124.9");
  });
});

const sampleBoard: HockeyRatingBoard = {
  season_id: 13,
  window: 0,
  averages: [
    {
      player_id: 1,
      player_name: "McDavid C.",
      team_name: "Edmonton Oilers",
      games: 9,
      average: 3,
    },
  ],
  best_games: [
    {
      player_id: 1,
      player_name: "McDavid C.",
      match_id: 10,
      match_date: "02.10.2026",
      opponent_name: "Vancouver Canucks",
      total: 5.5,
    },
  ],
  worst_games: [
    {
      player_id: 2,
      player_name: "Lankinen K.",
      match_id: 11,
      match_date: "02.10.2026",
      opponent_name: "Edmonton Oilers",
      total: -4.9,
    },
  ],
};
