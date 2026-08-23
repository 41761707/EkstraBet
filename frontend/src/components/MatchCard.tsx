import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { formatMatchDate, formatRoundLabel } from "@/lib/format";
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
  const roundLabel = formatRoundLabel(match.round_label);

  return (
    <div className="rounded-lg border border-border bg-surface p-4 transition hover:border-accent/40 hover:bg-surface-muted">
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-muted">
        <Link
          href={`/matches/${match.id}`}
          className="transition hover:text-accent-text"
        >
          {formatMatchDate(match.game_date)}
        </Link>
        {roundLabel !== null ? <span>{roundLabel}</span> : null}
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <Link
          href={teamHref(match.home_team.id, seasonId, leagueId)}
          className={`truncate text-right font-medium transition hover:text-accent-text-hover ${
            highlightTeamId === match.home_team.id
              ? "text-accent-text"
              : "text-text"
          }`}
        >
          {match.home_team.name}
        </Link>
        <Link
          href={`/matches/${match.id}`}
          className="text-center transition hover:text-accent-text"
        >
          <MatchScoreDisplay match={match} size="md" />
        </Link>
        <Link
          href={teamHref(match.away_team.id, seasonId, leagueId)}
          className={`truncate font-medium transition hover:text-accent-text-hover ${
            highlightTeamId === match.away_team.id
              ? "text-accent-text"
              : "text-text"
          }`}
        >
          {match.away_team.name}
        </Link>
      </div>
    </div>
  );
}
