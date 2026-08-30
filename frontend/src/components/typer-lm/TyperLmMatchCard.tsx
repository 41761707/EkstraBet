import { formatMatchDateTime } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import {
  formatPredictionChangeLine,
  formatTyperOddsValue,
  formatTyperPointsLabel,
  formatTyperResultLabel,
  isTyperMatchLockedForUi,
  isTyperOddsPlaceholderVisible,
  takeRecentPredictionChanges,
  TYPER_LM_ODDS_PLACEHOLDER,
} from "@/lib/typerLm";
import type { TyperMatch, TyperOutcome } from "@/types/api";

import { TyperLmOutcomeButtons } from "./TyperLmOutcomeButtons";

interface TyperLmMatchCardProps {
  match: TyperMatch;
  teamNameDisplay: TeamNameDisplayPreference;
  isPending: boolean;
  nowMs?: number | null;
  errorMessage?: string;
  onSelectOutcome: (outcome: TyperOutcome) => void;
}

export function TyperLmMatchCard({
  match,
  teamNameDisplay,
  isPending,
  nowMs,
  errorMessage,
  onSelectOutcome,
}: TyperLmMatchCardProps) {
  const isLocked = isTyperMatchLockedForUi(match, nowMs);
  const homeName = formatTeamName(
    match.home_team.name,
    match.home_team.shortcut,
    teamNameDisplay,
  );
  const awayName = formatTeamName(
    match.away_team.name,
    match.away_team.shortcut,
    teamNameDisplay,
  );
  const recentChanges = takeRecentPredictionChanges(match.changes);
  const showOddsPlaceholder = isTyperOddsPlaceholderVisible(match);
  const resultLabel = formatTyperResultLabel(match, nowMs);

  return (
    <article className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <header className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <time dateTime={match.game_date}>
          {formatMatchDateTime(match.game_date)}
        </time>
        <span>
          {isLocked ? "Typowanie zablokowane" : "Do rozpoczęcia"}
        </span>
      </header>

      <p className="text-center text-base font-semibold text-text">
        {homeName} — {awayName}
      </p>

      {showOddsPlaceholder ? (
        <p className="text-center text-sm text-muted">
          {TYPER_LM_ODDS_PLACEHOLDER}
        </p>
      ) : (
        <dl className="grid grid-cols-3 gap-2 text-center text-sm">
          <OddsCell label="1" value={match.odds_home} />
          <OddsCell label="X" value={match.odds_draw} />
          <OddsCell label="2" value={match.odds_away} />
        </dl>
      )}

      <TyperLmOutcomeButtons
        match={match}
        isPending={isPending}
        isLocked={isLocked}
        onSelect={onSelectOutcome}
      />

      <p className="text-sm text-muted">
        {resultLabel ? (
          <>
            <span className="font-medium text-text">{resultLabel}</span>
            {" · "}
          </>
        ) : null}
        Punkty:{" "}
        <span className="font-medium text-text">
          {formatTyperPointsLabel(match)}
        </span>
      </p>

      {isPending ? (
        <p className="text-sm text-accent-text" role="status">
          Zapisywanie typu…
        </p>
      ) : null}

      {errorMessage ? (
        <p className="text-sm text-danger-text" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {recentChanges.length > 0 ? (
        <ul className="space-y-1 text-xs text-subtle">
          {recentChanges.map((change) => (
            <li key={`${change.changed_at}-${change.new_outcome}`}>
              {formatPredictionChangeLine(change)}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function OddsCell({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted px-2 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-medium text-text">{formatTyperOddsValue(value)}</dd>
    </div>
  );
}
