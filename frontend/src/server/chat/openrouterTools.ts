import {
  CHAT_TOOL_DESCRIPTIONS,
  isChatToolName,
  OPENROUTER_TOOLS,
  type OpenRouterToolDefinition,
} from "@/server/chat/tools/catalog";

export type { OpenRouterToolDefinition };
export { CHAT_TOOL_DESCRIPTIONS, isChatToolName, OPENROUTER_TOOLS };

/** Structured output schema for the OpenRouter summary pass. */
export const CHAT_SUMMARY_JSON_SCHEMA = {
  name: "chat_summary",
  strict: true,
  schema: {
    type: "object",
    properties: {
      answerText: { type: "string" },
      warnings: {
        type: "array",
        items: { type: "string" },
      },
    },
    required: ["answerText", "warnings"],
    additionalProperties: false,
  },
} as const;
