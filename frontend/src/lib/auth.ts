/** Auth cookie / kill-switch helpers shared by middleware and BFF routes. */

export const DEFAULT_AUTH_COOKIE_NAME = "ekstrabet_token";

export function getAuthCookieName(): string {
  return process.env.AUTH_COOKIE_NAME ?? DEFAULT_AUTH_COOKIE_NAME;
}

/** Server-side kill switch; must match backend AUTH_ENABLED. */
export function isAuthEnabled(): boolean {
  const raw = (process.env.AUTH_ENABLED ?? "true").trim().toLowerCase();
  return raw !== "false" && raw !== "0" && raw !== "no" && raw !== "off";
}

export function getApiBaseUrl(): string {
  return (
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  );
}

/**
 * Read JWT from the HttpOnly auth cookie (RSC / Route Handlers / server chat).
 * Returns Authorization headers for direct FastAPI calls.
 */
export async function getServerAuthHeaders(): Promise<HeadersInit> {
  if (typeof window !== "undefined") {
    return {};
  }
  try {
    const { cookies } = await import("next/headers");
    const jar = await cookies();
    const token = jar.get(getAuthCookieName())?.value;
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch {
    // poza request scope Next (np. build) — bez Authorization
  }
  return {};
}

/** Safe post-login path: internal only, blocks protocol-relative //evil.com. */
export function safeInternalPath(next: string | null | undefined): string {
  if (!next) {
    return "/";
  }
  if (!next.startsWith("/") || next.startsWith("//")) {
    return "/";
  }
  return next;
}
