import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PrematchHeadToHeadSection } from "@/components/matches/PrematchHeadToHeadSection";
import type { HeadToHeadSummary, MatchSummary } from "@/types/api";

function meeting(
  id: number,
  homeGoals: number,
  awayGoals: number,
): MatchSummary {
  return {
    id,
    league_id: 1,
    season_id: 10,
    round: id,
    round_label: String(id),
    game_date: "2026-05-10T18:00:00",
    home_team: { id: 1, name: "Charleroi", shortcut: "CHA" },
    away_team: { id: 2, name: "Antwerp", shortcut: "ANT" },
    home_goals: homeGoals,
    away_goals: awayGoals,
    result: "1",
    is_played: true,
    score_resolution: null,
  };
}

function headToHead(meetings: MatchSummary[]): HeadToHeadSummary {
  return {
    team_id: 1,
    opponent_id: 2,
    played: 22,
    wins: 6,
    draws: 4,
    losses: 12,
    goals_for: 26,
    goals_conceded: 32,
    btts_count: 14,
    btts_percentage: 63.6,
    avg_goals_per_match: 2.64,
    meetings,
  };
}

describe("PrematchHeadToHeadSection", () => {
  it("shows played and over 2.5 from the selected meetings, not the full history", () => {
    const html = renderToStaticMarkup(
      <PrematchHeadToHeadSection
        headToHead={headToHead([
          meeting(1, 2, 1),
          meeting(2, 0, 0),
        ])}
        meetings={[meeting(1, 2, 1), meeting(2, 0, 0)]}
        isHockey={false}
        seasonId={10}
        leagueId={1}
      />,
    );

    expect(html).toContain("Rozegrane");
    expect(html).toContain(">2<");
    expect(html).not.toContain(">22<");
    expect(html).toContain("Over 2.5");
    expect(html).toContain("50.0%");
    expect(html).toContain("BTTS");
    expect(html).not.toContain("63.6%");
  });

  it("shows over 6.5 for hockey and hides BTTS", () => {
    const html = renderToStaticMarkup(
      <PrematchHeadToHeadSection
        headToHead={headToHead([meeting(1, 4, 3)])}
        meetings={[meeting(1, 4, 3)]}
        isHockey
        seasonId={10}
        leagueId={45}
      />,
    );

    expect(html).toContain("Over 6.5");
    expect(html).toContain("100.0%");
    expect(html).not.toContain("BTTS");
    expect(html).not.toContain("Over 2.5");
  });
});
