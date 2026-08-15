import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { getAuthCookieName, isAuthEnabled } from "@/lib/authCookie";
import { getApiBaseUrl } from "@/lib/runtimeConfig";

interface CompleteFirstLoginBody {
  username?: string;
  new_password?: string;
  new_password_confirm?: string;
}

interface ParsedCompleteFirstLoginBody {
  username: string;
  newPassword: string;
  newPasswordConfirm: string;
}

function jsonError(detail: string, status: number): NextResponse {
  return NextResponse.json({ detail }, { status });
}

function readCompleteFirstLoginBody(
  body: CompleteFirstLoginBody,
): ParsedCompleteFirstLoginBody | null {
  const username = body.username?.trim() ?? "";
  const newPassword = body.new_password ?? "";
  const newPasswordConfirm = body.new_password_confirm ?? "";
  if (!username || !newPassword || !newPasswordConfirm) {
    return null;
  }
  return { username, newPassword, newPasswordConfirm };
}

export async function POST(request: Request) {
  const jar = await cookies();
  const token = jar.get(getAuthCookieName())?.value;
  if (isAuthEnabled() && !token) {
    return jsonError("Not authenticated", 401);
  }

  let body: CompleteFirstLoginBody;
  try {
    body = (await request.json()) as CompleteFirstLoginBody;
  } catch {
    return jsonError("Nieprawidłowa treść żądania", 400);
  }

  const parsed = readCompleteFirstLoginBody(body);
  if (!parsed) {
    return jsonError("Nazwa użytkownika i oba hasła są wymagane", 400);
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const upstream = await fetch(`${getApiBaseUrl()}/auth/complete-first-login`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      username: parsed.username,
      new_password: parsed.newPassword,
      new_password_confirm: parsed.newPasswordConfirm,
    }),
    cache: "no-store",
  });

  const payload = (await upstream.json().catch(() => ({}))) as {
    detail?: string;
  };

  if (!upstream.ok) {
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : "Nie udało się zapisać danych konta";
    return jsonError(detail, upstream.status || 400);
  }

  return NextResponse.json({ ok: true });
}
