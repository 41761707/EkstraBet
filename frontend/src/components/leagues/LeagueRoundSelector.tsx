import Link from "next/link";
import { leaguePath } from "@/lib/leaguePaths";
import type { LeagueRound } from "@/types/api";

interface LeagueRoundSelectorProps {
  leagueSlug: string;
  seasonId: number;
  rounds: LeagueRound[];
  selectedRound: number;
}

function buildLeagueHref(
  leagueSlug: string,
  seasonId: number,
  roundNumber: number,
): string {
  return leaguePath(leagueSlug, {
    season_id: seasonId,
    round: roundNumber,
  });
}

export function LeagueRoundSelector({
  leagueSlug,
  seasonId,
  rounds,
  selectedRound,
}: LeagueRoundSelectorProps) {
  if (rounds.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-white">Kolejka</h2>
      <div className="flex flex-wrap gap-2">
        {rounds.map((round) => {
          const isActive = round.round_number === selectedRound;
          return (
            <Link
              key={round.round_number}
              href={buildLeagueHref(leagueSlug, seasonId, round.round_number)}
              className={`rounded-full px-3 py-1.5 text-sm transition ${
                isActive
                  ? "bg-sky-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {round.round_label}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
