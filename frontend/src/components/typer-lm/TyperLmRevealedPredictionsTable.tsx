import { formatMatchDateTime } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import {
  buildRevealedPickLookup,
  formatRevealedPickLabel,
  revealedPickVerdict,
  type RevealedPickVerdict,
} from "@/lib/typerLmRevealed";
import type {
  TyperOutcome,
  TyperRevealedMatch,
  TyperRevealedParticipant,
} from "@/types/api";

const EMPTY_PICK_MARK = "—";
const EMPTY_PICK_LABEL = "Brak typu";
const NO_PICKS_COLUMN_LABEL = "Brak oddanych typów";

interface TyperLmRevealedPredictionsTableProps {
  matches: TyperRevealedMatch[];
  participants: TyperRevealedParticipant[];
  currentUserUuid: string;
  teamNameDisplay: TeamNameDisplayPreference;
}

export function TyperLmRevealedPredictionsTable({
  matches,
  participants,
  currentUserUuid,
  teamNameDisplay,
}: TyperLmRevealedPredictionsTableProps) {
  const lookup = buildRevealedPickLookup(matches);
  const pickColClass =
    teamNameDisplay === "full" ? "min-w-44" : "min-w-28";
  const matchColClass =
    teamNameDisplay === "full" ? "min-w-52" : "min-w-36";

  return (
    <div className="space-y-2">
      <div className="max-h-[min(70vh,36rem)] overflow-auto rounded-xl border border-border">
        <table
          className={
            "min-w-full border-separate border-spacing-px bg-pick-grid " +
            "text-left text-sm"
          }
        >
          <caption className="sr-only">Typy uczestników</caption>
          <thead className="text-muted">
            <RevealedTableHead
              participants={participants}
              currentUserUuid={currentUserUuid}
              matchColClass={matchColClass}
              pickColClass={pickColClass}
            />
          </thead>
          <tbody>
            {matches.map((match, rowIndex) => (
              <RevealedTableRow
                key={match.match_id}
                match={match}
                participants={participants}
                currentUserUuid={currentUserUuid}
                teamNameDisplay={teamNameDisplay}
                lookup={lookup}
                rowIndex={rowIndex}
                matchColClass={matchColClass}
                pickColClass={pickColClass}
              />
            ))}
          </tbody>
        </table>
      </div>
      <RevealedPickLegend />
    </div>
  );
}

function RevealedPickLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
      <span className="font-medium text-text">Legenda</span>
      <span className="inline-flex items-center gap-2">
        <span
          aria-hidden="true"
          className="h-4 w-8 rounded-sm border border-border bg-pick-hit-bg"
        />
        Trafiony typ
      </span>
      <span className="inline-flex items-center gap-2">
        <span
          aria-hidden="true"
          className="h-4 w-8 rounded-sm border border-border bg-pick-miss-bg"
        />
        Nietrafiony typ
      </span>
    </div>
  );
}

function RevealedTableHead({
  participants,
  currentUserUuid,
  matchColClass,
  pickColClass,
}: {
  participants: TyperRevealedParticipant[];
  currentUserUuid: string;
  matchColClass: string;
  pickColClass: string;
}) {
  return (
    <tr>
      <th
        scope="col"
        className={
          `sticky left-0 top-0 z-30 bg-surface-muted px-3 py-2 font-medium ` +
          `${matchColClass}`
        }
      >
        Mecz
      </th>
      {participants.length === 0 ? (
        <th
          scope="col"
          className={
            `sticky top-0 z-20 whitespace-nowrap bg-surface-muted px-3 py-2 ` +
            `font-medium ${pickColClass}`
          }
        >
          {NO_PICKS_COLUMN_LABEL}
        </th>
      ) : (
        participants.map((participant) => (
          <th
            key={participant.user_uuid}
            scope="col"
            className={participantHeaderClass(
              participant.user_uuid === currentUserUuid,
              pickColClass,
            )}
          >
            {participant.display_name}
          </th>
        ))
      )}
    </tr>
  );
}

function participantHeaderClass(
  isCurrentUser: boolean,
  pickColClass: string,
): string {
  const highlight = isCurrentUser
    ? "bg-accent-soft text-text"
    : "bg-surface-muted";
  return (
    `sticky top-0 z-20 whitespace-nowrap px-3 py-2 font-medium ` +
    `${pickColClass} ${highlight}`
  );
}

function RevealedTableRow({
  match,
  participants,
  currentUserUuid,
  teamNameDisplay,
  lookup,
  rowIndex,
  matchColClass,
  pickColClass,
}: {
  match: TyperRevealedMatch;
  participants: TyperRevealedParticipant[];
  currentUserUuid: string;
  teamNameDisplay: TeamNameDisplayPreference;
  lookup: Map<number, Map<string, TyperOutcome>>;
  rowIndex: number;
  matchColClass: string;
  pickColClass: string;
}) {
  const rowClass = rowIndex % 2 === 0 ? "bg-surface" : "bg-surface-muted";
  const picksByUser = lookup.get(match.match_id);

  return (
    <tr className="text-text">
      <th
        scope="row"
        className={
          `sticky left-0 z-10 px-3 py-2 font-medium ` +
          `${matchColClass} ${rowClass}`
        }
      >
        <RevealedMatchLabel match={match} teamNameDisplay={teamNameDisplay} />
      </th>
      {participants.length === 0 ? (
        <td className={`px-3 py-2 ${pickColClass} ${rowClass}`}>
          <MissingPickMark />
        </td>
      ) : (
        participants.map((participant) => (
          <RevealedPickCell
            key={participant.user_uuid}
            match={match}
            outcome={picksByUser?.get(participant.user_uuid)}
            teamNameDisplay={teamNameDisplay}
            isCurrentUser={participant.user_uuid === currentUserUuid}
            pickColClass={pickColClass}
            rowClass={rowClass}
          />
        ))
      )}
    </tr>
  );
}

function RevealedMatchLabel({
  match,
  teamNameDisplay,
}: {
  match: TyperRevealedMatch;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
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
  return (
    <div className="whitespace-nowrap">
      <span>{homeName} – {awayName}</span>
      <span className="mt-0.5 block text-xs font-normal text-muted">
        {formatMatchDateTime(match.game_date)}
      </span>
    </div>
  );
}

function RevealedPickCell({
  match,
  outcome,
  teamNameDisplay,
  isCurrentUser,
  pickColClass,
  rowClass,
}: {
  match: TyperRevealedMatch;
  outcome: TyperOutcome | undefined;
  teamNameDisplay: TeamNameDisplayPreference;
  isCurrentUser: boolean;
  pickColClass: string;
  rowClass: string;
}) {
  const verdict = revealedPickVerdict(match.result, outcome);
  return (
    <td
      className={revealedPickCellClass(
        isCurrentUser,
        verdict,
        pickColClass,
        rowClass,
      )}
    >
      <RevealedPickVerdictLabel verdict={verdict} />
      {outcome === undefined ? (
        <MissingPickMark />
      ) : (
        formatRevealedPickLabel(match, outcome, teamNameDisplay)
      )}
    </td>
  );
}

function revealedPickCellClass(
  isCurrentUser: boolean,
  verdict: RevealedPickVerdict | null,
  pickColClass: string,
  rowClass: string,
): string {
  const tone =
    verdict === "hit"
      ? "bg-pick-hit-bg"
      : verdict === "miss"
        ? "bg-pick-miss-bg"
        : isCurrentUser
          ? "bg-accent-soft"
          : rowClass;
  return `whitespace-nowrap px-3 py-2 ${pickColClass} ${tone}`;
}

function RevealedPickVerdictLabel({
  verdict,
}: {
  verdict: RevealedPickVerdict | null;
}) {
  if (verdict === null) {
    return null;
  }
  const label = verdict === "hit" ? "Trafiony typ" : "Nietrafiony typ";
  return <span className="sr-only">{label}. </span>;
}

function MissingPickMark() {
  return (
    <span aria-label={EMPTY_PICK_LABEL}>
      {EMPTY_PICK_MARK}
    </span>
  );
}
