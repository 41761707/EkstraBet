/** BFF proxy path allowlist and request guards. */

export type HttpMethod = "GET" | "HEAD" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface AllowedRoute {
  /** Path prefix without leading slash (e.g. "leagues"). */
  prefix: string;
  methods: readonly HttpMethod[];
}

/**
 * Explicit allowlist of FastAPI prefixes the Next.js BFF may proxy.
 * Aligned with browser-facing `@/lib/apiClient` (least privilege).
 * Chat/server tools call FastAPI directly via API_BASE_URL — not via BFF.
 */
export const BFF_ALLOWED_ROUTES: readonly AllowedRoute[] = [
  { prefix: "leagues", methods: ["GET"] },
  { prefix: "teams", methods: ["GET"] },
  { prefix: "matches", methods: ["GET"] },
  { prefix: "bets", methods: ["GET"] },
  { prefix: "analytics", methods: ["GET"] },
  { prefix: "models", methods: ["GET"] },
  { prefix: "players", methods: ["GET"] },
  { prefix: "predictions", methods: ["GET", "POST"] },
  { prefix: "users", methods: ["GET", "PUT", "DELETE"] },
  { prefix: "typer-lm", methods: ["GET", "PUT", "POST", "DELETE"] },
];

const MUTATING_METHODS = new Set<HttpMethod>([
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
]);

const ENCODED_SEPARATOR_PATTERN = /%(?:2e|2f|5c)/i;
const BACKSLASH_PATTERN = /\\/;
const ABSOLUTE_URL_PATTERN = /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i;

export type BffPathRejectReason =
  | "empty"
  | "absolute"
  | "backslash"
  | "encoded-separator"
  | "traversal"
  | "not-normalized";

export interface BffPathValidationResult {
  ok: boolean;
  path?: string;
  reason?: BffPathRejectReason;
}

/**
 * Normalize and validate catch-all path segments before building an upstream URL.
 */
export function normalizeBffPath(pathSegments: string[]): BffPathValidationResult {
  if (pathSegments.length === 0) {
    return { ok: false, reason: "empty" };
  }

  const joined = pathSegments.join("/");
  if (!joined || joined === "/") {
    return { ok: false, reason: "empty" };
  }

  if (ABSOLUTE_URL_PATTERN.test(joined)) {
    return { ok: false, reason: "absolute" };
  }

  if (BACKSLASH_PATTERN.test(joined)) {
    return { ok: false, reason: "backslash" };
  }

  if (ENCODED_SEPARATOR_PATTERN.test(joined)) {
    return { ok: false, reason: "encoded-separator" };
  }

  let decoded: string;
  try {
    decoded = decodeURIComponent(joined);
  } catch {
    return { ok: false, reason: "encoded-separator" };
  }

  if (ABSOLUTE_URL_PATTERN.test(decoded) || BACKSLASH_PATTERN.test(decoded)) {
    return {
      ok: false,
      reason: ABSOLUTE_URL_PATTERN.test(decoded) ? "absolute" : "backslash",
    };
  }

  if (ENCODED_SEPARATOR_PATTERN.test(decoded)) {
    return { ok: false, reason: "encoded-separator" };
  }

  const segments = decoded.split("/").filter((segment) => segment.length > 0);
  if (segments.length === 0) {
    return { ok: false, reason: "empty" };
  }

  for (const segment of segments) {
    if (segment === "." || segment === "..") {
      return { ok: false, reason: "traversal" };
    }
    if (segment.includes("\\") || ABSOLUTE_URL_PATTERN.test(segment)) {
      return { ok: false, reason: "absolute" };
    }
  }

  const normalized = segments.join("/");
  if (normalized !== decoded.replace(/^\/+|\/+$/g, "").replace(/\/+/g, "/")) {
    // odrzucamy formy, które po złożeniu wyglądają inaczej niż jawne segmenty
    return { ok: false, reason: "not-normalized" };
  }

  return { ok: true, path: normalized };
}

export function isMethodAllowedForPath(
  path: string,
  method: string,
  allowlist: readonly AllowedRoute[] = BFF_ALLOWED_ROUTES,
): boolean {
  const upperMethod = method.toUpperCase() as HttpMethod;
  const firstSegment = path.split("/")[0] ?? "";
  const route = allowlist.find((entry) => entry.prefix === firstSegment);
  if (!route) {
    return false;
  }
  return route.methods.includes(upperMethod);
}

export function isMutatingMethod(method: string): boolean {
  return MUTATING_METHODS.has(method.toUpperCase() as HttpMethod);
}

/**
 * Expected Origin for mutating BFF calls.
 * Prefer APP_ORIGIN; without it (local .env) use the BFF request origin.
 */
export function resolveExpectedMutatingOrigin(
  appOrigin: string | null,
  requestUrl: string,
): string | null {
  if (appOrigin) {
    return appOrigin;
  }
  try {
    return new URL(requestUrl).origin;
  } catch {
    return null;
  }
}

/**
 * Mutating BFF calls must present Origin matching the expected app origin.
 * Same-origin browser fetches always send Origin for POST/PUT/PATCH/DELETE.
 */
export function isAllowedMutatingOrigin(
  originHeader: string | null,
  expectedOrigin: string | null,
): boolean {
  if (!expectedOrigin || !originHeader) {
    return false;
  }
  try {
    const expected = new URL(expectedOrigin).origin;
    const actual = new URL(originHeader).origin;
    return expected === actual;
  } catch {
    return false;
  }
}

export function buildUpstreamUrl(
  apiBaseUrl: string,
  normalizedPath: string,
  search: string,
): URL {
  const targetUrl = new URL(normalizedPath, `${apiBaseUrl.replace(/\/$/, "")}/`);
  targetUrl.search = search;
  return targetUrl;
}
