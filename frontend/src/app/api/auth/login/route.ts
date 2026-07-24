import { NextResponse } from "next/server";

import { getApiBaseUrl, getAuthCookieName } from "@/lib/auth";

interface LoginBody {
  username?: string;
  password?: string;
}

export async function POST(request: Request) {
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json({ detail: "Nieprawidłowa treść żądania" }, { status: 400 });
  }

  const username = body.username?.trim() ?? "";
  const password = body.password ?? "";
  if (!username || !password) {
    return NextResponse.json(
      { detail: "Nazwa użytkownika i hasło są wymagane" },
      { status: 400 },
    );
  }

  const upstream = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  });

  const payload = (await upstream.json().catch(() => ({}))) as {
    access_token?: string;
    expires_in?: number;
    detail?: string;
  };

  if (!upstream.ok || !payload.access_token) {
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : "Nieprawidłowa nazwa użytkownika lub hasło";
    return NextResponse.json({ detail }, { status: upstream.status || 401 });
  }

  const response = NextResponse.json({ ok: true });
  const maxAge =
    typeof payload.expires_in === "number" && payload.expires_in > 0
      ? payload.expires_in
      : 60 * 60 * 24;

  response.cookies.set({
    name: getAuthCookieName(),
    value: payload.access_token,
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge,
  });

  return response;
}
