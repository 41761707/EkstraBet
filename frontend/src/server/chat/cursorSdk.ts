import { Agent, CursorAgentError } from "@cursor/sdk";
import type { ChatAnswer, ChatSportContext } from "@/types/api";
import {
  ChatProviderError,
  withProviderTimeout,
} from "@/server/chat/errors";
import {
  buildCursorPlanningPrompt,
  buildCursorSummaryPrompt,
} from "@/server/chat/prompts";
import {
  assembleChatAnswer,
  buildRefusalAnswer,
  extractJsonObject,
  sanitizeToolResultForModel,
  stableStringify,
} from "@/server/chat/shared";
import { runPlannedTools, type PlannedToolCall } from "@/server/chat/tools";

interface CursorPlan {
  toolCalls: PlannedToolCall[];
  refusal?: string;
}

interface CursorSummary {
  answerText?: string;
  warnings?: string[];
}

const DEFAULT_CURSOR_MODEL = "composer-2.5";

function requireCursorApiKey(): string {
  const apiKey = process.env.CURSOR_API_KEY?.trim();
  if (!apiKey) {
    throw new ChatProviderError(
      "Missing CURSOR_API_KEY for Cursor SDK chat prototype.",
    );
  }
  return apiKey;
}

function extractText(result: unknown): string {
  if (typeof result === "string") {
    return result;
  }
  if (result && typeof result === "object" && "result" in result) {
    const value = (result as { result?: unknown }).result;
    return typeof value === "string" ? value : JSON.stringify(value);
  }
  return JSON.stringify(result);
}

async function runCursorPrompt(prompt: string): Promise<string> {
  try {
    // local runtime — agent działa na maszynie wywołującej (prototyp wewnętrzny)
    const result = await withProviderTimeout(
      Agent.prompt(prompt, {
        apiKey: requireCursorApiKey(),
        model: { id: process.env.CURSOR_MODEL ?? DEFAULT_CURSOR_MODEL },
        local: { cwd: process.cwd() },
      }),
      "Cursor SDK request timed out.",
    );
    return extractText(result);
  } catch (error) {
    if (error instanceof CursorAgentError) {
      throw new ChatProviderError(
        `Cursor SDK failed to start: ${error.message}`,
      );
    }
    if (error instanceof ChatProviderError) {
      throw error;
    }
    throw new ChatProviderError(
      error instanceof Error ? error.message : "Cursor SDK request failed.",
    );
  }
}

function normalizePlan(plan: CursorPlan): CursorPlan {
  if (!Array.isArray(plan.toolCalls)) {
    return { toolCalls: [], refusal: plan.refusal };
  }

  const seenToolCalls = new Set<string>();
  const toolCalls: PlannedToolCall[] = [];
  for (const call of plan.toolCalls) {
    if (
      !call ||
      typeof call.tool !== "string" ||
      !call.args ||
      typeof call.args !== "object"
    ) {
      continue;
    }

    const key = `${call.tool}:${stableStringify(call.args)}`;
    if (seenToolCalls.has(key)) {
      continue;
    }
    seenToolCalls.add(key);
    toolCalls.push(call);
  }

  return {
    toolCalls: toolCalls.slice(0, 4),
    refusal: typeof plan.refusal === "string" ? plan.refusal : undefined,
  };
}

export async function answerWithLocalCursorSdk(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  const planText = await runCursorPrompt(
    buildCursorPlanningPrompt(messages, sport),
  );
  const plan = normalizePlan(extractJsonObject<CursorPlan>(planText));

  if (plan.toolCalls.length === 0) {
    return buildRefusalAnswer(plan.refusal);
  }

  const lastUser = [...messages].reverse().find((item) => item.role === "user");
  const toolResults = await runPlannedTools(plan.toolCalls, sport, {
    provider: "cursor",
    questionPreview: lastUser?.content,
  });
  // ta sama sanitizacja co OpenRouter — pełne toolResults nie idą do summary
  const sanitizedResults = toolResults.map(sanitizeToolResultForModel);
  const summaryText = await runCursorPrompt(
    buildCursorSummaryPrompt({
      messages,
      toolResults: sanitizedResults,
      sport,
    }),
  );
  const summary = extractJsonObject<CursorSummary>(summaryText);

  return assembleChatAnswer({
    toolResults,
    answerText: summary.answerText,
    warnings: Array.isArray(summary.warnings) ? summary.warnings : [],
  });
}
