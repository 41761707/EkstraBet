import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  formatTyperOutcomeButtonLabel,
  TYPER_OUTCOMES,
} from "@/lib/typerLm";
import type { TyperMatch, TyperOutcome } from "@/types/api";

interface TyperLmOutcomeButtonsProps {
  match: TyperMatch;
  teamNameDisplay: TeamNameDisplayPreference;
  isPending: boolean;
  isLocked: boolean;
  onSelect: (outcome: TyperOutcome) => void;
}

const SELECTED_BUTTON_CLASS_NAME = "border-accent bg-accent text-on-accent";
const IDLE_BUTTON_CLASS_NAME =
  "border-border bg-surface text-text hover:border-accent/40 " +
  "hover:bg-surface-muted";
const BASE_BUTTON_CLASS_NAME =
  "rounded-lg border px-2 py-2 text-center text-xs font-semibold " +
  "leading-snug break-words transition sm:px-3 sm:text-sm";

export function TyperLmOutcomeButtons({
  match,
  teamNameDisplay,
  isPending,
  isLocked,
  onSelect,
}: TyperLmOutcomeButtonsProps) {
  const isDisabled = isLocked || isPending;

  return (
    <div
      className="grid grid-cols-3 gap-2"
      role="group"
      aria-label="Typ gospodarza, remisu albo gościa"
    >
      {TYPER_OUTCOMES.map((outcome) => {
        const isSelected = match.outcome === outcome;
        const label = formatTyperOutcomeButtonLabel(
          match,
          outcome,
          teamNameDisplay,
        );
        return (
          <button
            key={outcome}
            type="button"
            disabled={isDisabled}
            aria-pressed={isSelected}
            aria-label={`Typ ${label}`}
            onClick={() => onSelect(outcome)}
            className={`${BASE_BUTTON_CLASS_NAME} ${
              isSelected ? SELECTED_BUTTON_CLASS_NAME : IDLE_BUTTON_CLASS_NAME
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
