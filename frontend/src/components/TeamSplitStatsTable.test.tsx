import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TeamSplitStatsTable } from "@/components/TeamSplitStatsTable";
import type { TeamSplitStats } from "@/types/api";

function stats(overrides: Partial<TeamSplitStats> = {}): TeamSplitStats {
  return {
    played: 1,
    wins: 1,
    draws: 0,
    losses: 0,
    goals_for: 3,
    goals_conceded: 2,
    goal_difference: 1,
    points: 2,
    ...overrides,
  };
}

describe("TeamSplitStatsTable", () => {
  it("renders D for football and hides OT", () => {
    const html = renderToStaticMarkup(
      <TeamSplitStatsTable
        overall={stats()}
        home={stats()}
        away={stats()}
      />,
    );

    expect(html).toContain(">D<");
    expect(html).not.toContain(">OT<");
  });

  it("renders OT for hockey and hides D", () => {
    const html = renderToStaticMarkup(
      <TeamSplitStatsTable
        variant="hockey"
        overall={stats({ overtime_losses: 1 })}
        home={stats()}
        away={stats()}
      />,
    );

    expect(html).toContain(">OT<");
    expect(html).not.toContain(">D<");
    expect(html).toContain("Przegrane po dogrywce lub karnych");
  });
});
