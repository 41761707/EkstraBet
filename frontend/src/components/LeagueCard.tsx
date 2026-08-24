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
      className="group block rounded-xl border border-border bg-surface p-4 transition hover:border-accent/50 hover:bg-surface-muted"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-text group-hover:text-accent-text">
            {league.name}
          </h2>
          {subtitle ? (
            <p className="mt-1 text-sm text-muted">{subtitle}</p>
          ) : null}
        </div>
        {league.active ? (
          <span className="rounded-full bg-success-bg px-2 py-0.5 text-xs text-success">
            Aktywna
          </span>
        ) : null}
      </div>
      {league.last_update ? (
        <p className="mt-3 text-xs text-subtle">
          Aktualizacja: {league.last_update}
        </p>
      ) : null}
    </Link>
  );
}
