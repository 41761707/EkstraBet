import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  PREFERENCES_VERSION,
  THEME_PREFERENCES,
  type ResolvedTheme,
  type ThemePreference,
} from "@/lib/preferences";

export const COLOR_SCHEME_DARK_QUERY = "(prefers-color-scheme: dark)";

/**
 * Resolve a stored preference against the current system color scheme.
 * Explicit dark/light win; `system` follows `systemPrefersDark`.
 */
export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme {
  if (preference === "light" || preference === "dark") {
    return preference;
  }
  return systemPrefersDark ? "dark" : "light";
}

/**
 * Read `prefers-color-scheme`. Missing `matchMedia` falls back to dark
 * so the first paint matches the current (dark-only) UI.
 */
export function getSystemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return true;
  }
  try {
    return window.matchMedia(COLOR_SCHEME_DARK_QUERY).matches;
  } catch {
    return true;
  }
}

/**
 * Apply a resolved theme to the document. No-ops during SSR.
 */
export function applyResolvedTheme(theme: ResolvedTheme): void {
  if (typeof document === "undefined") {
    return;
  }
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

/**
 * Blocking inline script for the root layout. Duplicates a minimal parser
 * because it must run before React; key, version and allowlist are interpolated
 * from the same module as `parsePreferences`.
 *
 * Do not emit `&` / `&&` in the IIFE: Next.js 15 App Router serializes them in
 * the RSC payload as `\u0026\u0026`, which throws SyntaxError on the client.
 */
export function buildThemeBootstrapScript(): string {
  const storageKey = JSON.stringify(PREFERENCES_STORAGE_KEY);
  const version = JSON.stringify(PREFERENCES_VERSION);
  const allowed = JSON.stringify([...THEME_PREFERENCES]);
  const defaultTheme = JSON.stringify(DEFAULT_PREFERENCES.theme);
  const mediaQuery = JSON.stringify(COLOR_SCHEME_DARK_QUERY);

  return (
    `(function(){` +
    `var storageKey=${storageKey};` +
    `var version=${version};` +
    `var allowed=${allowed};` +
    `var theme=${defaultTheme};` +
    `var mediaQuery=${mediaQuery};` +
    `try{` +
    `var raw=localStorage.getItem(storageKey);` +
    `if(raw){` +
    `var parsed=JSON.parse(raw);` +
    `if(parsed){` +
    `if(parsed.version===version){` +
    `if(allowed.indexOf(parsed.theme)!==-1){` +
    `theme=parsed.theme;` +
    `}` +
    `}` +
    `}` +
    `}` +
    `}catch(e){}` +
    `var resolved=theme;` +
    `if(theme==="system"){` +
    `var prefersDark=true;` +
    `try{prefersDark=window.matchMedia(mediaQuery).matches;}catch(e){}` +
    `resolved=prefersDark?"dark":"light";` +
    `}` +
    `var root=document.documentElement;` +
    `root.dataset.theme=resolved;` +
    `root.style.colorScheme=resolved;` +
    `})();`
  );
}
