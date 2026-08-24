import Link from "next/link";
import {
  sportLeaguePath,
  SPORT_PLAYOFFS_PHASE,
  SPORT_REGULAR_SEASON_PHASE,
} from "@/lib/sportLeagueParams";

interface SportLeaguePhaseSelectorProps {
  leagueSlug: string;
  seasonId: number;
  selectedPhase: number;
  dateFilter: boolean;
  dateFrom: string;
  dateTo: string;
}

const PHASES = [
  { value: SPORT_REGULAR_SEASON_PHASE, label: "Sezon zasadniczy" },
  { value: SPORT_PLAYOFFS_PHASE, label: "Playoffy" },
] as const;

export function SportLeaguePhaseSelector({
  leagueSlug,
  seasonId,
  selectedPhase,
  dateFilter,
  dateFrom,
  dateTo,
}: SportLeaguePhaseSelectorProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-text">Faza sezonu</h2>
      <div className="flex flex-wrap gap-2">
        {PHASES.map((phase) => {
          const isActive = phase.value === selectedPhase;
          return (
            <Link
              key={phase.value}
              href={sportLeaguePath(leagueSlug, {
                seasonId: seasonId,
                phase: phase.value,
                dateFilter,
                dateFrom,
                dateTo,
              })}
              scroll={false}
              className={`rounded-full px-3 py-1.5 text-sm transition ${
                isActive
                  ? "bg-accent text-on-accent"
                  : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
              }`}
            >
              {phase.label}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
