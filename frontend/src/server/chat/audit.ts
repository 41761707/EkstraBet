/** Structured audit logging for chat tool execution (no secrets). */

export interface ChatAuditToolCall {
  tool: string;
  args: Record<string, unknown>;
  durationMs: number;
  ok: boolean;
  warningCount: number;
}

export interface ChatAuditEntry {
  event: "chat.tools" | "chat.round";
  provider?: string;
  sportId?: number;
  questionPreview?: string;
  toolCalls: ChatAuditToolCall[];
  totalDurationMs: number;
}

function previewText(value: string | undefined, max = 160): string | undefined {
  if (!value) {
    return undefined;
  }
  const trimmed = value.trim().replace(/\s+/g, " ");
  return trimmed.length <= max ? trimmed : `${trimmed.slice(0, max)}…`;
}

function sanitizeArgs(args: Record<string, unknown>): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args)) {
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null
    ) {
      sanitized[key] =
        typeof value === "string" ? value.slice(0, 120) : value;
    } else {
      sanitized[key] = "[complex]";
    }
  }
  return sanitized;
}

export function logChatAudit(entry: ChatAuditEntry): void {
  const payload = {
    ...entry,
    questionPreview: previewText(entry.questionPreview),
    toolCalls: entry.toolCalls.map((call) => ({
      ...call,
      args: sanitizeArgs(call.args),
    })),
  };
  console.info("[chat-audit]", JSON.stringify(payload));
}

export function buildAuditToolCall(params: {
  tool: string;
  args: Record<string, unknown>;
  durationMs: number;
  ok: boolean;
  warningCount: number;
}): ChatAuditToolCall {
  return {
    tool: params.tool,
    args: params.args,
    durationMs: params.durationMs,
    ok: params.ok,
    warningCount: params.warningCount,
  };
}
