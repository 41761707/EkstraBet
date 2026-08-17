/**
 * Client-only navigation helpers. Call from event handlers, not during render.
 */

/** Full document load after Set-Cookie so middleware sees the new session. */
export function navigateAfterAuth(path: string): void {
  window.location.replace(path);
}

export interface SearchRouter {
  push: (href: string, options?: { scroll?: boolean }) => void;
  refresh: () => void;
}

export function isCurrentPath(path: string): boolean {
  const current = `${window.location.pathname}${window.location.search}`;
  return decodeURIComponent(current) === decodeURIComponent(path);
}

/**
 * Update the query string through the App Router so Server Components re-fetch.
 *
 * `history.pushState` + `router.refresh()` looks like it works, but Next.js
 * treats an external pushState as ACTION_RESTORE (URL only) and discards a
 * same-tick ACTION_REFRESH. The first Apply click then only changes the
 * address bar; the second click finally refreshes data.
 */
export function navigateSearch(path: string, router: SearchRouter): void {
  if (isCurrentPath(path)) {
    // Next.js discards refresh in the same tick as pushState — defer it.
    setTimeout(() => router.refresh(), 0);
    return;
  }
  router.push(path, { scroll: false });
}
