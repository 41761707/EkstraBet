/**
 * Client-only navigation helpers. Call from event handlers, not during render.
 */

/** Full document load after Set-Cookie so middleware sees the new session. */
export function navigateAfterAuth(path: string): void {
  window.location.replace(path);
}

/**
 * Update the query string and re-render Server Components for the new URL.
 * `router.push` on the same pathname is unreliable in production.
 */
export function navigateSearch(path: string, refresh: () => void): void {
  const current = `${window.location.pathname}${window.location.search}`;
  if (current !== path) {
    window.history.pushState(null, "", path);
  }
  refresh();
}
