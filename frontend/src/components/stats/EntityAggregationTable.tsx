import { formatPercent, formatProfit } from "@/lib/format";
import type {
  AccuracyAggregation,
  EntityAggregationRow,
  ProfitAggregation,
} from "@/types/api";

interface EntityAggregationTableProps {
  title: string;
  rows: EntityAggregationRow[];
  metric: "accuracy" | "profit";
}

export function EntityAggregationTable({
  title,
  rows,
  metric,
}: EntityAggregationTableProps) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-700/80">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900/80 text-left text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              {metric === "accuracy" ? (
                <>
                  <th className="px-4 py-3 text-right font-medium">
                    Predictions
                  </th>
                  <th className="px-4 py-3 text-right font-medium">Correct</th>
                  <th className="px-4 py-3 text-right font-medium">Accuracy</th>
                </>
              ) : (
                <th className="px-4 py-3 text-right font-medium">Profit</th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.entity_id ?? "avg"}-${row.entity_name}`}
                className="border-t border-slate-800/80 hover:bg-slate-900/50"
              >
                <td className="px-4 py-3 font-medium text-white">
                  {row.entity_name}
                </td>
                {metric === "accuracy" ? (
                  <>
                    <td className="px-4 py-3 text-right text-slate-200">
                      {row.total_predictions ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-200">
                      {row.correct_predictions ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-sky-200">
                      {formatPercent(row.accuracy_pct)}
                    </td>
                  </>
                ) : (
                  <td className="px-4 py-3 text-right text-amber-200">
                    {formatProfit(row.profit)}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const categoryLabels: Record<string, string> = {
  ou: "Over/Under",
  btts: "BTTS",
  result: "1X2",
};

export function AggregationsSection({
  byTeam,
  byLeague,
}: {
  byTeam: AccuracyAggregation | null;
  byLeague: AccuracyAggregation | ProfitAggregation | null;
}) {
  if (!byTeam && !byLeague) {
    return null;
  }

  return (
    <section className="space-y-8">
      <h2 className="text-2xl font-semibold text-white">Aggregations</h2>

      {byTeam ? (
        <div className="space-y-6">
          {(["ou", "btts", "result"] as const).map((key) => {
            const rows = byTeam[key];
            if (!rows || rows.length === 0) {
              return null;
            }
            return (
              <EntityAggregationTable
                key={`team-${key}`}
                title={`Team accuracy — ${categoryLabels[key]}`}
                rows={rows}
                metric="accuracy"
              />
            );
          })}
        </div>
      ) : null}

      {byLeague ? (
        <div className="space-y-6">
          {(["ou", "btts", "result"] as const).map((key) => {
            const rows = byLeague[key];
            if (!rows || rows.length === 0) {
              return null;
            }
            return (
              <EntityAggregationTable
                key={`league-${key}`}
                title={`League ${byLeague.metric} — ${categoryLabels[key]}`}
                rows={rows}
                metric={byLeague.metric}
              />
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
