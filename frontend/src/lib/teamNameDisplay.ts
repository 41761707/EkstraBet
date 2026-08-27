import type { TeamNameDisplayPreference } from "@/lib/preferences";

/**
 * Format a team label for abbreviation-capable UI.
 * Shortcut mode uses a trimmed shortcut and falls back to the full name
 * when the shortcut is missing or blank.
 */
export function formatTeamName(
  fullName: string,
  shortcut: string | null | undefined,
  preference: TeamNameDisplayPreference,
): string {
  if (preference !== "shortcut") {
    return fullName;
  }
  const trimmedShortcut = shortcut?.trim();
  return trimmedShortcut ? trimmedShortcut : fullName;
}
