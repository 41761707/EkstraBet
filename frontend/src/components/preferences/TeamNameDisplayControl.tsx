"use client";

import { useId } from "react";

import { usePreferences } from "@/components/preferences/PreferencesProvider";
import {
  TEAM_NAME_DISPLAY_PREFERENCES,
  type TeamNameDisplayPreference,
} from "@/lib/preferences";

export const TEAM_NAME_DISPLAY_LABEL = "Nazwy drużyn";
export const TEAM_NAME_DISPLAY_DESCRIPTION =
  "Wybierz pełne nazwy lub skróty w wykresach i progresie ELO.";

export const TEAM_NAME_DISPLAY_OPTION_LABELS: Record<
  TeamNameDisplayPreference,
  string
> = {
  full: "Pełne nazwy",
  shortcut: "Skróty",
};

const SEGMENT_BASE_CLASS =
  "cursor-pointer select-none rounded px-3 py-1 text-sm transition " +
  "has-[:focus-visible]:outline has-[:focus-visible]:outline-2 " +
  "has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus-ring";

const SEGMENT_ACTIVE_CLASS = "bg-accent text-on-accent";
const SEGMENT_IDLE_CLASS = "text-muted hover:text-text";

interface TeamNameDisplayControlProps {
  className?: string;
}

/**
 * Segmented radio group for the team-name display preference. Native radios
 * give keyboard users Tab-to-group + arrow-key navigation, and the visually
 * hidden legend keeps the group labelled for screen readers.
 */
export function TeamNameDisplayControl({
  className = "",
}: TeamNameDisplayControlProps) {
  const { preferences, setTeamNameDisplay } = usePreferences();
  const groupName = useId();

  return (
    <fieldset
      className={
        "inline-flex rounded-md border border-border bg-surface-muted p-0.5 " +
        className
      }
    >
      <legend className="sr-only">{TEAM_NAME_DISPLAY_LABEL}</legend>
      {TEAM_NAME_DISPLAY_PREFERENCES.map((option) => {
        const optionId = `${groupName}-${option}`;
        const isActive = preferences.teamNameDisplay === option;
        return (
          <label
            key={option}
            htmlFor={optionId}
            className={
              SEGMENT_BASE_CLASS +
              " " +
              (isActive ? SEGMENT_ACTIVE_CLASS : SEGMENT_IDLE_CLASS)
            }
          >
            <input
              type="radio"
              id={optionId}
              name={groupName}
              value={option}
              checked={isActive}
              onChange={() => setTeamNameDisplay(option)}
              className="sr-only"
            />
            {TEAM_NAME_DISPLAY_OPTION_LABELS[option]}
          </label>
        );
      })}
    </fieldset>
  );
}
