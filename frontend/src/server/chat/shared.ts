import type { ChatAnswer } from "@/types/api";

const TOOL_RESULT_PREVIEW_CHARS = 4_000;

/** Stable JSON for dedupe keys (sorted object keys). */
export function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

export function extractJsonObject<T>(text: string): T {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const jsonText = fenced?.[1] ?? text;
  const start = jsonText.indexOf("{");
  const end = jsonText.lastIndexOf("}");
  if (start < 0 || end < start) {
    throw new Error("Response did not contain a JSON object.");
  }
  return JSON.parse(jsonText.slice(start, end + 1)) as T;
}

export function uniqueDataSources(
  sources: ChatAnswer["dataSources"],
): ChatAnswer["dataSources"] {
  const seenSources = new Set<string>();
  return sources.filter((source) => {
    const key = `${source.label}:${source.endpoint}:${stableStringify(
      source.params ?? {},
    )}`;
    if (seenSources.has(key)) {
      return false;
    }
    seenSources.add(key);
    return true;
  });
}

export function buildRefusalAnswer(refusal?: string | null): ChatAnswer {
  return {
    answerText:
      refusal ??
      "Nie znalazłem bezpiecznego zapytania read-only, które obsłużyłoby tę prośbę.",
    chart: null,
    table: null,
    dataSources: [],
    warnings: ["Zapytanie nie zostało wykonane na API."],
  };
}

/**
 * Skraca wynik narzędzia zanim trafi do modelu (OpenRouter / Cursor summary).
 * Pełne payloady API mogą przepełnić kontekst i podbić koszt.
 */
export function sanitizeToolResultForModel(result: {
  name: string;
  summary: string;
  data: unknown;
  warnings: string[];
  chart?: { title?: string } | null;
  table?: { title?: string } | null;
}): Record<string, unknown> {
  return {
    name: result.name,
    summary: result.summary,
    warnings: result.warnings,
    chartTitle: result.chart?.title ?? null,
    tableTitle: result.table?.title ?? null,
    dataPreview: truncateJson(result.data, TOOL_RESULT_PREVIEW_CHARS),
  };
}

export function truncateJson(value: unknown, maxChars: number): unknown {
  const text = JSON.stringify(value);
  if (!text) {
    return null;
  }
  if (text.length <= maxChars) {
    return value;
  }
  return {
    truncated: true,
    preview: text.slice(0, maxChars),
  };
}

interface ToolResultLike {
  summary: string;
  chart?: ChatAnswer["chart"];
  table?: ChatAnswer["table"];
  dataSources: ChatAnswer["dataSources"];
  warnings: string[];
}

export function assembleChatAnswer(params: {
  toolResults: ToolResultLike[];
  answerText?: string;
  warnings?: string[];
}): ChatAnswer {
  const firstChart =
    params.toolResults.find((result) => result.chart)?.chart ?? null;
  const firstTable =
    params.toolResults.find((result) => result.table)?.table ?? null;

  return {
    answerText:
      params.answerText ??
      params.toolResults.map((result) => result.summary).join(" "),
    chart: firstChart,
    table: firstTable,
    dataSources: uniqueDataSources(
      params.toolResults.flatMap((result) => result.dataSources),
    ),
    warnings: [
      ...new Set([
        ...params.toolResults.flatMap((result) => result.warnings),
        ...(params.warnings ?? []),
      ]),
    ],
  };
}
