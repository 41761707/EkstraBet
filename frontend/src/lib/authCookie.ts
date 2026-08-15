/** Edge- and browser-safe auth cookie helpers (no FastAPI URL / server-only). */

export const DEFAULT_AUTH_COOKIE_NAME = "ekstrabet_token";

export function getAuthCookieName(): string {
  return process.env.AUTH_COOKIE_NAME ?? DEFAULT_AUTH_COOKIE_NAME;
}

/** Kill switch; must match backend AUTH_ENABLED. */
export function isAuthEnabled(): boolean {
  const raw = (process.env.AUTH_ENABLED ?? "true").trim().toLowerCase();
  return raw !== "false" && raw !== "0" && raw !== "no" && raw !== "off";
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

/** After login, unfinished first-login accounts go to the completion form. */
export function resolvePostLoginPath(
  firstLogin: boolean,
  next: string | null | undefined,
): string {
  if (firstLogin) {
    return "/first-login";
  }
  return safeInternalPath(next);
}
