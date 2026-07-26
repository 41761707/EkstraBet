import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  BetRecommendation,
  MatchDetails,
  MatchPredictionItem,
  MatchSummary,
  OddsItem,
  TeamProfile,
  TeamSeasonMatchPoint,
  TeamSummary,
} from "@/types/api";

vi.mock("@/server/chat/tools/http", () => ({
  fetchReadOnly: vi.fn(),
  getEndpoint: (path: string) => `GET ${path}`,
  buildUrl: (path: string) => `http://localhost:8000${path}`,
}));

import { fetchReadOnly } from "@/server/chat/tools/http";
import {
  addIsoCalendarDays,
  analyzeMatchBet,
  computeEv,
  computeEvAfterTax,
  findMatchOpportunities,
  getWarsawDateIso,
  listMarketOpportunities,
  matchEventByQuery,
  parseMarketQuery,
  pickBestOdds,
} from "@/server/chat/tools/markets";
import { searchMatches } from "@/server/chat/tools/matches";
import type { MarketOpportunity } from "@/types/api";

const mockedFetch = vi.mocked(fetchReadOnly);

afterEach(() => {
  mockedFetch.mockReset();
});

describe("computeEv / computeEvAfterTax", () => {
  it("computes known EV values", () => {
    expect(computeEv(0.55, 2.0)).toBeCloseTo(0.1, 8);
    expect(computeEvAfterTax(0.55, 2.0, 0.12)).toBeCloseTo(-0.032, 8);
  });
});

describe("parseMarketQuery", () => {
  it("parses Polish over goals total market", () => {
    const parsed = parseMarketQuery("Powyżej 2.5 gola");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(2.5);
    expect(parsed.stat).toBe("goals");
    expect(parsed.subject).toBe("total");
  });

  it("parses under shots on target for home", () => {
    const parsed = parseMarketQuery(
      "Poniżej 3.5 strzału celnego gospodarza",
    );
    expect(parsed.direction).toBe("under");
    expect(parsed.line).toBe(3.5);
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.subject).toBe("home");
  });

  it("maps strzały na bramkę to shots_on_target", () => {
    const parsed = parseMarketQuery("Over 4.5 strzałów na bramkę gościa");
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.subject).toBe("away");
    expect(parsed.direction).toBe("over");
  });

  it("does not guess subject for team name without home/away/total", () => {
    const parsed = parseMarketQuery(
      "Górnik powyżej 3.5 strzału celnego",
    );
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("does not treat two-word club name as player", () => {
    const parsed = parseMarketQuery(
      "Górnik Zabrze powyżej 3.5 strzału celnego",
    );
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("does not treat Legia Warszawa as player for team market", () => {
    const parsed = parseMarketQuery(
      "Legia Warszawa powyżej 9.5 rożnych",
    );
    expect(parsed.stat).toBe("corners");
    expect(parsed.subject).toBeNull();
    expect(parsed.playerQuery).toBeNull();
  });

  it("detects player prop from surname before direction", () => {
    const parsed = parseMarketQuery("Lewandowski powyżej 0.5 gola");
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("goals");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(0.5);
  });

  it("detects full player name before direction", () => {
    const parsed = parseMarketQuery("Robert Lewandowski over 0.5 goals");
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Robert Lewandowski");
  });

  it("keeps clean playerQuery with explicit zawodnik and SOT market", () => {
    const parsed = parseMarketQuery(
      "zawodnik Lewandowski powyżej 3.5 strzału celnego",
    );
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("shots_on_target");
    expect(parsed.direction).toBe("over");
    expect(parsed.line).toBe(3.5);
  });

  it("parses player prop from structured args with text fallback", () => {
    const parsed = parseMarketQuery("Lewandowski powyżej 0.5 gola", {
      subject: "player",
      playerQuery: "Lewandowski",
      stat: "goals",
      direction: "over",
      line: 0.5,
    });
    expect(parsed.subject).toBe("player");
    expect(parsed.playerQuery).toBe("Lewandowski");
    expect(parsed.stat).toBe("goals");
    expect(parsed.line).toBe(0.5);
  });

  it("lets structured args override ambiguous text", () => {
    const parsed = parseMarketQuery("coś niejasnego", {
      stat: "corners",
      subject: "total",
      direction: "under",
      line: 9.5,
    });
    expect(parsed.stat).toBe("corners");
    expect(parsed.direction).toBe("under");
    expect(parsed.line).toBe(9.5);
    expect(parsed.subject).toBe("total");
  });

  it("leaves ambiguous fields null instead of guessing", () => {
    const parsed = parseMarketQuery("ciekawy rynek");
    expect(parsed.stat).toBeNull();
    expect(parsed.direction).toBeNull();
    expect(parsed.line).toBeNull();
    expect(parsed.subject).toBeNull();
  });
});

describe("matchEventByQuery", () => {
  const events = [
    { event_id: 8, event_name: "Powyżej 2.5 gola" },
    { event_id: 12, event_name: "Poniżej 2.5 gola" },
    { event_id: 6, event_name: "Obie strzelą" },
  ];

  it("prefers exact and fuller matches", () => {
    const matched = matchEventByQuery(events, "Powyżej 2.5 gola");
    expect(matched[0]?.event_id).toBe(8);
    expect(matched[0]?.isComplementary).toBe(false);
  });

  it("matches partial query preferring longer overlap", () => {
    const matched = matchEventByQuery(events, "powyżej 2.5");
    expect(matched[0]?.event_id).toBe(8);
  });

  it("returns complementary Over when only Under side is missing", () => {
    const onlyOver = [{ event_id: 8, event_name: "Powyżej 2.5 gola" }];
    const matched = matchEventByQuery(onlyOver, "Poniżej 2.5 gola");
    expect(matched).toHaveLength(1);
    expect(matched[0]?.event_id).toBe(8);
    expect(matched[0]?.isComplementary).toBe(true);
    expect(matched[0]?.askedEventId).toBe(12);
  });
});

describe("pickBestOdds", () => {
  it("returns max odds for event", () => {
    const best = pickBestOdds(
      [
        {
          event_id: 8,
          odds: 1.9,
          bookmaker_id: 1,
          bookmaker_name: "A",
        },
        {
          event_id: 8,
          odds: 2.15,
          bookmaker_id: 2,
          bookmaker_name: "B",
        },
        {
          event_id: 12,
          odds: 3.0,
          bookmaker_id: 2,
          bookmaker_name: "B",
        },
      ],
      8,
    );
    expect(best).toEqual({
      bookmaker_id: 2,
      bookmaker_name: "B",
      odds: 2.15,
    });
  });
});

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

function makeMatchDetails(
  overrides?: Partial<MatchDetails>,
): MatchDetails {
  return {
    id: 119435,
    league_id: 1,
    season_id: 10,
    sport_id: 1,
    round: 1,
    round_label: "1",
    game_date: "2026-07-28T18:00:00",
    home_team: { id: 1, name: "Górnik Zabrze", shortcut: "GOR" },
    away_team: { id: 2, name: "Śląsk Wrocław", shortcut: "SLA" },
    home_goals: null,
    away_goals: null,
    result: "0",
    is_played: false,
    score_resolution: null,
    final_predictions: [],
    prediction_analysis: null,
    odds: [],
    stats: null,
    hockey_stats: null,
    has_player_stats: false,
    head_to_head: {
      team_id: 1,
      opponent_id: 2,
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_conceded: 0,
      btts_count: 0,
      btts_percentage: 0,
      avg_goals_per_match: 0,
      meetings: [],
    },
    home_team_history: [],
    away_team_history: [],
    boxscore: null,
    hockey_boxscore: null,
    model_assessments: [],
    ...overrides,
  };
}

function makeSotMatch(
  teamValue: number,
  opponentValue: number,
  isHome = true,
): TeamSeasonMatchPoint {
  return {
    match_id: 1,
    match_date: "2026-01-01",
    opponent_shortcut: "OPP",
    opponent_name: "Opponent",
    total_goals: 2,
    btts: false,
    result: "W",
    home_team_name: "Home",
    away_team_name: "Away",
    home_goals: 1,
    away_goals: 1,
    is_home: isHome,
    team_cards: 0,
    opponent_cards: 0,
    total_cards: 0,
    team_offsides: 0,
    opponent_offsides: 0,
    total_offsides: 0,
    team_corners: 0,
    opponent_corners: 0,
    total_corners: 0,
    team_shots: 10,
    opponent_shots: 8,
    total_shots: 18,
    team_shots_on_target: teamValue,
    opponent_shots_on_target: opponentValue,
    total_shots_on_target: teamValue + opponentValue,
    team_fouls: 0,
    opponent_fouls: 0,
    total_fouls: 0,
  };
}

function makeProfile(
  team: TeamSummary,
  matches: TeamSeasonMatchPoint[],
): TeamProfile {
  return {
    team,
    season_id: 10,
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

function makeBet(overrides?: Partial<BetRecommendation>): BetRecommendation {
  return {
    bet_id: 1,
    match_id: 119435,
    league_id: 1,
    league_name: "Ekstraklasa",
    season_id: 10,
    game_date: "2026-07-28T18:00:00",
    home_team: { id: 1, name: "Górnik Zabrze", shortcut: "GOR" },
    away_team: { id: 2, name: "Śląsk Wrocław", shortcut: "SLA" },
    event_id: 8,
    event_name: "Powyżej 2.5 gola",
    event_family: null,
    odds: 2.1,
    probability: 0.58,
    probability_pct: 58,
    ev: 0.218,
    ev_after_tax: 0.07184,
    bookmaker_id: 1,
    bookmaker_name: "STS",
    model_id: 3,
    model_name: "OU Model",
    settlement_status: "pending",
    custom_bet: false,
    ...overrides,
  };
}

function makePrediction(
  overrides?: Partial<MatchPredictionItem>,
): MatchPredictionItem {
  return {
    prediction_id: 1,
    event_id: 8,
    event_name: "Powyżej 2.5 gola",
    event_family: null,
    model_id: 3,
    model_name: "OU Model",
    value: 0.58,
    outcome: null,
    ...overrides,
  };
}

function makeOdds(overrides?: Partial<OddsItem>): OddsItem {
  return {
    id: 1,
    match_id: 119435,
    bookmaker_id: 1,
    bookmaker_name: "STS",
    event_id: 8,
    event_name: "Powyżej 2.5 gola",
    event_family: null,
    odds: 2.1,
    ...overrides,
  };
}

function strongSotMatches(value: number): TeamSeasonMatchPoint[] {
  return Array.from({ length: 10 }, () => makeSotMatch(value, 2));
}

/** Serie z hit rate w zakresie 0.6–0.9, żeby buildStatisticalCandidates nie odrzucał kandydatów. */
function viableStatMatches(role: "strong" | "soft"): TeamSeasonMatchPoint[] {
  const strong = [
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
  ];
  const soft = [
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
  ];
  const values = role === "strong" ? strong : soft;
  return values.map((entry, index) => ({
    ...makeSotMatch(entry.for, entry.against, index % 2 === 0),
    match_id: index + 1,
    team_shots: entry.for * 2,
    opponent_shots: entry.against * 2,
    total_shots: entry.total * 2,
    team_shots_on_target: entry.for,
    opponent_shots_on_target: entry.against,
    total_shots_on_target: entry.total,
    team_corners: entry.for,
    opponent_corners: entry.against,
    total_corners: entry.total,
    home_goals: index % 2 === 0 ? Math.min(entry.for, 3) : Math.min(entry.against, 2),
    away_goals: index % 2 === 0 ? Math.min(entry.against, 2) : Math.min(entry.for, 3),
    total_goals: Math.min(entry.total, 4),
  }));
}

function makeGoalsMatch(
  teamValue: number,
  opponentValue: number,
  isHome = true,
): TeamSeasonMatchPoint {
  return {
    ...makeSotMatch(0, 0, isHome),
    home_goals: isHome ? teamValue : opponentValue,
    away_goals: isHome ? opponentValue : teamValue,
    total_goals: teamValue + opponentValue,
  };
}

function weakGoalsMatches(): TeamSeasonMatchPoint[] {
  // niska liczba goli — słabe wsparcie dla over 2.5
  return Array.from({ length: 10 }, () => makeGoalsMatch(0, 1));
}

function strongGoalsMatches(): TeamSeasonMatchPoint[] {
  // sumy > 2.5 — wsparcie historyczne dla over 2.5
  return Array.from({ length: 10 }, () => makeGoalsMatch(2, 2));
}

function makeMatchSummary(
  overrides?: Partial<MatchSummary> & {
    id?: number;
    game_date?: string;
    home_name?: string;
    away_name?: string;
  },
): MatchSummary {
  return {
    id: overrides?.id ?? 119435,
    league_id: overrides?.league_id ?? 1,
    season_id: overrides?.season_id ?? 10,
    round: overrides?.round ?? 1,
    round_label: overrides?.round_label ?? "1",
    game_date: overrides?.game_date ?? "2099-07-28T18:00:00",
    home_team: overrides?.home_team ?? {
      id: 1,
      name: overrides?.home_name ?? "Górnik Zabrze",
      shortcut: "GOR",
    },
    away_team: overrides?.away_team ?? {
      id: 2,
      name: overrides?.away_name ?? "Śląsk Wrocław",
      shortcut: "SLA",
    },
    home_goals: overrides?.home_goals ?? null,
    away_goals: overrides?.away_goals ?? null,
    result: overrides?.result ?? "0",
    is_played: overrides?.is_played ?? false,
    score_resolution: overrides?.score_resolution ?? null,
  };
}

/**
 * Route mock responses by path for analyze_match_bet parallel fetches.
 */
function mockAnalyzeSources(params: {
  details?: MatchDetails;
  bets?: BetRecommendation[];
  predictions?: MatchPredictionItem[];
  odds?: OddsItem[];
  profileHome?: TeamProfile;
  profileAway?: TeamProfile;
  searchMatches?: MatchSummary[];
  searchFallbackMatches?: MatchSummary[];
}) {
  const details = params.details ?? makeMatchDetails();
  const home = makeTeam(1, "Górnik Zabrze");
  const away = makeTeam(2, "Śląsk Wrocław");
  let searchCalls = 0;

  mockedFetch.mockImplementation(async (path: string, requestParams?) => {
    if (path === "/matches/search") {
      searchCalls += 1;
      const played = requestParams?.played;
      if (searchCalls === 1 && played === false) {
        return {
          matches: params.searchMatches ?? [],
          total_count: (params.searchMatches ?? []).length,
          filters_applied: {},
        };
      }
      return {
        matches: params.searchFallbackMatches ?? params.searchMatches ?? [],
        total_count: (
          params.searchFallbackMatches ??
          params.searchMatches ??
          []
        ).length,
        filters_applied: {},
      };
    }
    if (path.includes("/matches/") && path.endsWith("/details")) {
      return details;
    }
    if (path === "/bets/recommendations") {
      return {
        recommendations: params.bets ?? [],
        total_count: (params.bets ?? []).length,
        filters_applied: {},
      };
    }
    if (path.startsWith("/predictions/match/")) {
      return {
        match_predictions: params.predictions ?? [],
        total_count: (params.predictions ?? []).length,
        match_id: details.id,
      };
    }
    if (path.startsWith("/odds/match/")) {
      return {
        odds: params.odds ?? [],
        total_count: (params.odds ?? []).length,
        match_id: details.id,
      };
    }
    if (path.startsWith("/teams/") && path.endsWith("/profile")) {
      const teamId = Number(path.split("/")[2]);
      if (teamId === details.home_team.id || teamId === 1) {
        return (
          params.profileHome ??
          makeProfile(home, strongGoalsMatches())
        );
      }
      return (
        params.profileAway ??
        makeProfile(away, strongGoalsMatches())
      );
    }
    throw new Error(`Unexpected fetch path: ${path}`);
  });
}

describe("analyze_match_bet", () => {
  it("happy path with bets, prediction, odds and matching stats", async () => {
    mockAnalyzeSources({
      bets: [makeBet()],
      predictions: [makePrediction()],
      odds: [makeOdds()],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        strongGoalsMatches(),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        strongGoalsMatches(),
      ),
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Powyżej 2.5 gola",
      subject: "total",
      stat: "goals",
      direction: "over",
      line: 2.5,
      apply_tax: true,
      sport_id: 1,
    });

    expect(result.name).toBe("analyze_match_bet");
    expect(result.data).toMatchObject({
      verdict_basis: "value",
      primary_evidence_source: "bet",
      odds_available: true,
      probability: 0.58,
      best_odds: 2.1,
    });
    const data = result.data as {
      supporting_evidence: Array<{ source: string; label: string }>;
      contradicting_evidence: Array<{ source: string }>;
      available_evidence_sources: string[];
      verdict: string;
      ev: number;
      ev_after_tax: number;
      statistical: { combined_hit_rate: number } | null;
    };
    expect(data.available_evidence_sources).toEqual(
      expect.arrayContaining(["bet", "prediction", "statistics"]),
    );
    expect(data.ev).toBeCloseTo(0.58 * 2.1 - 1, 5);
    expect(data.ev_after_tax).toBeCloseTo(0.58 * 2.1 * 0.88 - 1, 5);
    expect(data.verdict).toBe("lean_positive");
    expect(data.statistical?.combined_hit_rate).toBeGreaterThan(0.55);
    expect(
      data.supporting_evidence.some((item) => item.source === "bet"),
    ).toBe(true);
    expect(
      data.contradicting_evidence.some((item) => item.source === "statistics"),
    ).toBe(false);
  });

  it("puts negative-EV bet record into contradicting_evidence", async () => {
    mockAnalyzeSources({
      bets: [
        makeBet({
          probability: 0.4,
          odds: 1.8,
          ev: 0.4 * 1.8 - 1,
          ev_after_tax: 0.4 * 1.8 * 0.88 - 1,
        }),
      ],
      predictions: [makePrediction({ value: 0.4 })],
      odds: [makeOdds({ odds: 1.8 })],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        strongGoalsMatches(),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        strongGoalsMatches(),
      ),
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Powyżej 2.5 gola",
      subject: "total",
      stat: "goals",
      direction: "over",
      line: 2.5,
      apply_tax: true,
      sport_id: 1,
    });

    const data = result.data as {
      supporting_evidence: Array<{ source: string; label: string }>;
      contradicting_evidence: Array<{ source: string; label: string }>;
    };
    expect(
      data.supporting_evidence.some((item) => item.source === "bet"),
    ).toBe(false);
    expect(
      data.contradicting_evidence.some(
        (item) =>
          item.source === "bet" &&
          item.label.includes("ujemny/zerowy EV"),
      ),
    ).toBe(true);
  });

  it("resolves a single match via team name search", async () => {
    const match = makeMatchSummary();
    mockAnalyzeSources({
      searchMatches: [match],
      bets: [makeBet()],
      predictions: [makePrediction()],
      odds: [makeOdds()],
    });

    const result = await analyzeMatchBet({
      team_a_query: "Górnik Zabrze",
      team_b_query: "Śląsk Wrocław",
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    expect(result.data).toMatchObject({
      match_id: 119435,
      primary_evidence_source: "bet",
    });
    expect(
      mockedFetch.mock.calls.some(
        (call) =>
          call[0] === "/matches/search" &&
          call[1]?.played === false,
      ),
    ).toBe(true);
    expect(
      result.warnings.some((warning) => /Znaleziono \d+ meczów/i.test(warning)),
    ).toBe(false);
  });

  it("warns when multiple matches are found and picks the nearest", async () => {
    mockAnalyzeSources({
      searchMatches: [
        makeMatchSummary({
          id: 100,
          game_date: "2099-08-10T18:00:00",
        }),
        makeMatchSummary({
          id: 200,
          game_date: "2099-07-28T18:00:00",
        }),
      ],
      bets: [makeBet({ match_id: 200 })],
      predictions: [makePrediction()],
      odds: [makeOdds({ match_id: 200 })],
    });

    const result = await analyzeMatchBet({
      team_a_query: "Górnik",
      team_b_query: "Śląsk",
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    expect(result.data).toMatchObject({ match_id: 200 });
    expect(
      result.warnings.some((warning) =>
        /Znaleziono 2 meczów — użyłem najbliższego/i.test(warning),
      ),
    ).toBe(true);
  });

  it("falls back when played=false search is empty", async () => {
    mockAnalyzeSources({
      searchMatches: [],
      searchFallbackMatches: [
        makeMatchSummary({
          id: 300,
          game_date: "2026-01-15T18:00:00",
          is_played: true,
          result: "1",
        }),
      ],
      bets: [makeBet({ match_id: 300 })],
      predictions: [makePrediction()],
      odds: [makeOdds({ match_id: 300 })],
    });

    const result = await analyzeMatchBet({
      team_a_query: "Górnik Zabrze",
      team_b_query: "Śląsk Wrocław",
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    expect(result.data).toMatchObject({ match_id: 300 });
    expect(
      result.warnings.some((warning) =>
        /Brak nadchodzącego meczu nierozegnanego/i.test(warning),
      ),
    ).toBe(true);
    const searchCalls = mockedFetch.mock.calls.filter(
      (call) => call[0] === "/matches/search",
    );
    expect(searchCalls.length).toBeGreaterThanOrEqual(2);
    expect(searchCalls[0]?.[1]).toMatchObject({ played: false });
    expect(searchCalls[1]?.[1]).toMatchObject({ from_now: false });
  });

  it("softens verdict when positive EV conflicts with weak statistics", async () => {
    mockAnalyzeSources({
      bets: [makeBet({ probability: 0.6, odds: 2.2, ev: 0.32 })],
      predictions: [makePrediction({ value: 0.6 })],
      odds: [makeOdds({ odds: 2.2 })],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        weakGoalsMatches(),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        weakGoalsMatches(),
      ),
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Powyżej 2.5 gola",
      subject: "total",
      stat: "goals",
      direction: "over",
      line: 2.5,
      sport_id: 1,
    });

    const data = result.data as {
      verdict: string;
      contradicting_evidence: unknown[];
      verdict_basis: string;
    };
    expect(data.verdict_basis).toBe("value");
    expect(["neutral", "lean_positive", "lean_negative"]).toContain(
      data.verdict,
    );
    expect(data.contradicting_evidence.length).toBeGreaterThan(0);
  });

  it("uses prediction + odds when bets are empty", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [makePrediction({ value: 0.62 })],
      odds: [makeOdds({ odds: 1.95 })],
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    const data = result.data as {
      primary_evidence_source: string;
      verdict_basis: string;
      odds_available: boolean;
      probability: number;
      ev: number | null;
    };
    expect(data.primary_evidence_source).toBe("prediction");
    expect(data.verdict_basis).toBe("value");
    expect(data.odds_available).toBe(true);
    expect(data.probability).toBe(0.62);
    expect(data.ev).not.toBeNull();
  });

  it("returns probability verdict without odds and keeps ev null", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [makePrediction({ value: 0.7 })],
      odds: [],
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    const data = result.data as {
      verdict_basis: string;
      verdict: string;
      odds_available: boolean;
      ev: number | null;
      ev_after_tax: number | null;
      probability: number;
    };
    expect(data.verdict_basis).toBe("probability");
    expect(data.odds_available).toBe(false);
    expect(data.ev).toBeNull();
    expect(data.ev_after_tax).toBeNull();
    expect(data.probability).toBe(0.7);
    expect(data.verdict).toBe("positive");
    expect(result.warnings.some((w) => /value bet|Brak kursu/i.test(w))).toBe(
      true,
    );
  });

  it("falls back to statistical verdict for SOT without model/odds", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [],
      odds: [],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        strongSotMatches(5),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        // rywal często oddaje dużo SOT — wspiera over gospodarza
        Array.from({ length: 10 }, () => makeSotMatch(2, 5)),
      ),
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Górnik powyżej 3.5 strzału celnego",
      subject: "home",
      stat: "shots_on_target",
      direction: "over",
      line: 3.5,
      sport_id: 1,
    });

    const data = result.data as {
      verdict_basis: string;
      verdict: string;
      odds_available: boolean;
      primary_evidence_source: string;
      statistical: { combined_hit_rate: number } | null;
    };
    expect(data.verdict_basis).toBe("statistical_support");
    expect(data.primary_evidence_source).toBe("statistics");
    expect(data.odds_available).toBe(false);
    expect(data.verdict).not.toBe("insufficient_data");
    expect(data.statistical?.combined_hit_rate).toBeGreaterThan(0.5);
  });

  it("returns insufficient_data when all sources and sample are missing", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [],
      odds: [],
      profileHome: makeProfile(makeTeam(1, "Górnik Zabrze"), [
        makeSotMatch(4, 2),
      ]),
      profileAway: makeProfile(makeTeam(2, "Śląsk Wrocław"), [
        makeSotMatch(2, 4),
      ]),
    });

    const result = await analyzeMatchBet({
      match_id: 119435,
      event_query: "Górnik powyżej 3.5 strzału celnego",
      subject: "home",
      stat: "shots_on_target",
      direction: "over",
      line: 3.5,
      sport_id: 1,
    });

    const data = result.data as { verdict: string };
    expect(data.verdict).toBe("insufficient_data");
  });

  it("returns controlled empty result when match cannot be resolved", async () => {
    const result = await analyzeMatchBet({
      event_query: "Powyżej 2.5 gola",
      sport_id: 1,
    });

    expect(result.data).toBeNull();
    expect(result.warnings.length).toBeGreaterThan(0);
    expect(mockedFetch).not.toHaveBeenCalled();
  });
});

describe("getWarsawDateIso / addIsoCalendarDays", () => {
  it("formats a fixed UTC instant as Europe/Warsaw calendar date", () => {
    // 2026-07-25 22:30 UTC = 2026-07-26 in Warsaw (CEST)
    const iso = getWarsawDateIso(new Date("2026-07-25T22:30:00.000Z"));
    expect(iso).toBe("2026-07-26");
  });

  it("adds calendar days without timezone drift", () => {
    expect(addIsoCalendarDays("2026-07-26", 1)).toBe("2026-07-27");
    expect(addIsoCalendarDays("2026-07-26", 6)).toBe("2026-08-01");
  });
});

describe("search_matches", () => {
  it("calls /matches/search once and returns a table", async () => {
    const match = makeMatchSummary();
    mockedFetch.mockResolvedValue({
      matches: [match],
      total_count: 1,
      filters_applied: { warnings: [] },
    });

    const result = await searchMatches({
      team_a_query: "Górnik",
      team_b_query: "Śląsk",
      sport_id: 1,
    });

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    expect(mockedFetch).toHaveBeenCalledWith(
      "/matches/search",
      expect.objectContaining({
        team_a_query: "Górnik",
        team_b_query: "Śląsk",
        from_now: true,
        page_size: 10,
      }),
    );
    expect(result.name).toBe("search_matches");
    const data = result.data as { matches: MatchSummary[]; total_count: number };
    expect(data.matches).toHaveLength(1);
    expect(result.table?.rows).toHaveLength(1);
  });
});

describe("list_market_opportunities", () => {
  function makeOpportunity(
    overrides?: Partial<MarketOpportunity>,
  ): MarketOpportunity {
    return {
      match_id: 1,
      sport_id: 1,
      league_id: 1,
      league_name: "Ekstraklasa",
      game_date: "2026-07-26T18:00:00",
      home_team: "Legia",
      away_team: "Lech",
      event_id: 8,
      event_name: "Powyżej 2.5 gola",
      model_id: 3,
      model_name: "OU",
      probability: 0.55,
      probability_pct: 55,
      odds: 2.1,
      bookmaker_id: 1,
      bookmaker_name: "STS",
      implied_probability: 1 / 2.1,
      ev: 0.155,
      ev_after_tax: 0.0164,
      source: "bet",
      ranking_basis: "ev_after_tax",
      ...overrides,
    };
  }

  it("makes exactly one HTTP call for today scope", async () => {
    mockedFetch.mockResolvedValue({
      opportunities: [
        makeOpportunity(),
        makeOpportunity({
          match_id: 2,
          source: "prediction",
          odds: null,
          ev: null,
          ev_after_tax: null,
          ranking_basis: "probability",
          bookmaker_id: null,
          bookmaker_name: null,
          implied_probability: null,
        }),
      ],
      total_count: 2,
      filters_applied: { sport_id: 1 },
      source_counts: { bet: 1, prediction: 1 },
      warnings: ["Uzupełniono ranking predykcjami bez kursu."],
    });

    const result = await listMarketOpportunities({
      sport_id: 1,
      date_scope: "today",
    });

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    expect(mockedFetch).toHaveBeenCalledWith(
      "/bets/opportunities",
      expect.objectContaining({
        sport_id: 1,
        match_date: getWarsawDateIso(),
        from_now: true,
        positive_ev_only: true,
        apply_tax: true,
        include_prediction_fallback: true,
        one_per_match: true,
        limit: 10,
      }),
    );
    expect(result.name).toBe("list_market_opportunities");
    const data = result.data as {
      opportunities: MarketOpportunity[];
      source_counts: Record<string, number>;
    };
    expect(data.opportunities).toHaveLength(2);
    expect(data.source_counts.bet).toBe(1);
    expect(result.table?.rows.some((row) => row[0] === "predykcja bez kursu")).toBe(
      true,
    );
    expect(result.warnings.some((w) => /predykcjami/.test(w))).toBe(true);
  });

  it("returns empty list without further calls", async () => {
    mockedFetch.mockResolvedValue({
      opportunities: [],
      total_count: 0,
      filters_applied: {},
      source_counts: { bet: 0, prediction: 0 },
      warnings: [],
    });

    const result = await listMarketOpportunities({
      sport_id: 1,
      date_scope: "tomorrow",
    });

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    expect(mockedFetch.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({
        match_date: addIsoCalendarDays(getWarsawDateIso(), 1),
      }),
    );
    expect(result.summary).toMatch(/Brak opportunities/);
    const data = result.data as { opportunities: unknown[] };
    expect(data.opportunities).toHaveLength(0);
  });

  it("uses date_from/date_to for next_7_days", async () => {
    mockedFetch.mockResolvedValue({
      opportunities: [],
      total_count: 0,
      filters_applied: {},
      source_counts: {},
      warnings: [],
    });

    await listMarketOpportunities({
      sport_id: 1,
      date_scope: "next_7_days",
    });

    const today = getWarsawDateIso();
    expect(mockedFetch).toHaveBeenCalledWith(
      "/bets/opportunities",
      expect.objectContaining({
        date_from: today,
        date_to: addIsoCalendarDays(today, 6),
        match_date: undefined,
      }),
    );
  });
});

describe("find_match_opportunities", () => {
  it("prioritizes bet -> prediction -> statistics and respects limit", async () => {
    mockAnalyzeSources({
      bets: [
        makeBet({ event_id: 8, event_name: "Powyżej 2.5 gola", ev_after_tax: 0.08 }),
        makeBet({
          bet_id: 2,
          event_id: 6,
          event_name: "Obie strzelą",
          ev_after_tax: 0.05,
        }),
      ],
      predictions: [
        makePrediction({
          event_id: 12,
          event_name: "Poniżej 2.5 gola",
          value: 0.7,
        }),
        makePrediction({
          prediction_id: 2,
          event_id: 99,
          event_name: "Remis",
          value: 0.62,
        }),
      ],
      odds: [],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        strongSotMatches(5),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        Array.from({ length: 10 }, () => makeSotMatch(2, 5)),
      ),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 3,
      sport_id: 1,
    });

    expect(result.name).toBe("find_match_opportunities");
    const data = result.data as {
      opportunities: Array<{
        primary_evidence_source: string;
        event_id: number | null;
        event_name: string;
      }>;
    };
    expect(data.opportunities).toHaveLength(3);
    expect(data.opportunities[0]?.primary_evidence_source).toBe("bet");
    expect(data.opportunities[1]?.primary_evidence_source).toBe("bet");
    expect(data.opportunities[2]?.primary_evidence_source).toBe("prediction");
    // Under 2.5 (12) is complementary to Over 2.5 (8) already taken from bets
    expect(
      data.opportunities.some((item) => item.event_id === 12),
    ).toBe(false);
    expect(data.opportunities[2]?.event_id).toBe(99);
  });

  it("returns prediction and statistics without odds/bets", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [
        makePrediction({
          event_id: 8,
          event_name: "Powyżej 2.5 gola",
          value: 0.66,
        }),
      ],
      odds: [],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        viableStatMatches("strong"),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        viableStatMatches("soft"),
      ),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 3,
      sport_id: 1,
    });

    const data = result.data as {
      opportunities: Array<{
        primary_evidence_source: string;
        odds_available: boolean;
        note: string | null;
      }>;
    };
    expect(data.opportunities.length).toBeGreaterThan(0);
    expect(data.opportunities[0]?.primary_evidence_source).toBe("prediction");
    expect(data.opportunities[0]?.odds_available).toBe(false);
    expect(data.opportunities[0]?.note).toMatch(/bez kursu/);
    expect(
      data.opportunities.some(
        (item) => item.primary_evidence_source === "statistics",
      ),
    ).toBe(true);
  });

  it("returns empty controlled result when all tiers are empty", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [],
      odds: [],
      profileHome: makeProfile(makeTeam(1, "Górnik Zabrze"), [
        makeSotMatch(4, 2),
      ]),
      profileAway: makeProfile(makeTeam(2, "Śląsk Wrocław"), [
        makeSotMatch(2, 4),
      ]),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 3,
      sport_id: 1,
    });

    const data = result.data as { opportunities: unknown[] };
    expect(data.opportunities).toHaveLength(0);
    expect(result.warnings.some((w) => /Brak dodatnich bets/i.test(w))).toBe(
      true,
    );
  });

  it("does not include opposing statistical directions for the same line", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [],
      odds: [],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        viableStatMatches("strong"),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        viableStatMatches("soft"),
      ),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 5,
      sport_id: 1,
    });

    const data = result.data as {
      opportunities: Array<{
        statistical: {
          stat: string;
          subject: string;
          line: number;
          direction: string;
        } | null;
      }>;
    };
    const keys = data.opportunities
      .filter((item) => item.statistical)
      .map(
        (item) =>
          `${item.statistical!.stat}:${item.statistical!.subject}:${item.statistical!.line}`,
      );
    expect(keys.length).toBeGreaterThan(0);
    expect(keys.length).toBe(new Set(keys).size);
  });

  it("drops negative-EV and low-probability predictions from discovery tier", async () => {
    mockAnalyzeSources({
      bets: [],
      predictions: [
        makePrediction({
          event_id: 8,
          event_name: "Powyżej 2.5 gola",
          value: 0.4,
        }),
        makePrediction({
          prediction_id: 2,
          event_id: 99,
          event_name: "Remis",
          value: 0.4,
        }),
        makePrediction({
          prediction_id: 3,
          event_id: 100,
          event_name: "Wygrana gospodarzy",
          value: 0.62,
        }),
      ],
      odds: [
        {
          id: 1,
          match_id: 119435,
          bookmaker_id: 1,
          bookmaker_name: "STS",
          event_id: 8,
          event_name: "Powyżej 2.5 gola",
          event_family: null,
          odds: 2.0,
        },
      ],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        viableStatMatches("strong"),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        viableStatMatches("soft"),
      ),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 3,
      sport_id: 1,
      apply_tax: true,
    });

    const data = result.data as {
      opportunities: Array<{
        event_id: number | null;
        primary_evidence_source: string;
        odds_available: boolean;
      }>;
    };
    // EV = 0.4*2*0.88 - 1 < 0 → odrzucone; Remis 0.4 < 0.55 → odrzucone
    expect(data.opportunities.some((item) => item.event_id === 8)).toBe(false);
    expect(data.opportunities.some((item) => item.event_id === 99)).toBe(false);
    expect(data.opportunities.some((item) => item.event_id === 100)).toBe(true);
    expect(
      data.opportunities.some(
        (item) => item.primary_evidence_source === "statistics",
      ),
    ).toBe(true);
  });

  it("dedupes statistical OU 2.5 goals against model Over/Under 2.5", async () => {
    mockAnalyzeSources({
      bets: [
        makeBet({
          event_id: 8,
          event_name: "Powyżej 2.5 gola",
          ev_after_tax: 0.08,
        }),
      ],
      predictions: [],
      odds: [],
      profileHome: makeProfile(
        makeTeam(1, "Górnik Zabrze"),
        viableStatMatches("strong"),
      ),
      profileAway: makeProfile(
        makeTeam(2, "Śląsk Wrocław"),
        viableStatMatches("soft"),
      ),
    });

    const result = await findMatchOpportunities({
      match_id: 119435,
      limit: 5,
      sport_id: 1,
    });

    const data = result.data as {
      opportunities: Array<{
        event_id: number | null;
        event_name: string;
        primary_evidence_source: string;
        statistical: { stat: string; subject: string; line: number } | null;
      }>;
    };

    expect(data.opportunities[0]?.primary_evidence_source).toBe("bet");
    expect(data.opportunities[0]?.event_id).toBe(8);
    expect(
      data.opportunities.some(
        (item) =>
          item.statistical?.stat === "goals" &&
          item.statistical.subject === "total" &&
          item.statistical.line === 2.5,
      ),
    ).toBe(false);
    expect(
      data.opportunities.some(
        (item) =>
          item.primary_evidence_source === "statistics" &&
          /2\.5.*[Bb]ramk|2\.5.*[Gg]ol/i.test(item.event_name) &&
          /suma/i.test(item.event_name),
      ),
    ).toBe(false);
  });
});
