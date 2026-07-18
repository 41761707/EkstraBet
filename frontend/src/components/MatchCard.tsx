import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { formatMatchDate } from "@/lib/format";
import type { MatchSummary } from "@/types/api";

interface MatchCardProps {
  match: MatchSummary;
  highlightTeamId?: number;
  seasonId?: number;
  leagueId?: number;
}

function teamHref(
  teamId: number,
  seasonId?: number,
  leagueId?: number,
): string {
  const params = new URLSearchParams();
  if (seasonId) {
    params.set("season_id", String(seasonId));
  }
  if (leagueId) {
    params.set("league_id", String(leagueId));
  }
  const query = params.toString();
  return query ? `/teams/${teamId}?${query}` : `/teams/${teamId}`;
}

export function MatchCard({
  match,
  highlightTeamId,
  seasonId,
  leagueId,
}: MatchCardProps) {
  return (
    <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4 transition hover:border-sky-500/40 hover:bg-slate-900/80">
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-slate-400">
        <Link
          href={`/matches/${match.id}`}
          className="transition hover:text-sky-300"
        >
          {formatMatchDate(match.game_date)}
        </Link>
        {match.round_label !== null ? <span>{match.round_label}</span> : null}
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <Link
          href={teamHref(match.home_team.id, seasonId, leagueId)}
          className={`truncate text-right font-medium transition hover:text-sky-200 ${
            highlightTeamId === match.home_team.id
              ? "text-sky-200"
              : "text-white"
          }`}
        >
          {match.home_team.name}
        </Link>
        <Link
          href={`/matches/${match.id}`}
          className="text-center transition hover:text-sky-100"
        >
          <MatchScoreDisplay match={match} size="md" />
        </Link>
        <Link
          href={teamHref(match.away_team.id, seasonId, leagueId)}
          className={`truncate font-medium transition hover:text-sky-200 ${
            highlightTeamId === match.away_team.id
              ? "text-sky-200"
              : "text-white"
          }`}
        >
          {match.away_team.name}
        </Link>
      </div>
    </div>
  );
}
