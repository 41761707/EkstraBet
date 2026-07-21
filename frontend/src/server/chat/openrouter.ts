import type { ChatAnswer, ChatSportContext } from "@/types/api";
import {
  ChatProviderError,
  isTimeoutError,
  LLM_REQUEST_TIMEOUT_MS,
} from "@/server/chat/errors";
import {
  assembleChatAnswer,
  buildRefusalAnswer,
  extractJsonObject,
  sanitizeToolResultForModel,
} from "@/server/chat/shared";
import {
  buildOpenRouterSummarySystemPrompt,
  buildOpenRouterSystemPrompt,
} from "@/server/chat/prompts";
import {
  CHAT_SUMMARY_JSON_SCHEMA,
  isChatToolName,
  OPENROUTER_TOOLS,
} from "@/server/chat/openrouterTools";
import { runPlannedTools } from "@/server/chat/tools";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini";
const MAX_TOOL_ROUNDS = 3;
const MAX_TOOL_CALLS = 4;

interface OpenRouterToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

interface OpenRouterMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: OpenRouterToolCall[];
  tool_call_id?: string;
}

interface OpenRouterChoiceMessage {
  role: "assistant";
  content: string | null;
  tool_calls?: OpenRouterToolCall[];
}

interface OpenRouterCompletion {
  choices?: Array<{
    message?: OpenRouterChoiceMessage;
    finish_reason?: string | null;
  }>;
  error?: { message?: string };
}

interface ChatSummary {
  answerText: string;
  warnings: string[];
}

type ToolResultList = Awaited<ReturnType<typeof runPlannedTools>>;

function requireOpenRouterApiKey(): string {
  const apiKey = process.env.OPENROUTER_API_KEY?.trim();
  if (!apiKey) {
    throw new ChatProviderError(
      "Missing OPENROUTER_API_KEY for production OpenRouter chat.",
    );
  }
  return apiKey;
}

function resolveModel(): string {
  return process.env.OPENROUTER_MODEL?.trim() || DEFAULT_OPENROUTER_MODEL;
}

function buildHeaders(apiKey: string): HeadersInit {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  const referer = process.env.OPENROUTER_HTTP_REFERER?.trim();
  const title = process.env.OPENROUTER_APP_TITLE?.trim() || "EkstraBet Chat";
  if (referer) {
    headers["HTTP-Referer"] = referer;
  }
  headers["X-Title"] = title;
  return headers;
}

async function callOpenRouter(
  body: Record<string, unknown>,
): Promise<OpenRouterCompletion> {
  const apiKey = requireOpenRouterApiKey();
  let response: Response;
  try {
    response = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: buildHeaders(apiKey),
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(LLM_REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    if (isTimeoutError(error)) {
      throw new ChatProviderError("OpenRouter request timed out.");
    }
    throw new ChatProviderError(
      error instanceof Error ? error.message : "OpenRouter request failed.",
    );
  }

  const payload = (await response.json().catch(() => null)) as
    | OpenRouterCompletion
    | null;
  if (!response.ok) {
    const detail =
      payload?.error?.message ??
      `OpenRouter request failed with status ${response.status}.`;
    throw new ChatProviderError(detail);
  }
  if (!payload) {
    throw new ChatProviderError("OpenRouter returned an empty response.");
  }
  return payload;
}

function parseToolCallArguments(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return parsed as Record<string, unknown>;
  } catch {
    return {};
  }
}

function buildBlockedResult(name: string, warning: string): ToolResultList[number] {
  return {
    name,
    summary: warning,
    data: null,
    dataSources: [],
    warnings: [warning],
  };
}

async function executeToolCallsForRound(params: {
  toolCalls: OpenRouterToolCall[];
  sport: ChatSportContext;
  remainingSlots: number;
  questionPreview?: string;
}): Promise<{ results: ToolResultList; executedCount: number }> {
  const results: ToolResultList = [];
  const planned: Array<{
    tool: Parameters<typeof runPlannedTools>[0][number]["tool"];
    args: Record<string, unknown>;
  }> = [];
  const plannedIndexes: number[] = [];

  for (let index = 0; index < params.toolCalls.length; index += 1) {
    const toolCall = params.toolCalls[index];
    if (!isChatToolName(toolCall.function.name)) {
      results[index] = buildBlockedResult(
        toolCall.function.name,
        `Blocked tool: ${toolCall.function.name}`,
      );
      continue;
    }
    if (planned.length >= params.remainingSlots) {
      results[index] = buildBlockedResult(
        toolCall.function.name,
        "Tool call limit reached.",
      );
      continue;
    }
    plannedIndexes.push(index);
    planned.push({
      tool: toolCall.function.name,
      args: parseToolCallArguments(toolCall.function.arguments),
    });
  }

  if (planned.length > 0) {
    // jeden audit chat.tools na rundę zamiast N osobnych wpisów
    const executed = await runPlannedTools(planned, params.sport, {
      provider: "openrouter",
      questionPreview: params.questionPreview,
    });
    for (let offset = 0; offset < plannedIndexes.length; offset += 1) {
      results[plannedIndexes[offset]] = executed[offset];
    }
  }

  return {
    results: params.toolCalls.map(
      (_, index) =>
        results[index] ??
        buildBlockedResult("unknown", "Tool call skipped."),
    ),
    executedCount: planned.length,
  };
}

async function runToolCallingLoop(params: {
  messages: { role: string; content: string }[];
  sport: ChatSportContext;
}): Promise<{ toolResults: ToolResultList; refusalText: string | null }> {
  const conversation: OpenRouterMessage[] = [
    { role: "system", content: buildOpenRouterSystemPrompt(params.sport) },
    ...params.messages.slice(-6).map((message) => ({
      role: message.role as "user" | "assistant",
      content: message.content,
    })),
  ];

  const toolResults: ToolResultList = [];
  let executedTotal = 0;
  let refusalText: string | null = null;

  for (let round = 0; round < MAX_TOOL_ROUNDS; round += 1) {
    const remainingSlots = MAX_TOOL_CALLS - executedTotal;
    const completion = await callOpenRouter({
      model: resolveModel(),
      messages: conversation,
      tools: remainingSlots > 0 ? OPENROUTER_TOOLS : undefined,
      tool_choice: remainingSlots > 0 ? "auto" : "none",
      temperature: 0.2,
      provider: {
        require_parameters: true,
      },
    });

    const message = completion.choices?.[0]?.message;
    if (!message) {
      throw new Error("OpenRouter returned no assistant message.");
    }

    if (!message.tool_calls || message.tool_calls.length === 0) {
      refusalText = message.content?.trim() || null;
      break;
    }

    conversation.push({
      role: "assistant",
      content: message.content,
      tool_calls: message.tool_calls,
    });

    const lastUser = [...params.messages]
      .reverse()
      .find((item) => item.role === "user");
    const { results, executedCount } = await executeToolCallsForRound({
      toolCalls: message.tool_calls,
      sport: params.sport,
      remainingSlots,
      questionPreview: lastUser?.content,
    });

    executedTotal += executedCount;
    if (executedCount === 0 && toolResults.length === 0) {
      refusalText =
        "Model wybrał niedozwolone narzędzie. Zapytanie zostało zablokowane.";
    }

    for (let index = 0; index < message.tool_calls.length; index += 1) {
      const toolCall = message.tool_calls[index];
      const result = results[index];
      conversation.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(sanitizeToolResultForModel(result)),
      });
    }

    toolResults.push(...results);
  }

  return { toolResults, refusalText };
}

async function summarizeWithStructuredOutput(params: {
  messages: { role: string; content: string }[];
  sport: ChatSportContext;
  toolResults: ToolResultList;
}): Promise<ChatSummary> {
  const sanitized = params.toolResults.map(sanitizeToolResultForModel);
  const completion = await callOpenRouter({
    model: resolveModel(),
    messages: [
      {
        role: "system",
        content: buildOpenRouterSummarySystemPrompt(params.sport),
      },
      {
        role: "user",
        content: JSON.stringify({
          messages: params.messages.slice(-6),
          toolResults: sanitized,
        }),
      },
    ],
    temperature: 0.2,
    response_format: {
      type: "json_schema",
      json_schema: CHAT_SUMMARY_JSON_SCHEMA,
    },
    provider: {
      require_parameters: true,
    },
  });

  const content = completion.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error("OpenRouter summary response was empty.");
  }

  const summary = extractJsonObject<ChatSummary>(content);
  return {
    answerText:
      typeof summary.answerText === "string" && summary.answerText.trim()
        ? summary.answerText.trim()
        : params.toolResults.map((result) => result.summary).join(" "),
    warnings: Array.isArray(summary.warnings)
      ? summary.warnings.filter((item): item is string => typeof item === "string")
      : [],
  };
}

function hasUsefulToolData(toolResults: ToolResultList): boolean {
  return toolResults.some(
    (result) =>
      result.data !== null ||
      Boolean(result.chart) ||
      Boolean(result.table) ||
      result.dataSources.length > 0,
  );
}

export async function answerWithOpenRouter(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  const { toolResults, refusalText } = await runToolCallingLoop({
    messages,
    sport,
  });

  if (!hasUsefulToolData(toolResults)) {
    return buildRefusalAnswer(refusalText);
  }

  try {
    const summary = await summarizeWithStructuredOutput({
      messages,
      sport,
      toolResults,
    });
    return assembleChatAnswer({
      toolResults,
      answerText: summary.answerText,
      warnings: summary.warnings,
    });
  } catch (error) {
    // fallback gdy model nie wspiera response_format — używamy summary z narzędzi
    const fallbackWarning =
      error instanceof Error
        ? `Structured summary fallback: ${error.message}`
        : "Structured summary fallback.";
    return assembleChatAnswer({
      toolResults,
      warnings: [fallbackWarning],
    });
  }
}
