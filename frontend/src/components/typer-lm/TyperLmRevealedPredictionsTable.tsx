import { formatMatchDateTime } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import {
  buildRevealedPickLookup,
  formatRevealedPickLabel,
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
    <div className="max-h-[min(70vh,36rem)] overflow-auto rounded-xl border border-border">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <caption className="sr-only">Typy uczestników</caption>
        <thead className="bg-surface-muted text-muted">
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
          `sticky left-0 top-0 z-30 border-r border-border bg-surface-muted ` +
          `px-3 py-2 font-medium ${matchColClass}`
        }
      >
        Mecz
      </th>
      {participants.length === 0 ? (
        <th
          scope="col"
          className={
            `sticky top-0 z-20 whitespace-nowrap bg-surface-muted ` +
            `px-3 py-2 font-medium ${pickColClass}`
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
    <tr className={`${rowClass} text-text`}>
      <th
        scope="row"
        className={
          `sticky left-0 z-10 border-r border-border px-3 py-2 font-medium ` +
          `${matchColClass} ${rowClass}`
        }
      >
        <RevealedMatchLabel match={match} teamNameDisplay={teamNameDisplay} />
      </th>
      {participants.length === 0 ? (
        <td className={`px-3 py-2 ${pickColClass}`}>
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
}: {
  match: TyperRevealedMatch;
  outcome: TyperOutcome | undefined;
  teamNameDisplay: TeamNameDisplayPreference;
  isCurrentUser: boolean;
  pickColClass: string;
}) {
  const highlight = isCurrentUser ? "bg-accent-soft" : "";
  return (
    <td
      className={
        `whitespace-nowrap px-3 py-2 ${pickColClass} ${highlight}`.trim()
      }
    >
      {outcome === undefined ? (
        <MissingPickMark />
      ) : (
        formatRevealedPickLabel(match, outcome, teamNameDisplay)
      )}
    </td>
  );
}

function MissingPickMark() {
  return (
    <span aria-label={EMPTY_PICK_LABEL}>
      {EMPTY_PICK_MARK}
    </span>
  );
}
