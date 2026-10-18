import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyEventRankingBoard } from "@/components/hockey/HockeyEventRankingBoard";
import type { HockeyPlayerEventRanking } from "@/types/api";

function shotRanking(): HockeyPlayerEventRanking {
  return {
    metric: "shot",
    label: "Strzał",
    hint: "P(SOG > 2.5)",
    rows: [
      {
        rank: 1,
        player_id: 7,
        player_name: "MacKinnon",
        team_id: 1,
        team_name: "Colorado Avalanche",
        team_shortcut: "COL",
        match_id: 99,
        game_date: "2026-10-18T01:00:00",
        opponent_name: "Dallas Stars",
        opponent_shortcut: "DAL",
        is_home: true,
        probability: 71.2,
        expected_shots: 4.12,
      },
    ],
  };
}

function rankedRow(
  rank: number,
  name: string,
): HockeyPlayerEventRanking["rows"][number] {
  return {
    rank,
    player_id: rank,
    player_name: name,
    team_id: rank,
    team_name: "Club",
    team_shortcut: "CLB",
    match_id: 100 + rank,
    game_date: "2026-10-18T01:00:00",
    opponent_name: "Opponent",
    opponent_shortcut: "OPP",
    is_home: false,
    probability: 80 - rank,
    expected_shots: null,
  };
}

describe("HockeyEventRankingBoard", () => {
  it("links the row, shows the shot total and the home opponent", () => {
    const html = renderToStaticMarkup(
      <HockeyEventRankingBoard ranking={shotRanking()} />,
    );

    expect(html).toContain('href="/matches/99"');
    expect(html).toContain("4.12 SOG");
    expect(html).toContain("vs DAL");
    expect(html).toContain("71.2%");
    expect(html).toContain("01:00");
    expect(html).toContain("MacKinnon");
    expect(html).toContain("COL");
    expect(html).not.toContain("<ol");
  });

  it("puts the first three on the podium and the rest in the list", () => {
    const ranking: HockeyPlayerEventRanking = {
      metric: "point",
      label: "Punkt",
      hint: "P(punkt)",
      rows: [
        rankedRow(1, "Leader"),
        rankedRow(2, "Second"),
        rankedRow(3, "Third"),
        rankedRow(4, "Fourth"),
      ],
    };
    const html = renderToStaticMarkup(
      <HockeyEventRankingBoard ranking={ranking} />,
    );
    const listStart = html.indexOf("<ol");

    expect(listStart).toBeGreaterThan(0);
    expect(html.slice(0, listStart)).toContain("Leader");
    expect(html.slice(0, listStart)).toContain("Second");
    expect(html.slice(0, listStart)).toContain("Third");
    expect(html.slice(0, listStart)).not.toContain("Fourth");
    expect(html.slice(listStart)).toContain("Fourth");
    expect(html.slice(listStart)).toContain("@ OPP");
    expect(html).toContain("min-h-32");
  });
});
