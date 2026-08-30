import { formatOdds } from "@/lib/format";
import type { TyperLeaderboardRow } from "@/types/api";

import { StatusMessage } from "@/components/StatusMessage";

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
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-surface-muted text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Miejsce</th>
              <th className="px-3 py-2 font-medium">Gracz</th>
              <th className="px-3 py-2 font-medium">Punkty</th>
              <th className="px-3 py-2 font-medium">Trafienia</th>
              <th className="px-3 py-2 font-medium">Rozstrzygnięte</th>
            </tr>
          </thead>
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

function LeaderboardRow({
  row,
  isCurrentUser,
}: {
  row: TyperLeaderboardRow;
  isCurrentUser: boolean;
}) {
  return (
    <tr
      className={
        isCurrentUser
          ? "bg-accent-soft text-text"
          : "bg-surface text-text even:bg-surface-muted"
      }
    >
      <td className="px-3 py-2">{row.place}</td>
      <td className="px-3 py-2">
        <span className="font-medium">{row.display_name}</span>
        <span className="mt-0.5 block text-xs text-subtle">{row.user_uuid}</span>
      </td>
      <td className="px-3 py-2">{formatOdds(row.total_points)}</td>
      <td className="px-3 py-2">{row.correct_predictions}</td>
      <td className="px-3 py-2">{row.settled_predictions}</td>
    </tr>
  );
}
