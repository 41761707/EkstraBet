import { formatOdds } from "@/lib/format";
import type { TyperLeaderboardRow } from "@/types/api";

import { StatusMessage } from "@/components/StatusMessage";

const HEADER_CELL =
  "whitespace-nowrap px-4 pb-2 pt-1 text-xs font-semibold uppercase " +
  "tracking-wide text-muted";
const BODY_CELL = "border-y border-border px-4 py-3.5 align-middle";

interface TyperLmLeaderboardProps {
  rows: TyperLeaderboardRow[];
  currentUserUuid: string;
}

export function TyperLmLeaderboard({
  rows,
  currentUserUuid,
}: TyperLmLeaderboardProps) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Ranking jest pusty"
        message="Punkty pojawią się po rozstrzygnięciu pierwszych typów."
      />
    );
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-text">Ranking</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] border-separate border-spacing-y-2 text-left text-sm">
          <caption className="sr-only">Ranking Typer LM</caption>
          <LeaderboardHead />
          <tbody>
            {rows.map((row) => (
              <LeaderboardRow
                key={row.user_uuid}
                row={row}
                isCurrentUser={row.user_uuid === currentUserUuid}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LeaderboardHead() {
  return (
    <thead>
      <tr>
        <th className={HEADER_CELL} scope="col">
          Miejsce
        </th>
        <th className={HEADER_CELL} scope="col">
          Gracz
        </th>
        <th className={`${HEADER_CELL} text-right`} scope="col">
          Mecze
        </th>
        <th className={`${HEADER_CELL} text-right`} scope="col">
          Długoterminowe
        </th>
        <th className={`${HEADER_CELL} text-right text-text`} scope="col">
          Suma
        </th>
        <th className={`${HEADER_CELL} border-l border-border text-right`} scope="col">
          Trafienia
        </th>
        <th className={`${HEADER_CELL} text-right`} scope="col">
          Rozstrzygnięte
        </th>
      </tr>
    </thead>
  );
}

function LeaderboardRow({
  row,
  isCurrentUser,
}: {
  row: TyperLeaderboardRow;
  isCurrentUser: boolean;
}) {
  const tone = isCurrentUser
    ? "bg-accent-soft"
    : "bg-surface group-hover:bg-surface-muted";
  const cell = `${BODY_CELL} ${tone} transition-colors`;

  return (
    <tr className="group text-text">
      <td className={`${cell} rounded-l-xl border-l`}>
        <PlaceMark place={row.place} />
      </td>
      <td className={`${cell} font-medium`}>
        <span>{row.display_name}</span>
        {isCurrentUser ? <CurrentUserMark /> : null}
      </td>
      <td className={`${cell} text-right tabular-nums`}>
        {formatOdds(row.match_points)}
      </td>
      <td className={`${cell} text-right tabular-nums`}>
        {formatOdds(row.long_term_points)}
      </td>
      <td className={`${cell} text-right text-base font-semibold tabular-nums`}>
        {formatOdds(row.total_points)}
      </td>
      <td className={`${cell} border-l text-right tabular-nums`}>
        {row.correct_predictions}
      </td>
      <td className={`${cell} rounded-r-xl border-r text-right tabular-nums`}>
        {row.settled_predictions}
      </td>
    </tr>
  );
}

function PlaceMark({ place }: { place: number }) {
  return (
    <span
      className={
        "inline-flex h-7 w-7 items-center justify-center rounded-full " +
        "text-xs font-semibold tabular-nums " +
        placeTone(place)
      }
    >
      {place}
    </span>
  );
}

function placeTone(place: number): string {
  if (place === 1) {
    return "bg-warning-bg text-warning-text";
  }
  if (place === 2) {
    return "bg-surface-muted text-text ring-1 ring-border-strong";
  }
  if (place === 3) {
    return "bg-surface-muted text-text ring-1 ring-border";
  }
  return "text-muted";
}

function CurrentUserMark() {
  return (
    <span className="ml-2 inline-flex rounded-full bg-accent px-2 py-0.5 align-middle text-xs font-medium text-on-accent">
      Ty
    </span>
  );
}
