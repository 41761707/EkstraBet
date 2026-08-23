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
      <h3 className="text-lg font-semibold text-text">{title}</h3>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-surface text-left text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Nazwa</th>
              {metric === "accuracy" ? (
                <>
                  <th className="px-4 py-3 text-right font-medium">
                    Predykcje
                  </th>
                  <th className="px-4 py-3 text-right font-medium">Trafione</th>
                  <th className="px-4 py-3 text-right font-medium">Skuteczność</th>
                </>
              ) : (
                <th className="px-4 py-3 text-right font-medium">Zysk</th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.entity_id ?? "avg"}-${row.entity_name}`}
                className="border-t border-border hover:bg-surface-muted/50"
              >
                <td className="px-4 py-3 font-medium text-text">
                  {row.entity_name}
                </td>
                {metric === "accuracy" ? (
                  <>
                    <td className="px-4 py-3 text-right text-text">
                      {row.total_predictions ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-text">
                      {row.correct_predictions ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-accent-text-hover">
                      {formatPercent(row.accuracy_pct)}
                    </td>
                  </>
                ) : (
                  <td className="px-4 py-3 text-right text-warning-text">
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

const metricLabels: Record<"accuracy" | "profit", string> = {
  accuracy: "Skuteczność",
  profit: "Zysk",
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
      <h2 className="text-2xl font-semibold text-text">Agregacje</h2>

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
                title={`Skuteczność drużyn — ${categoryLabels[key]}`}
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
                title={`${metricLabels[byLeague.metric]} lig — ${categoryLabels[key]}`}
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
