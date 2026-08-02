import { describe, expect, it } from "vitest";

import {
  buildRatingProgressChartModel,
  buildSeriesSourcePoints,
  colorForTeam,
  computeRatingExtent,
  filterTeamsByIds,
  resolveEndLabelYs,
  seasonBaselineIso,
  selectDefaultTeamIds,
  selectBottomTeamIds,
  sortTeamsByCurrentRating,
  teamDisplayLabel,
} from "@/components/charts/ratingProgressChartModel";
import type { TeamRatingProgress } from "@/types/api";

function makeTeam(
  overrides: Partial<TeamRatingProgress> & Pick<TeamRatingProgress, "team_id">,
): TeamRatingProgress {
  const teamId = overrides.team_id;
  return {
    team_id: teamId,
    team_name: overrides.team_name ?? `Team ${teamId}`,
    team_shortcut: overrides.team_shortcut ?? null,
    start_rating: overrides.start_rating ?? 1500,
    current_rating: overrides.current_rating ?? 1500,
    change: overrides.change ?? 0,
    current_rank: overrides.current_rank ?? 1,
    points: overrides.points ?? [
      {
        match_id: teamId * 10,
        round_number: 1,
        played_at: "2025-08-01T17:00:00",
        rating: overrides.current_rating ?? 1500,
      },
    ],
  };
}

describe("teamDisplayLabel", () => {
  it("prefers shortcut when present", () => {
    expect(
      teamDisplayLabel({ team_name: "Legia Warszawa", team_shortcut: "LEG" }),
    ).toBe("LEG");
  });

  it("falls back to full name", () => {
    expect(
      teamDisplayLabel({ team_name: "Legia Warszawa", team_shortcut: null }),
    ).toBe("Legia Warszawa");
    expect(
      teamDisplayLabel({ team_name: "Legia Warszawa", team_shortcut: "  " }),
    ).toBe("Legia Warszawa");
  });
});

describe("colorForTeam", () => {
  it("is stable for the same team_id", () => {
    expect(colorForTeam(7)).toBe(colorForTeam(7));
    expect(colorForTeam(1)).not.toBe(colorForTeam(2));
  });
});

describe("selection helpers", () => {
  const teams = [
    makeTeam({ team_id: 3, current_rating: 1600, current_rank: 2 }),
    makeTeam({ team_id: 1, current_rating: 1700, current_rank: 1 }),
    makeTeam({ team_id: 2, current_rating: 1600, current_rank: 3 }),
    makeTeam({ team_id: 4, current_rating: 1400, current_rank: 4 }),
  ];

  it("sorts by current rating then lower team_id", () => {
    expect(sortTeamsByCurrentRating(teams).map((team) => team.team_id)).toEqual(
      [1, 2, 3, 4],
    );
  });

  it("selects default top 6 (or fewer)", () => {
    expect(selectDefaultTeamIds(teams, 2)).toEqual([1, 2]);
    expect(selectDefaultTeamIds(teams)).toEqual([1, 2, 3, 4]);
  });

  it("selects bottom N by current rating", () => {
    expect(selectBottomTeamIds(teams, 2)).toEqual([3, 4]);
    expect(selectBottomTeamIds(teams)).toEqual([1, 2, 3, 4]);
  });

  it("filters by ids while keeping rating order", () => {
    expect(
      filterTeamsByIds(teams, [4, 1]).map((team) => team.team_id),
    ).toEqual([1, 4]);
  });
});

describe("series geometry", () => {
  it("prepends seasonal baseline before post-match points", () => {
    const team = makeTeam({
      team_id: 1,
      start_rating: 1510,
      current_rating: 1550,
      points: [
        {
          match_id: 11,
          round_number: 1,
          played_at: "2025-08-10T17:00:00",
          rating: 1520,
        },
        {
          match_id: 12,
          round_number: 2,
          played_at: "2025-08-17T17:00:00",
          rating: 1550,
        },
      ],
    });
    const points = buildSeriesSourcePoints(team, "2025-08-01T17:00:00");
    expect(points).toHaveLength(3);
    expect(points[0]).toMatchObject({
      isBaseline: true,
      rating: 1510,
      playedAt: "2025-08-01T17:00:00",
      matchId: null,
    });
    expect(points[2]?.rating).toBe(1550);
  });

  it("returns empty series when team has no points", () => {
    const team = makeTeam({ team_id: 9, points: [] });
    expect(buildSeriesSourcePoints(team, null)).toEqual([]);
  });

  it("uses shared earliest first-match date as baseline", () => {
    const teams = [
      makeTeam({
        team_id: 1,
        points: [
          {
            match_id: 1,
            round_number: 1,
            played_at: "2025-08-10T17:00:00",
            rating: 1500,
          },
        ],
      }),
      makeTeam({
        team_id: 2,
        points: [
          {
            match_id: 2,
            round_number: 1,
            played_at: "2025-08-01T17:00:00",
            rating: 1500,
          },
        ],
      }),
    ];
    expect(seasonBaselineIso(teams, null)).toBe("2025-08-01T17:00:00");
  });

  it("expands flat rating extent", () => {
    const teams = [
      makeTeam({ team_id: 1, start_rating: 1500, current_rating: 1500 }),
    ];
    const extent = computeRatingExtent(teams, null);
    expect(extent.max).toBeGreaterThan(extent.min);
  });

  it("spreads colliding end-label ratings", () => {
    expect(resolveEndLabelYs([1600, 1595, 1590], 10)).toEqual([
      1600, 1590, 1580,
    ]);
  });
});

describe("buildRatingProgressChartModel", () => {
  it("builds SVG paths and end labels for selected teams", () => {
    const teams = [
      makeTeam({
        team_id: 1,
        team_shortcut: "LEG",
        start_rating: 1500,
        current_rating: 1580,
        change: 80,
        current_rank: 1,
        points: [
          {
            match_id: 1,
            round_number: 1,
            played_at: "2025-08-01T17:00:00",
            rating: 1540,
          },
          {
            match_id: 2,
            round_number: 2,
            played_at: "2025-08-08T17:00:00",
            rating: 1580,
          },
        ],
      }),
      makeTeam({
        team_id: 2,
        team_shortcut: "WIS",
        start_rating: 1500,
        current_rating: 1460,
        change: -40,
        current_rank: 2,
        points: [
          {
            match_id: 3,
            round_number: 1,
            played_at: "2025-08-01T17:00:00",
            rating: 1480,
          },
          {
            match_id: 4,
            round_number: 2,
            played_at: "2025-08-08T17:00:00",
            rating: 1460,
          },
        ],
      }),
    ];

    const model = buildRatingProgressChartModel(teams);
    expect(model.series).toHaveLength(2);
    expect(model.series[0]?.pathD.startsWith("M ")).toBe(true);
    expect(model.series[0]?.points[0]?.isBaseline).toBe(true);
    expect(model.series[0]?.endLabel?.text).toContain("LEG");
    expect(model.yTicks.length).toBeGreaterThan(0);
    expect(model.xTicks.length).toBeGreaterThan(0);
  });

  it("handles teams with missing points without crashing", () => {
    const model = buildRatingProgressChartModel([
      makeTeam({ team_id: 1, points: [] }),
    ]);
    expect(model.series).toHaveLength(1);
    expect(model.series[0]?.pathD).toBe("");
    expect(model.series[0]?.endLabel).toBeNull();
  });
});
