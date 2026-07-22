import { afterEach, describe, expect, it, vi } from "vitest";

import { numberArg, stringArg } from "@/server/chat/tools/args";
import { runPlannedTools } from "@/server/chat/tools/registry";
import {
  assertChatRateLimit,
  clientKeyFromRequest,
  resetChatRateLimitForTests,
} from "@/server/chat/rateLimit";
import { ChatRateLimitError, ChatRequestError } from "@/server/chat/errors";
import {
  assertCursorProviderEnabled,
  parseChatRequest,
  parseProvider,
} from "@/server/chat/request";

vi.mock("@/server/chat/tools/http", () => ({
  fetchReadOnly: vi.fn(),
  getEndpoint: (path: string) => `GET ${path}`,
  buildUrl: (path: string) => `http://localhost:8000${path}`,
}));

import { fetchReadOnly } from "@/server/chat/tools/http";

const mockedFetch = vi.mocked(fetchReadOnly);

afterEach(() => {
  mockedFetch.mockReset();
  resetChatRateLimitForTests();
  vi.unstubAllEnvs();
});

describe("tool argument validation", () => {
  it("requires integer args and enforces bounds", () => {
    expect(() => numberArg({}, "limit", { required: true })).toThrow(
      /Missing required/,
    );
    expect(() =>
      numberArg({ limit: 99 }, "limit", { max: 10 }),
    ).toThrow(/at most 10/);
    expect(numberArg({ limit: 5 }, "limit", { min: 1, max: 10 })).toBe(5);
  });

  it("validates string args", () => {
    expect(() => stringArg({ query: 12 }, "query", { required: true })).toThrow(
      /must be a string/,
    );
    expect(stringArg({ query: "Legia" }, "query", { required: true })).toBe(
      "Legia",
    );
  });
});

describe("runPlannedTools allowlist and limits", () => {
  it("blocks unknown tools without calling API", async () => {
    const results = await runPlannedTools(
      [
        {
          tool: "execute_sql" as never,
          args: { query: "DROP TABLE matches" },
        },
      ],
      { sport_id: 1, label: "Piłka nożna" },
    );

    expect(mockedFetch).not.toHaveBeenCalled();
    expect(results[0]?.warnings[0]).toMatch(/niedozwolone/);
  });

  it("caps tool calls at MAX_TOOL_CALLS", async () => {
    mockedFetch.mockResolvedValue({
      id: 1,
      league_id: 1,
      season_id: 1,
      sport_id: 1,
      round: 1,
      round_label: "1",
      game_date: "2024-01-01",
      home_team: { id: 1, name: "A", shortcut: "A" },
      away_team: { id: 2, name: "B", shortcut: "B" },
      home_goals: 1,
      away_goals: 0,
      result: "1",
      is_played: true,
      score_resolution: null,
      final_predictions: [],
      prediction_analysis: null,
      odds: [],
      stats: null,
      hockey_stats: null,
      has_player_stats: false,
      head_to_head: {
        meetings: 0,
        home_wins: 0,
        draws: 0,
        away_wins: 0,
        recent_matches: [],
      },
      home_team_history: [],
      away_team_history: [],
      boxscore: null,
      hockey_boxscore: null,
      model_assessments: [],
    });

    const planned = Array.from({ length: 6 }, (_, index) => ({
      tool: "get_match_details" as const,
      args: { match_id: index + 1 },
    }));
    const results = await runPlannedTools(planned, {
      sport_id: 1,
      label: "Piłka nożna",
    });

    expect(results).toHaveLength(4);
    expect(mockedFetch).toHaveBeenCalledTimes(4);
  });

  it("executes get_match_details against allowlisted GET path", async () => {
    mockedFetch.mockResolvedValue({
      id: 42,
      league_id: 1,
      season_id: 10,
      sport_id: 1,
      round: 3,
      round_label: "Kolejka 3",
      game_date: "2024-05-01",
      home_team: { id: 1, name: "Legia", shortcut: "LEG" },
      away_team: { id: 2, name: "Lech", shortcut: "LPO" },
      home_goals: 2,
      away_goals: 1,
      result: "1",
      is_played: true,
      score_resolution: null,
      final_predictions: [{ id: 1 }],
      prediction_analysis: null,
      odds: [{ id: 1 }, { id: 2 }],
      stats: null,
      hockey_stats: null,
      has_player_stats: false,
      head_to_head: {
        meetings: 0,
        home_wins: 0,
        draws: 0,
        away_wins: 0,
        recent_matches: [],
      },
      home_team_history: [{ match_id: 1 }],
      away_team_history: [{ match_id: 2 }],
      boxscore: null,
      hockey_boxscore: null,
      model_assessments: [],
    });

    const [result] = await runPlannedTools(
      [{ tool: "get_match_details", args: { match_id: 42 } }],
      { sport_id: 1, label: "Piłka nożna" },
    );

    expect(mockedFetch).toHaveBeenCalledWith("/matches/42/details");
    expect(result.summary).toMatch(/Legia/);
    expect(result.dataSources[0]?.endpoint).toContain("/matches/42/details");
  });
});

describe("rate limit", () => {
  it("throws HTTP-mappable 429 after max requests", () => {
    vi.stubEnv("CHAT_RATE_LIMIT_MAX_REQUESTS", "2");
    vi.stubEnv("CHAT_RATE_LIMIT_WINDOW_MS", "60000");
    assertChatRateLimit("ip:test");
    assertChatRateLimit("ip:test");
    expect(() => assertChatRateLimit("ip:test")).toThrow(ChatRateLimitError);
  });
});

describe("request errors", () => {
  it("throws ChatRequestError for invalid body", () => {
    expect(() => parseChatRequest({})).toThrow(ChatRequestError);
  });

  it("blocks cursor provider when disabled", () => {
    vi.stubEnv("CHAT_ENABLE_CURSOR", "false");
    vi.stubEnv("NEXT_PUBLIC_CHAT_ENABLE_CURSOR", "false");
    expect(() => parseProvider({ provider: "cursor" }, "openrouter")).toThrow(
      ChatRequestError,
    );
    expect(() => assertCursorProviderEnabled()).toThrow(ChatRequestError);
  });

  it("keeps openrouter when GUI selects it even if default is cursor", () => {
    vi.stubEnv("CHAT_ENABLE_CURSOR", "true");
    expect(parseProvider({ provider: "openrouter" }, "cursor")).toBe(
      "openrouter",
    );
  });
});

describe("clientKeyFromRequest", () => {
  it("prefers hashed session cookie over IP", () => {
    const request = new Request("http://localhost/api/chat", {
      headers: {
        cookie: "ekstrabet_token=secret-session-token",
        "x-forwarded-for": "1.2.3.4",
      },
    });
    const key = clientKeyFromRequest(request);
    expect(key.startsWith("session:")).toBe(true);
    expect(key).not.toContain("secret-session-token");
  });

  it("falls back to IP when session cookie is missing", () => {
    const request = new Request("http://localhost/api/chat", {
      headers: { "x-real-ip": "9.9.9.9" },
    });
    expect(clientKeyFromRequest(request)).toBe("ip:9.9.9.9");
  });
});
