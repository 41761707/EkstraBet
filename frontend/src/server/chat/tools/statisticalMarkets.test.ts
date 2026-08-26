import { describe, expect, it } from "vitest";

import type {
  FootballPlayerMatchStat,
  TeamProfile,
  TeamSeasonMatchPoint,
  TeamSummary,
} from "@/types/api";
import type { ParsedMarket } from "@/server/chat/tools/markets";
import {
  assessPlayerMarket,
  assessTeamMarket,
  buildStatisticalCandidates,
} from "@/server/chat/tools/statisticalMarkets";

function makeTeam(id: number, name: string): TeamSummary {
  return {
    id,
    name,
    shortcut: name.slice(0, 3).toUpperCase(),
    country_id: null,
    country_name: null,
    country_emoji: null,
    sport_id: 1,
    sport_name: "Piłka nożna",
  };
}

function makeMatchPoint(
  overrides: Partial<TeamSeasonMatchPoint> & {
    team_value: number;
    opponent_value: number;
    total_value: number;
    stat?: "goals" | "shots_on_target";
  },
): TeamSeasonMatchPoint {
  const stat = overrides.stat ?? "shots_on_target";
  const base: TeamSeasonMatchPoint = {
    match_id: overrides.match_id ?? 1,
    match_date: "2026-01-01",
    opponent_shortcut: "OPP",
    opponent_name: "Opponent",
    total_goals: 0,
    btts: false,
    result: "W",
    home_team_name: "Home",
    away_team_name: "Away",
    home_goals: 0,
    away_goals: 0,
    is_home: overrides.is_home ?? true,
    team_cards: 0,
    opponent_cards: 0,
    total_cards: 0,
    team_offsides: 0,
    opponent_offsides: 0,
    total_offsides: 0,
    team_corners: 0,
    opponent_corners: 0,
    total_corners: 0,
    team_shots: 0,
    opponent_shots: 0,
    total_shots: 0,
    team_shots_on_target: 0,
    opponent_shots_on_target: 0,
    total_shots_on_target: 0,
    team_fouls: 0,
    opponent_fouls: 0,
    total_fouls: 0,
  };

  if (stat === "goals") {
    if (base.is_home) {
      base.home_goals = overrides.team_value;
      base.away_goals = overrides.opponent_value;
    } else {
      base.away_goals = overrides.team_value;
      base.home_goals = overrides.opponent_value;
    }
    base.total_goals = overrides.total_value;
    return { ...base, ...overrides };
  }

  return {
    ...base,
    ...overrides,
    team_shots_on_target: overrides.team_value,
    opponent_shots_on_target: overrides.opponent_value,
    total_shots_on_target: overrides.total_value,
  };
}

function makeProfile(
  team: TeamSummary,
  matches: TeamSeasonMatchPoint[],
): TeamProfile {
  return {
    team,
    season_id: 1,
    league_id: 1,
    form: [],
    recent_matches: [],
    overall_stats: {
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_conceded: 0,
      goal_difference: 0,
      points: 0,
    },
    home_stats: {
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_conceded: 0,
      goal_difference: 0,
      points: 0,
    },
    away_stats: {
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_conceded: 0,
      goal_difference: 0,
      points: 0,
    },
    season_matches: matches,
    head_to_head: null,
  };
}

function seriesOf(
  values: Array<{ for: number; against: number; total: number }>,
  stat: "goals" | "shots_on_target" = "shots_on_target",
): TeamSeasonMatchPoint[] {
  return values.map((entry, index) =>
    makeMatchPoint({
      match_id: index + 1,
      team_value: entry.for,
      opponent_value: entry.against,
      total_value: entry.total,
      is_home: index % 2 === 0,
      stat,
    }),
  );
}

describe("assessTeamMarket", () => {
  const strongFor = seriesOf([
    { for: 5, against: 1, total: 8 },
    { for: 4, against: 2, total: 7 },
    { for: 6, against: 1, total: 9 },
    { for: 5, against: 2, total: 8 },
    { for: 4, against: 1, total: 7 },
    { for: 5, against: 2, total: 9 },
    { for: 6, against: 1, total: 8 },
    { for: 4, against: 2, total: 7 },
    { for: 5, against: 1, total: 8 },
    { for: 5, against: 2, total: 9 },
  ]);

  const weakAgainst = seriesOf([
    { for: 1, against: 5, total: 8 },
    { for: 2, against: 4, total: 7 },
    { for: 1, against: 6, total: 9 },
    { for: 2, against: 5, total: 8 },
    { for: 1, against: 4, total: 7 },
    { for: 2, against: 5, total: 9 },
    { for: 1, against: 6, total: 8 },
    { for: 2, against: 4, total: 7 },
    { for: 1, against: 5, total: 8 },
    { for: 2, against: 5, total: 9 },
  ]);

  const profileA = makeProfile(makeTeam(1, "Górnik"), strongFor);
  const profileB = makeProfile(makeTeam(2, "Śląsk"), weakAgainst);

  const homeOver: ParsedMarket = {
    eventQuery: "gospodarz powyżej 3.5 strzału celnego",
    stat: "shots_on_target",
    subject: "home",
    playerQuery: null,
    direction: "over",
    line: 3.5,
  };

  it("returns positive verdict for strong home over line", () => {
    const result = assessTeamMarket(profileA, profileB, homeOver, 10);
    expect(result.verdict).toBe("positive");
    expect(result.confidence).toBe("high");
    expect(result.primary_sample_size).toBe(10);
    expect(result.opponent_sample_size).toBe(10);
    expect(result.combined_hit_rate).toBeGreaterThanOrEqual(0.65);
    expect(result.primary_hit_rate).toBeGreaterThanOrEqual(0.55);
    expect(result.opponent_hit_rate).toBeGreaterThanOrEqual(0.55);
  });

  it("supports away and total perspectives", () => {
    const away = assessTeamMarket(
      profileA,
      profileB,
      { ...homeOver, subject: "away", direction: "under", line: 3.5 },
      10,
    );
    expect(away.subject).toBe("away");
    expect(away.verdict).not.toBe("insufficient_data");

    const total = assessTeamMarket(
      profileA,
      profileB,
      {
        ...homeOver,
        subject: "total",
        direction: "over",
        line: 6.5,
      },
      10,
    );
    expect(total.subject).toBe("total");
    expect(total.combined_hit_rate).toBeGreaterThan(0);
  });

  it("counts integer-line pushes separately", () => {
    const matches = seriesOf(
      [
        { for: 2, against: 2, total: 4 },
        { for: 2, against: 2, total: 4 },
        { for: 2, against: 2, total: 4 },
        { for: 2, against: 2, total: 4 },
        { for: 2, against: 2, total: 4 },
        { for: 3, against: 1, total: 4 },
        { for: 3, against: 1, total: 4 },
        { for: 3, against: 1, total: 4 },
        { for: 3, against: 1, total: 4 },
        { for: 3, against: 1, total: 4 },
      ],
      "goals",
    );
    const result = assessTeamMarket(
      makeProfile(makeTeam(1, "A"), matches),
      makeProfile(makeTeam(2, "B"), matches),
      {
        eventQuery: "over 2 goals home",
        stat: "goals",
        subject: "home",
        playerQuery: null,
        direction: "over",
        line: 2,
      },
      10,
    );
    expect(result.push_rate).toBeGreaterThan(0);
    expect(result.verdict).not.toBe("insufficient_data");
  });

  it("returns insufficient_data for sample below 5", () => {
    const smallA = makeProfile(makeTeam(1, "A"), strongFor.slice(0, 3));
    const smallB = makeProfile(makeTeam(2, "B"), weakAgainst.slice(0, 3));
    const result = assessTeamMarket(smallA, smallB, homeOver, 10);
    expect(result.verdict).toBe("insufficient_data");
    expect(result.confidence).toBe("low");
  });

  it("uses lean/neutral/negative thresholds on combined hit rate", () => {
    const mixed = seriesOf([
      { for: 4, against: 3, total: 7 },
      { for: 2, against: 3, total: 5 },
      { for: 4, against: 2, total: 6 },
      { for: 2, against: 4, total: 6 },
      { for: 4, against: 3, total: 7 },
      { for: 2, against: 3, total: 5 },
      { for: 4, against: 2, total: 6 },
      { for: 2, against: 4, total: 6 },
      { for: 4, against: 3, total: 7 },
      { for: 2, against: 3, total: 5 },
    ]);
    const result = assessTeamMarket(
      makeProfile(makeTeam(1, "A"), mixed),
      makeProfile(makeTeam(2, "B"), mixed),
      homeOver,
      10,
    );
    expect(["lean_positive", "neutral", "lean_negative", "positive", "negative"]).toContain(
      result.verdict,
    );
  });
});

describe("assessPlayerMarket", () => {
  function playerMatches(values: number[]): FootballPlayerMatchStat[] {
    return values.map((shotsOnTarget, index) => ({
      match_id: index + 1,
      home_team: "A",
      away_team: "B",
      match_date: "2026-01-01",
      opponent_shortcut: "OPP",
      opponent_name: "Opponent",
      goals: 0,
      assists: 0,
      shots: shotsOnTarget + 1,
      shots_on_target: shotsOnTarget,
      fouls_conceded: 0,
      yellow_cards: 0,
    }));
  }

  it("computes hit rate and always warns about lineup", () => {
    const result = assessPlayerMarket(
      playerMatches([4, 5, 3, 4, 5, 4, 3, 5, 4, 4]),
      {
        eventQuery: "player over 2.5 SOT",
        stat: "shots_on_target",
        subject: "player",
        playerQuery: "Kownacki",
        direction: "over",
        line: 2.5,
      },
      10,
    );
    expect(result.verdict).not.toBe("insufficient_data");
    expect(result.opponent_hit_rate).toBeNull();
    expect(result.combined_hit_rate).toBe(result.primary_hit_rate);
    expect(result.warnings[0]).toMatch(/nie potwierdza obecności/);
  });

  it("returns insufficient_data below 5 appearances", () => {
    const result = assessPlayerMarket(
      playerMatches([4, 5, 3]),
      {
        eventQuery: "player over 2.5",
        stat: "shots_on_target",
        subject: "player",
        playerQuery: "X",
        direction: "over",
        line: 2.5,
      },
    );
    expect(result.verdict).toBe("insufficient_data");
    expect(result.warnings.some((warning) => /składzie/.test(warning))).toBe(
      true,
    );
  });
});

describe("buildStatisticalCandidates", () => {
  it("returns non-contradictory football candidates without odds", () => {
    const strong = seriesOf([
      { for: 5, against: 1, total: 10 },
      { for: 6, against: 2, total: 11 },
      { for: 5, against: 1, total: 9 },
      { for: 4, against: 2, total: 10 },
      { for: 5, against: 1, total: 12 },
      { for: 6, against: 2, total: 11 },
      { for: 5, against: 1, total: 10 },
      { for: 4, against: 2, total: 9 },
      { for: 5, against: 1, total: 11 },
      { for: 6, against: 2, total: 12 },
    ]);
    const soft = seriesOf([
      { for: 1, against: 5, total: 10 },
      { for: 2, against: 6, total: 11 },
      { for: 1, against: 5, total: 9 },
      { for: 2, against: 4, total: 10 },
      { for: 1, against: 5, total: 12 },
      { for: 2, against: 6, total: 11 },
      { for: 1, against: 5, total: 10 },
      { for: 2, against: 4, total: 9 },
      { for: 1, against: 5, total: 11 },
      { for: 2, against: 6, total: 12 },
    ]);

    const candidates = buildStatisticalCandidates(
      makeProfile(makeTeam(1, "Górnik"), strong),
      makeProfile(makeTeam(2, "Śląsk"), soft),
      { sportId: 1, limit: 10 },
    );

    expect(candidates.length).toBeGreaterThan(0);
    const stats = candidates.map((candidate) => candidate.stat);
    expect(new Set(stats).size).toBe(stats.length);
    for (const candidate of candidates) {
      expect(candidate.confidence).not.toBe("low");
      expect(candidate.combined_hit_rate).toBeGreaterThanOrEqual(0.6);
      expect(candidate.combined_hit_rate).toBeLessThanOrEqual(0.9);
      expect(candidate.label).toMatch(/zdarzenie statystyczne/);
    }
  });

  it("does not auto-generate candidates for non-football sports", () => {
    const profile = makeProfile(makeTeam(1, "A"), []);
    expect(
      buildStatisticalCandidates(profile, profile, { sportId: 2 }),
    ).toEqual([]);
  });
});
