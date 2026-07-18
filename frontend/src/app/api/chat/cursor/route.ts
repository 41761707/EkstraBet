import { NextResponse } from "next/server";
import { answerWithLocalCursorSdk } from "@/server/chat/cursorSdk";
import type { ChatRequest, ChatResponse, ChatSportContext } from "@/types/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function parseMessages(body: unknown): ChatRequest["messages"] {
  if (!body || typeof body !== "object" || !("messages" in body)) {
    throw new Error("Request body must include messages.");
  }

  const messages = (body as { messages?: unknown }).messages;
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Error("messages must be a non-empty array.");
  }

  return messages.slice(-8).map((message) => {
    if (
      !message ||
      typeof message !== "object" ||
      !("role" in message) ||
      !("content" in message)
    ) {
      throw new Error("Each message must include role and content.");
    }

    const role = (message as { role?: unknown }).role;
    const content = (message as { content?: unknown }).content;
    if (role !== "user" && role !== "assistant") {
      throw new Error("Message role must be user or assistant.");
    }
    if (typeof content !== "string" || content.trim().length === 0) {
      throw new Error("Message content must be a non-empty string.");
    }

    return {
      role,
      content: content.slice(0, 2_000),
    };
  });
}

function parseSport(body: unknown): ChatSportContext {
  if (!body || typeof body !== "object" || !("sport" in body)) {
    throw new Error("Request body must include sport.");
  }

  const sport = (body as { sport?: unknown }).sport;
  if (!sport || typeof sport !== "object") {
    throw new Error("sport must be an object.");
  }

  const rawSportId = (sport as { sport_id?: unknown }).sport_id;
  const label = (sport as { label?: unknown }).label;
  const sportId = typeof rawSportId === "number" ? rawSportId : Number(rawSportId);
  if (
    !Number.isInteger(sportId) ||
    typeof label !== "string" ||
    label.trim().length === 0
  ) {
    throw new Error("sport must include sport_id and label.");
  }

  if (sportId !== 1 && sportId !== 2) {
    throw new Error("Selected sport is not available in chat.");
  }

  return {
    sport_id: sportId,
    label: label.trim().slice(0, 80),
  };
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as unknown;
    const messages = parseMessages(body);
    const sport = parseSport(body);
    const answer = await answerWithLocalCursorSdk(messages, sport);
    const response: ChatResponse = { answer };

    return NextResponse.json(response);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unexpected chat route error.";
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}
