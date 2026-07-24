import Link from "next/link";
import { leaguePath } from "@/lib/leaguePaths";
import type { LeagueSummary } from "@/types/api";

interface LeagueCardProps {
  league: LeagueSummary;
}

export function LeagueCard({ league }: LeagueCardProps) {
  const subtitle = [league.country_emoji, league.country_name, league.sport_name]
    .filter(Boolean)
    .join(" · ");

  return (
    <Link
      href={leaguePath(league.slug)}
      className="group block rounded-xl border border-slate-700/80 bg-slate-900/70 p-4 transition hover:border-sky-500/50 hover:bg-slate-900"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white group-hover:text-sky-200">
            {league.name}
          </h2>
          {subtitle ? (
            <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
          ) : null}
        </div>
        {league.active ? (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
            Aktywna
          </span>
        ) : null}
      </div>
      {league.last_update ? (
        <p className="mt-3 text-xs text-slate-500">
          Aktualizacja: {league.last_update}
        </p>
      ) : null}
    </Link>
  );
}
