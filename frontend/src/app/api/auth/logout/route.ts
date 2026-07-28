import { NextResponse } from "next/server";

import { getAuthCookieName } from "@/lib/authCookie";
import { isSecureAuthCookie } from "@/lib/runtimeConfig";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: getAuthCookieName(),
    value: "",
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: isSecureAuthCookie(),
    maxAge: 0,
  });
  return response;
}
