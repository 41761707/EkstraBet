import { formatOdds } from "@/lib/format";
import type { OddsItem } from "@/types/api";

interface MatchOddsTableProps {
  odds: OddsItem[];
}

export function MatchOddsTable({ odds }: MatchOddsTableProps) {
  if (odds.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Bukmacher</th>
            <th className="px-4 py-3 font-medium">Zdarzenie</th>
            <th className="px-4 py-3 text-center font-medium">Kurs</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((item) => (
            <tr
              key={item.id}
              className="border-t border-border hover:bg-surface-muted"
            >
              <td className="px-4 py-3 text-text">{item.bookmaker_name}</td>
              <td className="px-4 py-3 text-muted">
                <div>{item.event_name}</div>
                {item.event_family ? (
                  <div className="text-xs text-subtle">
                    {item.event_family.name}
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3 text-center font-semibold text-success">
                {formatOdds(item.odds)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
