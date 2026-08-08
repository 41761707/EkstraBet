import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ProjectedSeasonStandingsContent } from "@/components/leagues/ProjectedSeasonStandingsSection";
import { ProjectedSeasonStandingsTable } from "@/components/leagues/ProjectedSeasonStandingsTable";
import {
  formatProjectionPoints,
  shouldFetchSeasonProjection,
  sortStandingsByExpectedPosition,
} from "@/components/leagues/projectedSeasonStandingsModel";
import type {
  SeasonProjectionResponse,
  SeasonProjectionStandingRow,
} from "@/types/api";

function standing(
  overrides: Partial<SeasonProjectionStandingRow> &
    Pick<SeasonProjectionStandingRow, "team_id" | "team_name">,
): SeasonProjectionStandingRow {
  return {
    current_position: 1,
    current_points: 10,
    expected_position: 1.5,
    most_likely_position: 1,
    position_min: 1,
    position_max: 3,
    expected_points: 42.5,
    points_variance: 4,
    points_stddev: 2,
    points_p05: 38,
    points_p50: 42,
    points_p95: 47,
    points_min: 30,
    points_max: 55,
    expected_goal_difference: 8,
    position_probabilities: [0.5, 0.3, 0.2],
    ...overrides,
  };
}

function sampleResponse(
  overrides: Partial<SeasonProjectionResponse> = {},
): SeasonProjectionResponse {
  return {
    league_id: 1,
    season_id: 13,
    mode: "from_now",
    generated_at: "2026-08-08T12:00:00Z",
    model_name: "FOOTBALL_GOALS_POISSON_V1",
    model_version: "1.0.0",
    n_trials: 2000,
    fixed_matches: 90,
    simulated_matches: 216,
    is_stale: false,
    standings: [
      standing({
        team_id: 2,
        team_name: "Beta",
        expected_position: 2.1,
        most_likely_position: 2,
        expected_points: 40,
      }),
      standing({
        team_id: 1,
        team_name: "Alpha",
        expected_position: 1.2,
        most_likely_position: 1,
        expected_points: 48,
      }),
    ],
    ...overrides,
  };
}

describe("projectedSeasonStandingsModel", () => {
  it("does not fetch before the expander is open", () => {
    expect(shouldFetchSeasonProjection(false, false)).toBe(false);
    expect(shouldFetchSeasonProjection(false, true)).toBe(false);
  });

  it("fetches only on first open without cached data", () => {
    expect(shouldFetchSeasonProjection(true, false)).toBe(true);
    expect(shouldFetchSeasonProjection(true, true)).toBe(false);
  });

  it("sorts standings by expected_position then team_id", () => {
    const sorted = sortStandingsByExpectedPosition([
      standing({
        team_id: 3,
        team_name: "C",
        expected_position: 2,
      }),
      standing({
        team_id: 1,
        team_name: "A",
        expected_position: 1,
      }),
      standing({
        team_id: 2,
        team_name: "B",
        expected_position: 2,
      }),
    ]);
    expect(sorted.map((row) => row.team_id)).toEqual([1, 2, 3]);
  });

  it("formats points", () => {
    expect(formatProjectionPoints(42.56)).toBe("42.6");
  });
});

describe("ProjectedSeasonStandingsTable", () => {
  it("renders # as expected_position aligned with sort order", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsTable, {
        standings: [
          standing({
            team_id: 2,
            team_name: "Beta",
            expected_position: 2.4,
            most_likely_position: 1,
            expected_points: 40,
          }),
          standing({
            team_id: 1,
            team_name: "Alpha",
            expected_position: 1.2,
            most_likely_position: 3,
            expected_points: 48,
          }),
        ],
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html.indexOf("Alpha")).toBeLessThan(html.indexOf("Beta"));
    expect(html.indexOf("1.2")).toBeLessThan(html.indexOf("2.4"));
    expect(html).toContain("xPts");
    expect(html).toContain("P05–P95");
    expect(html).toContain("48.0");
    expect(html).toContain("40.0");
  });
});

describe("ProjectedSeasonStandingsContent", () => {
  it("renders loading state", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: true,
        error: null,
        isNotFound: false,
        data: null,
        leagueId: 1,
        seasonId: 13,
      }),
    );
    expect(html).toContain("Ładowanie projekcji sezonu");
  });

  it("renders empty/404 state", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: true,
        data: null,
        leagueId: 1,
        seasonId: 13,
      }),
    );
    expect(html).toContain("Brak gotowej projekcji");
  });

  it("renders error state", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: "timeout",
        isNotFound: false,
        data: null,
        leagueId: 1,
        seasonId: 13,
      }),
    );
    expect(html).toContain("Nie udało się pobrać projekcji");
    expect(html).toContain("timeout");
  });

  it("renders stale banner and success content", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse({ is_stale: true }),
        leagueId: 1,
        seasonId: 13,
      }),
    );
    expect(html).toContain("Dane mogą być nieaktualne");
    expect(html).toContain("P05–P95 to stabilniejszy zakres");
    expect(html).toContain("Alpha");
    expect(html).toContain("2000");
  });

  it("renders idle hint before open fetch", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: null,
        leagueId: 1,
        seasonId: 13,
      }),
    );
    expect(html).toContain("Otwórz sekcję, aby pobrać projekcję");
  });
});
