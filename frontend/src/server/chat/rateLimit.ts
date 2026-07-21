import { createHash } from "node:crypto";

import { ChatRateLimitError } from "@/server/chat/errors";
import { getAuthCookieName } from "@/lib/auth";

interface RateLimitBucket {
  count: number;
  resetAt: number;
}

const buckets = new Map<string, RateLimitBucket>();

const DEFAULT_WINDOW_MS = 60_000;
const DEFAULT_MAX_REQUESTS = 20;

/**
 * In-memory fixed-window rate limit (per Node process).
 * Limits do NOT aggregate across workers/instances — use a shared store
 * (Redis etc.) when running multiple replicas.
 */
function readIntEnv(name: string, fallback: number): number {
  const raw = process.env[name]?.trim();
  if (!raw) {
    return fallback;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function pruneExpired(now: number): void {
  for (const [key, bucket] of buckets) {
    if (bucket.resetAt <= now) {
      buckets.delete(key);
    }
  }
}

/** In-memory sliding fixed-window rate limit (per process). */
export function assertChatRateLimit(key: string): void {
  const windowMs = readIntEnv("CHAT_RATE_LIMIT_WINDOW_MS", DEFAULT_WINDOW_MS);
  const maxRequests = readIntEnv(
    "CHAT_RATE_LIMIT_MAX_REQUESTS",
    DEFAULT_MAX_REQUESTS,
  );
  const now = Date.now();
  pruneExpired(now);

  const existing = buckets.get(key);
  if (!existing || existing.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return;
  }

  if (existing.count >= maxRequests) {
    const retryAfterSec = Math.max(
      1,
      Math.ceil((existing.resetAt - now) / 1000),
    );
    throw new ChatRateLimitError(
      `Chat rate limit exceeded. Retry after ${retryAfterSec}s.`,
      retryAfterSec,
    );
  }

  existing.count += 1;
}

function readCookieValue(
  cookieHeader: string | null,
  name: string,
): string | null {
  if (!cookieHeader) {
    return null;
  }
  for (const part of cookieHeader.split(";")) {
    const trimmed = part.trim();
    const eq = trimmed.indexOf("=");
    if (eq <= 0) {
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    if (key !== name) {
      continue;
    }
    const value = trimmed.slice(eq + 1).trim();
    return value || null;
  }
  return null;
}

function hashSessionToken(token: string): string {
  return createHash("sha256").update(token).digest("hex").slice(0, 16);
}

function clientIpFromRequest(request: Request): string | null {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) {
      return first;
    }
  }
  const realIp = request.headers.get("x-real-ip")?.trim();
  return realIp || null;
}

/**
 * Prefer authenticated session (hashed cookie) over IP.
 * Falls back to ip:unknown only when neither session nor IP is available
 * (all such clients share one bucket — acceptable only for single-instance).
 */
export function clientKeyFromRequest(request: Request): string {
  const session = readCookieValue(
    request.headers.get("cookie"),
    getAuthCookieName(),
  );
  if (session) {
    return `session:${hashSessionToken(session)}`;
  }
  const ip = clientIpFromRequest(request);
  if (ip) {
    return `ip:${ip}`;
  }
  return "ip:unknown";
}

/** Test helper — clears buckets between cases. */
export function resetChatRateLimitForTests(): void {
  buckets.clear();
}
