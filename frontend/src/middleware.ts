import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { getAuthCookieName, isAuthEnabled } from "@/lib/auth";

export function middleware(request: NextRequest) {
  if (!isAuthEnabled()) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  const token = request.cookies.get(getAuthCookieName())?.value;

  if (token) {
    return NextResponse.next();
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
    "/((?!_next/static|_next/image|favicon.ico|login|api/auth).*)",
  ],
};
