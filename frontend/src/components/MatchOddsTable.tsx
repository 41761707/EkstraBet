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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Bukmacher</th>
            <th className="px-4 py-3 font-medium">Wydarzenie</th>
            <th className="px-4 py-3 text-center font-medium">Kurs</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((item) => (
            <tr
              key={item.id}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-3 text-white">{item.bookmaker_name}</td>
              <td className="px-4 py-3 text-slate-300">
                <div>{item.event_name}</div>
                {item.event_family ? (
                  <div className="text-xs text-slate-500">
                    {item.event_family.name}
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3 text-center font-semibold text-emerald-300">
                {formatOdds(item.odds)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
