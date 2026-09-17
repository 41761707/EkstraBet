import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  ProjectionColumnLegend,
  ProjectionOutcomesLegend,
  ProjectedSeasonStandingsContent,
} from "@/components/leagues/ProjectedSeasonStandingsSection";
import { ProjectedSeasonOutcomesTable } from "@/components/leagues/ProjectedSeasonOutcomesTable";
import {
  ProjectedPositionChance,
  ProjectedPositionChanceList,
  ProjectedSeasonStandingsTable,
} from "@/components/leagues/ProjectedSeasonStandingsTable";
import {
  availableSeasonProjectionModes,
  defaultSeasonProjectionMode,
  formatProjectionPoints,
  hasAnyProjectionMode,
  probabilityForTablePosition,
  PROJECTION_VIEW_LABELS,
  shouldFetchProjectionModes,
  shouldFetchSeasonProjection,
  shouldShowBotColumn,
  shouldShowTopColumn,
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
    champion_probability: 0.5,
    top_probability: null,
    bot_probability: null,
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
    special_slots: null,
    standings: [
      standing({
        team_id: 2,
        team_name: "Beta",
        expected_position: 2.1,
        most_likely_position: 2,
        expected_points: 40,
        current_points: 12,
      }),
      standing({
        team_id: 1,
        team_name: "Alpha",
        expected_position: 1.2,
        most_likely_position: 1,
        expected_points: 48,
        current_points: 18,
      }),
    ],
    ...overrides,
  };
}

const bothModes = { from_now: true, from_season_start: true };

describe("projectedSeasonStandingsModel", () => {
  it("does not fetch modes before the expander is open", () => {
    expect(shouldFetchProjectionModes(false, false)).toBe(false);
    expect(shouldFetchProjectionModes(false, true)).toBe(false);
  });

  it("fetches modes only on first open", () => {
    expect(shouldFetchProjectionModes(true, false)).toBe(true);
    expect(shouldFetchProjectionModes(true, true)).toBe(false);
  });

  it("fetches projection only for a selected mode without cache", () => {
    expect(shouldFetchSeasonProjection(true, null, false)).toBe(false);
    expect(shouldFetchSeasonProjection(true, "from_now", false)).toBe(true);
    expect(shouldFetchSeasonProjection(true, "from_now", true)).toBe(false);
  });

  it("picks default mode from available flags", () => {
    expect(
      defaultSeasonProjectionMode({
        from_now: true,
        from_season_start: true,
      }),
    ).toBe("from_now");
    expect(
      defaultSeasonProjectionMode({
        from_now: false,
        from_season_start: true,
      }),
    ).toBe("from_season_start");
    expect(
      defaultSeasonProjectionMode({
        from_now: false,
        from_season_start: false,
      }),
    ).toBeNull();
  });

  it("lists only available modes", () => {
    expect(
      availableSeasonProjectionModes({
        from_now: false,
        from_season_start: true,
      }),
    ).toEqual(["from_season_start"]);
    expect(
      hasAnyProjectionMode({ from_now: false, from_season_start: false }),
    ).toBe(false);
  });

  it("reads probability for the displayed table position", () => {
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 1)).toBe(0.5);
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 2)).toBe(0.3);
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 9)).toBeNull();
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

  it("labels projection views as Punkty and Kluczowe miejsca", () => {
    expect(PROJECTION_VIEW_LABELS.points).toBe("Punkty");
    expect(PROJECTION_VIEW_LABELS.outcomes).toBe("Kluczowe miejsca");
  });

  it("shows Top and Spadek columns only when slots are positive", () => {
    expect(shouldShowTopColumn(null)).toBe(false);
    expect(shouldShowBotColumn(null)).toBe(false);
    expect(shouldShowTopColumn({ top_slots: 4, bot_slots: 3 })).toBe(true);
    expect(shouldShowBotColumn({ top_slots: 4, bot_slots: 3 })).toBe(true);
    expect(shouldShowTopColumn({ top_slots: 0, bot_slots: 3 })).toBe(false);
    expect(shouldShowBotColumn({ top_slots: 4, bot_slots: 0 })).toBe(false);
  });
});

describe("ProjectedSeasonStandingsTable", () => {
  it("renders integer predicted rank instead of mean expected_position", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsTable, {
        standings: [
          standing({
            team_id: 2,
            team_name: "Beta",
            expected_position: 2.4,
            most_likely_position: 1,
            expected_points: 40,
            current_points: 8,
          }),
          standing({
            team_id: 1,
            team_name: "Alpha",
            expected_position: 1.2,
            most_likely_position: 3,
            expected_points: 48,
            current_points: 14,
          }),
        ],
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html.indexOf("Alpha")).toBeLessThan(html.indexOf("Beta"));
    expect(html).not.toContain("1.2");
    expect(html).not.toContain("2.4");
    expect(html).toContain("xPts");
    expect(html).toContain("P05–P95");
    expect(html).toContain("48.0");
    expect(html).toContain("40.0");
    expect(html).toContain("14");
    expect(html).toContain("8");
  });

  it("formats chance for the displayed table position", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedPositionChance, {
        tablePosition: 1,
        probability: 0.5,
      }),
    );
    expect(html).toContain("Szansa na 1. miejsce");
    expect(html).toContain("50.0%");
  });

  it("renders chance for every finishing position", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedPositionChanceList, {
        probabilities: [0.5, 0.3, 0.2],
      }),
    );
    expect(html).toContain("Szansa na 1. miejsce");
    expect(html).toContain("50.0%");
    expect(html).toContain("Szansa na 2. miejsce");
    expect(html).toContain("30.0%");
    expect(html).toContain("Szansa na 3. miejsce");
    expect(html).toContain("20.0%");
  });
});

describe("ProjectedSeasonOutcomesTable", () => {
  const ekstraklasaSlots = { top_slots: 4, bot_slots: 3 };

  function outcomeStandings(): SeasonProjectionStandingRow[] {
    return [
      standing({
        team_id: 2,
        team_name: "Beta",
        expected_position: 2.1,
        champion_probability: 0.2,
        top_probability: 0.6,
        bot_probability: 0.1,
      }),
      standing({
        team_id: 1,
        team_name: "Alpha",
        expected_position: 1.2,
        champion_probability: 0.5,
        top_probability: 0.9,
        bot_probability: 0.05,
      }),
    ];
  }

  it("renders outcome percentages and Top / Spadek headers", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonOutcomesTable, {
        standings: outcomeStandings(),
        specialSlots: ekstraklasaSlots,
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html).toContain("Mistrz");
    expect(html).toContain("Puchary (TOP 4)");
    expect(html).toContain("Spadek (BOT 3)");
    expect(html).toContain("50.0%");
    expect(html).toContain("90.0%");
    expect(html).toContain("5.0%");
    expect(html).toContain("20.0%");
    expect(html).toContain("60.0%");
    expect(html).toContain("10.0%");
    expect(html).not.toContain("xPts");
  });

  it("keeps the same team order as the points table", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonOutcomesTable, {
        standings: outcomeStandings(),
        specialSlots: ekstraklasaSlots,
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html.indexOf("Alpha")).toBeLessThan(html.indexOf("Beta"));
  });

  it("hides the Spadek column when bot_slots is 0", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonOutcomesTable, {
        standings: outcomeStandings(),
        specialSlots: { top_slots: 4, bot_slots: 0 },
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html).toContain("Mistrz");
    expect(html).toContain("Puchary (TOP 4)");
    expect(html).not.toContain("Spadek");
  });

  it("hides Top and Spadek when special_slots is null", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonOutcomesTable, {
        standings: outcomeStandings(),
        specialSlots: null,
        seasonId: 13,
        leagueId: 1,
      }),
    );
    expect(html).toContain("Mistrz");
    expect(html).toContain("50.0%");
    expect(html).not.toContain("Top ");
    expect(html).not.toContain("Spadek");
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
        modeFlags: null,
        selectedMode: null,
        onSelectMode: () => undefined,
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
        modeFlags: null,
        selectedMode: null,
        onSelectMode: () => undefined,
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
        modeFlags: null,
        selectedMode: null,
        onSelectMode: () => undefined,
      }),
    );
    expect(html).toContain("Nie udało się pobrać projekcji");
    expect(html).toContain("timeout");
  });

  it("renders legend, mode options and current points from selected run", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse({ is_stale: true }),
        leagueId: 1,
        seasonId: 13,
        modeFlags: bothModes,
        selectedMode: "from_now",
        onSelectMode: () => undefined,
      }),
    );
    expect(html).toContain("Dane mogą być nieaktualne");
    expect(html).toContain("Od ostatniej kolejki");
    expect(html).toContain("Od początku sezonu");
    expect(html).toContain("Oczekiwane punkty na koniec sezonu");
    expect(html).not.toContain("P05–P95 to stabilniejszy zakres");
    expect(html).not.toContain("Obliczono:");
    expect(html).toContain("Alpha");
    expect(html).toContain("18");
  });

  it("hides a mode option when its flag is false", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse({ mode: "from_season_start" }),
        leagueId: 1,
        seasonId: 13,
        modeFlags: { from_now: false, from_season_start: true },
        selectedMode: "from_season_start",
        onSelectMode: () => undefined,
      }),
    );
    expect(html).toContain("Od początku sezonu");
    expect(html).not.toContain("Od ostatniej kolejki");
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
        modeFlags: null,
        selectedMode: null,
        onSelectMode: () => undefined,
      }),
    );
    expect(html).toContain("Otwórz sekcję, aby pobrać projekcję");
  });

  it("renders column legend symbols", () => {
    const html = renderToStaticMarkup(createElement(ProjectionColumnLegend));
    expect(html).toContain("xPts");
    expect(html).toContain("P05–P95");
    expect(html).toContain("Min–Max");
  });

  it("defaults to the points view and shows Punkty / Kluczowe miejsca tabs under mode toggle", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse({
          special_slots: { top_slots: 4, bot_slots: 3 },
        }),
        leagueId: 1,
        seasonId: 13,
        modeFlags: bothModes,
        selectedMode: "from_now",
        onSelectMode: () => undefined,
      }),
    );
    expect(html).toContain("Punkty");
    expect(html).toContain("Kluczowe miejsca");
    expect(html).toContain("xPts");
    expect(html).toContain("Oczekiwane punkty na koniec sezonu");
    expect(html).not.toContain("Mistrz");
    expect(html).not.toContain("Top 4");
    expect(html.indexOf("Od ostatniej kolejki")).toBeLessThan(
      html.indexOf("Punkty"),
    );
  });

  it("shows Mistrz and hides xPts on the outcomes view", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse({
          special_slots: { top_slots: 4, bot_slots: 3 },
          standings: [
            standing({
              team_id: 2,
              team_name: "Beta",
              expected_position: 2.1,
              champion_probability: 0.2,
              top_probability: 0.6,
              bot_probability: 0.1,
            }),
            standing({
              team_id: 1,
              team_name: "Alpha",
              expected_position: 1.2,
              champion_probability: 0.5,
              top_probability: 0.9,
              bot_probability: 0.05,
            }),
          ],
        }),
        leagueId: 1,
        seasonId: 13,
        modeFlags: bothModes,
        selectedMode: "from_now",
        onSelectMode: () => undefined,
        view: "outcomes",
      }),
    );
    expect(html).toContain("Kluczowe miejsca");
    expect(html).toContain("Mistrz");
    expect(html).toContain("Top 4");
    expect(html).toContain("Spadek (BOT 3)");
    expect(html).toContain("50.0%");
    expect(html).toContain("1. miejsce");
    expect(html).toContain("Od ostatniej kolejki");
    expect(html).not.toContain("xPts");
    expect(html).not.toContain("Oczekiwane punkty na koniec sezonu");
    expect(html).not.toContain("puchary europejskie");
  });

  it("keeps the Kluczowe miejsca tab with only Mistrz when special_slots is null", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectedSeasonStandingsContent, {
        loading: false,
        error: null,
        isNotFound: false,
        data: sampleResponse(),
        leagueId: 1,
        seasonId: 13,
        modeFlags: bothModes,
        selectedMode: "from_now",
        onSelectMode: () => undefined,
        view: "outcomes",
      }),
    );
    expect(html).toContain("Kluczowe miejsca");
    expect(html).toContain("Mistrz");
    expect(html).not.toContain("Top ");
    expect(html).not.toContain("Spadek");
    expect(html).not.toContain("xPts");
  });

  it("renders outcomes legend for visible slot columns", () => {
    const html = renderToStaticMarkup(
      createElement(ProjectionOutcomesLegend, {
        slots: { top_slots: 4, bot_slots: 3 },
      }),
    );
    expect(html).toContain("grid-cols-3");
    expect(html).toContain("Mistrz");
    expect(html).toContain("1. miejsce");
    expect(html).toContain("Top 4");
    expect(html).toContain("puchary albo awans");
    expect(html).toContain("Spadek (BOT 3)");
    expect(html).toContain("ostatnie 3 miejsca");
  });
});
