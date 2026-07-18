import Link from "next/link";
import { leaguePath } from "@/lib/leaguePaths";
import { StatusMessage } from "@/components/StatusMessage";
import type { LeagueSummary } from "@/types/api";

interface HomeLeaguesListProps {
  leagues: LeagueSummary[];
  errorMessage?: string;
}

export function HomeLeaguesList({ leagues, errorMessage }: HomeLeaguesListProps) {
  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować lig"
        message={errorMessage}
      />
    );
  }

  if (leagues.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak aktywnych lig"
        message="API zwróciło pustą listę. Sprawdź dane w backendzie."
      />
    );
  }

  return (
    <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {leagues.map((league) => (
        <li key={league.id}>
          <Link
            href={leaguePath(league.slug)}
            className="flex items-center gap-2 rounded-lg border border-slate-700/60 bg-slate-800/40 px-3 py-2 text-sm text-slate-200 transition hover:border-sky-500/40 hover:bg-slate-800 hover:text-white"
          >
            {league.country_emoji ? (
              <span aria-hidden="true">{league.country_emoji}</span>
            ) : null}
            <span>{league.name}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
