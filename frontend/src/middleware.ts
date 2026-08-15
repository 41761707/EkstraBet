import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { getAuthCookieName, isAuthEnabled } from "@/lib/authCookie";
import { PATHNAME_HEADER } from "@/lib/firstLogin";

function nextWithPathname(request: NextRequest): NextResponse {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(PATHNAME_HEADER, request.nextUrl.pathname);
  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export function middleware(request: NextRequest) {
  if (!isAuthEnabled()) {
    return nextWithPathname(request);
  }

  const { pathname } = request.nextUrl;
  const token = request.cookies.get(getAuthCookieName())?.value;

  if (token) {
    return nextWithPathname(request);
  }

  // wywołania API bez sesji -> 401 JSON (nie HTML redirect)
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  const redirectTarget = `${pathname}${request.nextUrl.search}`;
  if (redirectTarget && redirectTarget !== "/login") {
    loginUrl.searchParams.set("next", redirectTarget);
  }
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    // api/health: liveness bez sesji; api/auth: login/logout bez cookie
    "/((?!_next/static|_next/image|favicon.ico|login|api/auth|api/health).*)",
  ],
};
