import { MatchCard } from "@/components/MatchCard";
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
  return (
    <>
      {headToHead.played > 0 ? (
        <div className="mb-4 grid gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4">
          <H2HStat label="Rozegrane" value={headToHead.played} />
          <H2HStat
            label="Bilans (gospodarz)"
            value={`${headToHead.wins}W ${headToHead.draws}D ${headToHead.losses}L`}
          />
          <H2HStat
            label="Bramki"
            value={`${headToHead.goals_for}:${headToHead.goals_conceded}`}
          />
          {!isHockey ? (
            <H2HStat
              label="BTTS"
              value={`${headToHead.btts_percentage.toFixed(1)}%`}
            />
          ) : null}
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
