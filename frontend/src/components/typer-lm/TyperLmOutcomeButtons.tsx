import { TYPER_OUTCOMES } from "@/lib/typerLm";
import type { TyperMatch, TyperOutcome } from "@/types/api";

interface TyperLmOutcomeButtonsProps {
  match: TyperMatch;
  isPending: boolean;
  isLocked: boolean;
  onSelect: (outcome: TyperOutcome) => void;
}

const OUTCOME_LABELS: Record<TyperOutcome, string> = {
  "1": "1",
  X: "X",
  "2": "2",
};

export function TyperLmOutcomeButtons({
  match,
  isPending,
  isLocked,
  onSelect,
}: TyperLmOutcomeButtonsProps) {
  const isDisabled = isLocked || isPending;

  return (
    <div
      className="grid grid-cols-3 gap-2"
      role="group"
      aria-label="Typ 1X2"
    >
      {TYPER_OUTCOMES.map((outcome) => {
        const isSelected = match.outcome === outcome;
        return (
          <button
            key={outcome}
            type="button"
            disabled={isDisabled}
            aria-pressed={isSelected}
            aria-label={`Typ ${OUTCOME_LABELS[outcome]}`}
            onClick={() => onSelect(outcome)}
            className={`rounded-lg border px-3 py-2 text-sm font-semibold transition ${
              isSelected
                ? "border-accent bg-accent text-on-accent"
                : "border-border bg-surface text-text hover:border-accent/40 hover:bg-surface-muted"
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {OUTCOME_LABELS[outcome]}
          </button>
        );
      })}
    </div>
  );
}
