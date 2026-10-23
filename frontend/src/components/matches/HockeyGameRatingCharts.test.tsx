import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyGameRatingCharts } from "@/components/matches/HockeyGameRatingCharts";
import { CHART_COLOR_NEGATIVE, CHART_COLOR_POSITIVE } from "@/lib/chartColors";
import type {
  HockeyGameRating,
  HockeyRatedPlayer,
  HockeyRatingParts,
} from "@/types/api";

function parts(overrides: Partial<HockeyRatingParts> = {}): HockeyRatingParts {
  return {
    production: 0,
    empty_net: 0,
    shots: 0,
    teammate_goals: 0,
    faceoffs: 0,
    goals_against: 0,
    penalties: 0,
    blocks: 0,
    goaltending: 0,
    ...overrides,
  };
}

function player(
  overrides: Pick<HockeyRatedPlayer, "player_id" | "player_name" | "group"> &
    Partial<HockeyRatedPlayer>,
): HockeyRatedPlayer {
  return {
    offense: 0,
    defense: 0,
    total: 0,
    parts: parts(),
    ...overrides,
  };
}

function sampleRating(): HockeyGameRating {
  return {
    teams: [
      {
        team_id: 10,
        team_name: "Philadelphia Flyers",
        players: [
          player({
            player_id: 1,
            player_name: "Konecny T.",
            group: "forward",
            offense: 3.2,
            defense: -1.4,
            total: 1.8,
            parts: parts({ production: 3, shots: 0.2, goals_against: -1.4 }),
          }),
          player({
            player_id: 2,
            player_name: "Sanheim T.",
            group: "defense",
            offense: 0.5,
            defense: 0.1,
            total: 0.6,
          }),
          player({
            player_id: 3,
            player_name: "Ersson S.",
            group: "goalie",
            offense: 0,
            defense: 2.8,
            total: 2.8,
            parts: parts({ goaltending: 2.8 }),
          }),
        ],
      },
      {
        team_id: 20,
        team_name: "Ottawa Senators",
        players: [
          player({
            player_id: 4,
            player_name: "Stutzle T.",
            group: "forward",
            offense: 1,
            defense: -0.4,
            total: 0.6,
          }),
        ],
      },
    ],
  };
}

describe("HockeyGameRatingCharts", () => {
  it("renders both team names and three chart titles in each column", () => {
    const html = renderToStaticMarkup(
      <HockeyGameRatingCharts rating={sampleRating()} />,
    );

    expect(html.indexOf("Philadelphia Flyers")).toBeLessThan(
      html.indexOf("Ottawa Senators"),
    );
    expect(html.match(/Ogólna/g)).toHaveLength(2);
    expect(html.match(/Ofensywa/g)).toHaveLength(2);
    expect(html.match(/Defensywa/g)).toHaveLength(2);
    expect(html.indexOf("Ogólna")).toBeLessThan(html.indexOf("Ofensywa"));
    expect(html.indexOf("Ofensywa")).toBeLessThan(html.indexOf("Defensywa"));
    expect(html.indexOf("Napastnicy")).toBeLessThan(html.indexOf("Obrońcy"));
    expect(html.indexOf("Obrońcy")).toBeLessThan(html.indexOf("Bramkarze"));
    expect(html.indexOf("Bramkarze")).toBeLessThan(html.indexOf("Ofensywa"));
    expect(html).toContain("md:grid-cols-2");
    expect(html).toContain("bg-chart-track");
    expect(html).toContain("left-1/2");
    expect(html).toContain(`background-color:${CHART_COLOR_POSITIVE}`);
    expect(html).toContain(`background-color:${CHART_COLOR_NEGATIVE}`);
    expect(html).toContain("right:50%");
    expect(html).toContain("left:50%");
  });

  it("puts production and goals against in the row title", () => {
    const html = renderToStaticMarkup(
      <HockeyGameRatingCharts rating={sampleRating()} />,
    );

    expect(html).toContain(
      "Produkcja +3.0, strzały +0.2, bramki stracone \u22121.4",
    );
    expect(html).toContain("+3.2");
    expect(html).toContain("\u22121.4");
    expect(html).toContain("0.0");
  });

  it("does not render the rating heading when the rating is null", () => {
    const html = renderToStaticMarkup(<HockeyGameRatingCharts rating={null} />);

    expect(html).not.toContain("Ocena");
  });

  it("shows a short empty label when a team has no players", () => {
    const html = renderToStaticMarkup(
      <HockeyGameRatingCharts
        rating={{
          teams: [
            {
              team_id: 10,
              team_name: "Philadelphia Flyers",
              players: [],
            },
          ],
        }}
      />,
    );

    expect(html).toContain("Philadelphia Flyers");
    expect(html).toContain("Brak oceny");
    expect(html).not.toContain("Ogólna");
  });
});
