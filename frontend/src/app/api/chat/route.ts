import { NextResponse } from "next/server";
import { ChatRequestError, chatErrorResponse } from "@/server/chat/errors";
import { answerWithOpenRouterProvider } from "@/server/chat/provider";
import {
  assertChatRateLimit,
  clientKeyFromRequest,
} from "@/server/chat/rateLimit";
import { parseMessages, parseProvider, parseSport } from "@/server/chat/request";
import type { ChatResponse } from "@/types/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Production chat endpoint — OpenRouter only.
 * Cursor must use /api/chat/cursor; sending provider=cursor here is rejected.
 */
export async function POST(request: Request) {
  try {
    assertChatRateLimit(clientKeyFromRequest(request));
    const body = (await request.json()) as unknown;
    const messages = parseMessages(body);
    const sport = parseSport(body);
    const provider = parseProvider(body, "openrouter");

    if (provider === "cursor") {
      throw new ChatRequestError(
        'Cursor provider is not allowed on /api/chat. Use POST /api/chat/cursor.',
      );
    }

    const answer = await answerWithOpenRouterProvider(messages, sport);
    const response: ChatResponse = {
      answer,
      provider: "openrouter",
    };
    return NextResponse.json(response);
  } catch (error) {
    const mapped = chatErrorResponse(error);
    return NextResponse.json(mapped.body, {
      status: mapped.status,
      headers: mapped.headers,
    });
  }
}
