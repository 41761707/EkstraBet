import type { ChatProvider, ChatRequest, ChatSportContext } from "@/types/api";
import { ChatRequestError } from "@/server/chat/errors";

const ALLOWED_SPORT_IDS = new Set([1, 2]);
const ALLOWED_PROVIDERS = new Set<ChatProvider>(["cursor", "openrouter"]);

function readDefaultProvider(): ChatProvider {
  const fromEnv = process.env.CHAT_PROVIDER?.trim().toLowerCase();
  if (fromEnv === "cursor" || fromEnv === "openrouter") {
    return fromEnv;
  }
  return "openrouter";
}

/** True when Cursor prototype is explicitly enabled via env. */
export function isCursorProviderEnabled(): boolean {
  return (
    process.env.CHAT_ENABLE_CURSOR === "true" ||
    process.env.NEXT_PUBLIC_CHAT_ENABLE_CURSOR === "true"
  );
}

/** Reject Cursor provider when the internal prototype flag is off. */
export function assertCursorProviderEnabled(): void {
  if (!isCursorProviderEnabled()) {
    throw new ChatRequestError(
      "Cursor provider is disabled. Set CHAT_ENABLE_CURSOR=true for internal use.",
    );
  }
}

export function parseMessages(body: unknown): ChatRequest["messages"] {
  if (!body || typeof body !== "object" || !("messages" in body)) {
    throw new ChatRequestError("Request body must include messages.");
  }

  const messages = (body as { messages?: unknown }).messages;
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new ChatRequestError("messages must be a non-empty array.");
  }

  return messages.slice(-8).map((message) => {
    if (
      !message ||
      typeof message !== "object" ||
      !("role" in message) ||
      !("content" in message)
    ) {
      throw new ChatRequestError("Each message must include role and content.");
    }

    const role = (message as { role?: unknown }).role;
    const content = (message as { content?: unknown }).content;
    if (role !== "user" && role !== "assistant") {
      throw new ChatRequestError("Message role must be user or assistant.");
    }
    if (typeof content !== "string" || content.trim().length === 0) {
      throw new ChatRequestError("Message content must be a non-empty string.");
    }

    return {
      role,
      content: content.slice(0, 2_000),
    };
  });
}

export function parseSport(body: unknown): ChatSportContext {
  if (!body || typeof body !== "object" || !("sport" in body)) {
    throw new ChatRequestError("Request body must include sport.");
  }

  const sport = (body as { sport?: unknown }).sport;
  if (!sport || typeof sport !== "object") {
    throw new ChatRequestError("sport must be an object.");
  }

  const rawSportId = (sport as { sport_id?: unknown }).sport_id;
  const label = (sport as { label?: unknown }).label;
  const sportId =
    typeof rawSportId === "number" ? rawSportId : Number(rawSportId);
  if (
    !Number.isInteger(sportId) ||
    typeof label !== "string" ||
    label.trim().length === 0
  ) {
    throw new ChatRequestError("sport must include sport_id and label.");
  }

  if (!ALLOWED_SPORT_IDS.has(sportId)) {
    throw new ChatRequestError("Selected sport is not available in chat.");
  }

  return {
    sport_id: sportId,
    label: label.trim().slice(0, 80),
  };
}

export function parseProvider(
  body: unknown,
  fallback: ChatProvider = readDefaultProvider(),
): ChatProvider {
  if (!body || typeof body !== "object" || !("provider" in body)) {
    return fallback;
  }

  const provider = (body as { provider?: unknown }).provider;
  if (provider === undefined || provider === null || provider === "") {
    return fallback;
  }
  if (
    typeof provider !== "string" ||
    !ALLOWED_PROVIDERS.has(provider as ChatProvider)
  ) {
    throw new ChatRequestError('provider must be "cursor" or "openrouter".');
  }
  if (provider === "cursor") {
    assertCursorProviderEnabled();
  }
  return provider as ChatProvider;
}

export function parseChatRequest(body: unknown): ChatRequest {
  return {
    messages: parseMessages(body),
    sport: parseSport(body),
    provider: parseProvider(body),
  };
}
