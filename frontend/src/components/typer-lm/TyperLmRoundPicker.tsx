import { formatTyperRoundLabel } from "@/lib/typerLm";
import type { TyperRound } from "@/types/api";

interface TyperLmRoundPickerProps {
  rounds: TyperRound[];
  selectedRound: number | null;
  onSelect: (roundNumber: number) => void;
}

export function TyperLmRoundPicker({
  rounds,
  selectedRound,
  onSelect,
}: TyperLmRoundPickerProps) {
  if (rounds.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-text">Kolejka</h2>
      <div className="flex flex-wrap gap-2">
        {rounds.map((round) => {
          const isActive = round.round_number === selectedRound;
          return (
            <button
              key={round.round_number}
              type="button"
              onClick={() => onSelect(round.round_number)}
              className={`rounded-full px-3 py-1.5 text-sm transition ${
                isActive
                  ? "bg-accent text-on-accent"
                  : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
              }`}
            >
              {formatTyperRoundLabel(round.round_number, round.round_label)}
            </button>
          );
        })}
      </div>
    </section>
  );
}
