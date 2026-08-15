import "server-only";

/** Server-only auth helpers for RSC, route handlers and chat tools. */

import { getAuthCookieName } from "@/lib/authCookie";

export {
  DEFAULT_AUTH_COOKIE_NAME,
  getAuthCookieName,
  isAuthEnabled,
  resolvePostLoginPath,
  safeInternalPath,
} from "@/lib/authCookie";

export {
  getApiBaseUrl,
  getAppOrigin,
  isSecureAuthCookie,
} from "@/lib/runtimeConfig";

/**
 * Read JWT from the HttpOnly auth cookie (RSC / Route Handlers / server chat).
 * Returns Authorization headers for direct FastAPI calls.
 */
export async function getServerAuthHeaders(): Promise<HeadersInit> {
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
