import { describe, expect, it } from "vitest";

import {
  assembleChatAnswer,
  buildRefusalAnswer,
  extractJsonObject,
  sanitizeToolResultForModel,
  uniqueDataSources,
} from "@/server/chat/shared";
import { parseChatRequest, parseProvider } from "@/server/chat/request";
import {
  isChatToolName,
  OPENROUTER_TOOLS,
} from "@/server/chat/openrouterTools";
import {
  isClearlyOffTopic,
  OFF_TOPIC_REFUSAL_TEXT,
} from "@/server/chat/topicFilter";
import { answerWithOpenRouterProvider } from "@/server/chat/provider";
import { ChatProviderError, isTimeoutError } from "@/server/chat/errors";

describe("extractJsonObject", () => {
  it("parses raw JSON object", () => {
    const result = extractJsonObject<{ answerText: string }>(
      '{"answerText":"ok","warnings":[]}',
    );
    expect(result.answerText).toBe("ok");
  });

  it("parses fenced JSON", () => {
    const result = extractJsonObject<{ answerText: string }>(
      "```json\n{\"answerText\":\"fenced\"}\n```",
    );
    expect(result.answerText).toBe("fenced");
  });

  it("throws when JSON object is missing", () => {
    expect(() => extractJsonObject("no json here")).toThrow(
      /did not contain a JSON object/,
    );
  });
});

describe("assembleChatAnswer / refusal", () => {
  it("builds refusal answer", () => {
    const answer = buildRefusalAnswer("Poza zakresem.");
    expect(answer.answerText).toBe("Poza zakresem.");
    expect(answer.dataSources).toEqual([]);
    expect(answer.warnings.length).toBeGreaterThan(0);
  });

  it("assembles chart and unique data sources from tools", () => {
    const answer = assembleChatAnswer({
      answerText: "Podsumowanie",
      warnings: ["uwaga"],
      toolResults: [
        {
          summary: "A",
          chart: {
            type: "bar",
            title: "Serie",
            points: [{ label: "M1", value: 2 }],
          },
          dataSources: [
            { label: "Profil", endpoint: "/teams/1/profile", params: { limit: 5 } },
          ],
          warnings: ["brak sezonu"],
        },
        {
          summary: "B",
          dataSources: [
            { label: "Profil", endpoint: "/teams/1/profile", params: { limit: 5 } },
          ],
          warnings: [],
        },
      ],
    });

    expect(answer.answerText).toBe("Podsumowanie");
    expect(answer.chart?.title).toBe("Serie");
    expect(answer.dataSources).toHaveLength(1);
    expect(answer.warnings).toEqual(["brak sezonu", "uwaga"]);
  });

  it("dedupes data sources", () => {
    const sources = uniqueDataSources([
      { label: "A", endpoint: "/x", params: { a: 1 } },
      { label: "A", endpoint: "/x", params: { a: 1 } },
      { label: "B", endpoint: "/y" },
    ]);
    expect(sources).toHaveLength(2);
  });
});

describe("parseChatRequest", () => {
  it("parses valid request with openrouter provider", () => {
    const request = parseChatRequest({
      provider: "openrouter",
      sport: { sport_id: 1, label: "Piłka nożna" },
      messages: [{ role: "user", content: "Pokaż tabelę" }],
    });
    expect(request.provider).toBe("openrouter");
    expect(request.sport.sport_id).toBe(1);
    expect(request.messages).toHaveLength(1);
  });

  it("rejects invalid provider", () => {
    expect(() =>
      parseProvider({ provider: "openai" }, "openrouter"),
    ).toThrow(/provider must be/);
  });

  it("falls back to default provider when omitted", () => {
    expect(parseProvider({}, "cursor")).toBe("cursor");
  });

  it("rejects unsupported sport", () => {
    expect(() =>
      parseChatRequest({
        sport: { sport_id: 99, label: "Inny" },
        messages: [{ role: "user", content: "test" }],
      }),
    ).toThrow(/not available/);
  });
});

describe("openrouter tool allowlist", () => {
  it("exposes only known chat tools", () => {
    for (const tool of OPENROUTER_TOOLS) {
      expect(isChatToolName(tool.function.name)).toBe(true);
    }
  });

  it("rejects unknown tool names", () => {
    expect(isChatToolName("drop_database")).toBe(false);
    expect(isChatToolName("execute_sql")).toBe(false);
  });
});

describe("chat tool catalog single source of truth", () => {
  it("keeps Cursor descriptions and OpenRouter schemas in sync", async () => {
    const { CHAT_TOOL_DESCRIPTIONS, CHAT_TOOL_NAMES, CHAT_TOOL_CATALOG } =
      await import("@/server/chat/tools/catalog");

    expect(CHAT_TOOL_DESCRIPTIONS.map((item) => item.tool)).toEqual([
      ...CHAT_TOOL_NAMES,
    ]);
    expect(OPENROUTER_TOOLS.map((item) => item.function.name)).toEqual([
      ...CHAT_TOOL_NAMES,
    ]);

    for (const name of CHAT_TOOL_NAMES) {
      expect(CHAT_TOOL_CATALOG[name]).toBeDefined();
      const openRouter = OPENROUTER_TOOLS.find(
        (item) => item.function.name === name,
      );
      const description = CHAT_TOOL_DESCRIPTIONS.find(
        (item) => item.tool === name,
      );
      expect(openRouter?.function.description).toBe(
        CHAT_TOOL_CATALOG[name].description,
      );
      expect(description?.description).toBe(
        CHAT_TOOL_CATALOG[name].description,
      );
      expect(Object.keys(openRouter?.function.parameters.properties ?? {})).toEqual(
        Object.keys(CHAT_TOOL_CATALOG[name].args),
      );
    }
  });
});

describe("sanitizeToolResultForModel", () => {
  it("keeps small payloads intact and truncates large ones", () => {
    const small = sanitizeToolResultForModel({
      name: "get_match_details",
      summary: "ok",
      data: { match_id: 1 },
      warnings: [],
      chart: { title: "Wykres" },
      table: null,
    });
    expect(small.chartTitle).toBe("Wykres");
    expect(small.dataPreview).toEqual({ match_id: 1 });

    const huge = sanitizeToolResultForModel({
      name: "get_league_table",
      summary: "tabela",
      data: { rows: "x".repeat(5_000) },
      warnings: ["uwaga"],
    });
    expect(huge.dataPreview).toMatchObject({ truncated: true });
    expect(typeof (huge.dataPreview as { preview: string }).preview).toBe(
      "string",
    );
  });
});

describe("topicFilter (hard Etap 5)", () => {
  it("allows sports analytics questions", () => {
    expect(
      isClearlyOffTopic("Porównaj formę Legii i Lecha w ostatnich 5 meczach"),
    ).toBe(false);
    expect(isClearlyOffTopic("Pokaż tabelę Ekstraklasy")).toBe(false);
    expect(isClearlyOffTopic("Jaka pogoda na meczu Legii?")).toBe(false);
  });

  it("hard-refuses obvious off-topic", () => {
    expect(isClearlyOffTopic("Napisz mi kod w Pythonie")).toBe(true);
    expect(isClearlyOffTopic("Jaki jest przepis na pizzę")).toBe(true);
    expect(isClearlyOffTopic("Tell me a joke about cats")).toBe(true);
  });

  it("provider returns refusal without calling LLM tools path", async () => {
    const answer = await answerWithOpenRouterProvider(
      [{ role: "user", content: "Napisz mi kod w JavaScript" }],
      { sport_id: 1, label: "Piłka nożna" },
    );
    expect(answer.answerText).toBe(OFF_TOPIC_REFUSAL_TEXT);
    expect(answer.dataSources).toEqual([]);
  });

  it("parseProvider keeps openrouter when GUI selects it", () => {
    expect(
      parseProvider({ provider: "openrouter" }, "cursor"),
    ).toBe("openrouter");
  });
});

describe("provider timeout helpers", () => {
  it("detects TimeoutError / AbortError", () => {
    const timeout = new Error("aborted");
    timeout.name = "TimeoutError";
    expect(isTimeoutError(timeout)).toBe(true);

    const abort = new Error("aborted");
    abort.name = "AbortError";
    expect(isTimeoutError(abort)).toBe(true);

    expect(isTimeoutError(new ChatProviderError("x"))).toBe(false);
  });
});
