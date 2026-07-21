import type { ChatAnswer, ChatProvider, ChatSportContext } from "@/types/api";
import { answerWithOpenRouter } from "@/server/chat/openrouter";
import { buildRefusalAnswer } from "@/server/chat/shared";
import {
  isClearlyOffTopic,
  lastUserMessageContent,
  OFF_TOPIC_REFUSAL_TEXT,
} from "@/server/chat/topicFilter";

/** Hard topic gate shared by OpenRouter and Cursor routes. */
export function maybeRefuseOffTopic(
  messages: { role: string; content: string }[],
): ChatAnswer | null {
  const lastUser = lastUserMessageContent(messages);
  if (lastUser && isClearlyOffTopic(lastUser)) {
    return buildRefusalAnswer(OFF_TOPIC_REFUSAL_TEXT);
  }
  return null;
}

/**
 * Production OpenRouter path — never loads or calls Cursor SDK.
 */
export async function answerWithOpenRouterProvider(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  const refusal = maybeRefuseOffTopic(messages);
  if (refusal) {
    return refusal;
  }
  return answerWithOpenRouter(messages, sport);
}

/**
 * Cursor prototype path — Cursor SDK is loaded only here (dynamic import).
 */
export async function answerWithCursorProvider(
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  const refusal = maybeRefuseOffTopic(messages);
  if (refusal) {
    return refusal;
  }
  // lazy import: ścieżka OpenRouter nie ładuje @cursor/sdk
  const { answerWithLocalCursorSdk } = await import("@/server/chat/cursorSdk");
  return answerWithLocalCursorSdk(messages, sport);
}

/** Dispatcher kept for tests; production routes call the specific providers. */
export async function answerWithChatProvider(
  provider: ChatProvider,
  messages: { role: string; content: string }[],
  sport: ChatSportContext,
): Promise<ChatAnswer> {
  if (provider === "cursor") {
    return answerWithCursorProvider(messages, sport);
  }
  return answerWithOpenRouterProvider(messages, sport);
}
