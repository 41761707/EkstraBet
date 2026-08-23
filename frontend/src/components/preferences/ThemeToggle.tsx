"use client";

import { useEffect, useState } from "react";

import { usePreferences } from "@/components/preferences/PreferencesProvider";
import type { ResolvedTheme } from "@/lib/preferences";

const TOGGLE_CLASS_NAME =
  "inline-flex items-center justify-center rounded-md p-2 text-muted " +
  "transition hover:bg-surface-muted hover:text-text " +
  "focus-visible:outline focus-visible:outline-2 " +
  "focus-visible:outline-offset-2 focus-visible:outline-focus-ring";

const GENERIC_LABEL = "Przełącz motyw";

/** Accessible label describing the action the toggle will perform. */
export function themeToggleLabel(
  isMounted: boolean,
  resolvedTheme: ResolvedTheme,
): string {
  if (!isMounted) {
    return GENERIC_LABEL;
  }
  return resolvedTheme === "dark"
    ? "Przełącz na jasny motyw"
    : "Przełącz na ciemny motyw";
}

/**
 * Binary theme switch. Icon and action label wait until mount so SSR markup
 * does not disagree with the bootstrapped `data-theme`.
 */
export function ThemeToggle() {
  const { resolvedTheme, toggleTheme } = usePreferences();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const label = themeToggleLabel(isMounted, resolvedTheme);

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className={TOGGLE_CLASS_NAME}
    >
      {isMounted ? (
        resolvedTheme === "dark" ? (
          <SunIcon />
        ) : (
          <MoonIcon />
        )
      ) : (
        <span className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );
}

function SunIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2" />
      <path d="M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4" />
      <path d="M5.2 18.8l1.4-1.4M17.4 6.6l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z" />
    </svg>
  );
}
