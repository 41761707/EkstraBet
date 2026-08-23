import { formatProbability } from "@/lib/format";
import type { MatchPredictionItem } from "@/types/api";

interface MatchPredictionsTableProps {
  predictions: MatchPredictionItem[];
}

export function MatchPredictionsTable({
  predictions,
}: MatchPredictionsTableProps) {
  if (predictions.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Zdarzenie</th>
            <th className="px-4 py-3 font-medium">Model</th>
            <th className="px-4 py-3 text-center font-medium">
              Prawdopodobieństwo
            </th>
            <th className="px-4 py-3 text-center font-medium">Wynik</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((prediction) => (
            <tr
              key={prediction.prediction_id}
              className="border-t border-border hover:bg-surface-muted"
            >
              <td className="px-4 py-3 text-text">
                <div>{prediction.event_name}</div>
                {prediction.event_family ? (
                  <div className="text-xs text-subtle">
                    {prediction.event_family.name}
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3 text-muted">
                {prediction.model_name ?? `Model ${prediction.model_id}`}
              </td>
              <td className="px-4 py-3 text-center font-medium text-accent-text">
                {formatProbability(prediction.value)}
              </td>
              <td className="px-4 py-3 text-center text-muted">
                {prediction.outcome === null
                  ? "—"
                  : prediction.outcome === 1
                    ? "Poprawny"
                    : "Błędny"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
