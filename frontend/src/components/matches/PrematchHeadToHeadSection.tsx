import { MatchCard } from "@/components/MatchCard";
import {
  h2hOverLine,
  summarizeDisplayedHeadToHead,
} from "@/components/matches/prematchHeadToHeadSummary";
import { StatusMessage } from "@/components/StatusMessage";
import type { HeadToHeadSummary, MatchSummary } from "@/types/api";

interface PrematchHeadToHeadSectionProps {
  headToHead: HeadToHeadSummary;
  meetings: MatchSummary[];
  isHockey: boolean;
  seasonId: number;
  leagueId: number;
}

function H2HStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-subtle">{label}</p>
      <p className="mt-1 text-lg font-semibold text-text">{value}</p>
    </div>
  );
}

export function PrematchHeadToHeadSection({
  headToHead,
  meetings,
  isHockey,
  seasonId,
  leagueId,
}: PrematchHeadToHeadSectionProps) {
  const stats = summarizeDisplayedHeadToHead(
    headToHead.team_id,
    meetings,
    isHockey,
  );
  const overLabel = `Over ${h2hOverLine(isHockey).toFixed(1)}`;
  const statsGridClass = isHockey
    ? "mb-4 grid gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4"
    : "mb-4 grid gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-5";

  return (
    <>
      {stats.played > 0 ? (
        <div className={statsGridClass}>
          <H2HStat label="Rozegrane" value={stats.played} />
          <H2HStat
            label="Bilans (gospodarz)"
            value={`${stats.wins}W ${stats.draws}D ${stats.losses}L`}
          />
          <H2HStat
            label="Bramki"
            value={`${stats.goalsFor}:${stats.goalsConceded}`}
          />
          {!isHockey ? (
            <H2HStat
              label="BTTS"
              value={`${stats.bttsPercentage.toFixed(1)}%`}
            />
          ) : null}
          <H2HStat
            label={overLabel}
            value={`${stats.overPercentage.toFixed(1)}%`}
          />
        </div>
      ) : null}
      {meetings.length > 0 ? (
        <div className="grid gap-3">
          {meetings.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              seasonId={seasonId}
              leagueId={leagueId}
            />
          ))}
        </div>
      ) : (
        <StatusMessage
          variant="empty"
          title="Brak spotkań H2H"
          message="Brak bezpośrednich spotkań między drużynami w bazie danych."
        />
      )}
    </>
  );
}
