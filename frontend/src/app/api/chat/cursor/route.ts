import { NextResponse } from "next/server";
import { chatErrorResponse } from "@/server/chat/errors";
import { answerWithCursorProvider } from "@/server/chat/provider";
import {
  assertChatRateLimit,
  clientKeyFromRequest,
} from "@/server/chat/rateLimit";
import {
  assertCursorProviderEnabled,
  parseMessages,
  parseSport,
} from "@/server/chat/request";
import type { ChatResponse } from "@/types/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    assertCursorProviderEnabled();
    assertChatRateLimit(`cursor:${clientKeyFromRequest(request)}`);
    const body = (await request.json()) as unknown;
    const messages = parseMessages(body);
    const sport = parseSport(body);
    const answer = await answerWithCursorProvider(messages, sport);
    const response: ChatResponse = { answer, provider: "cursor" };
    return NextResponse.json(response);
  } catch (error) {
    const mapped = chatErrorResponse(error);
    return NextResponse.json(mapped.body, {
      status: mapped.status,
      headers: mapped.headers,
    });
  }
}
