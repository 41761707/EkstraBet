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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Event</th>
            <th className="px-4 py-3 font-medium">Model</th>
            <th className="px-4 py-3 text-center font-medium">Probability</th>
            <th className="px-4 py-3 text-center font-medium">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((prediction) => (
            <tr
              key={prediction.prediction_id}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-3 text-white">
                <div>{prediction.event_name}</div>
                {prediction.event_family ? (
                  <div className="text-xs text-slate-500">
                    {prediction.event_family.name}
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3 text-slate-300">
                {prediction.model_name ?? `Model ${prediction.model_id}`}
              </td>
              <td className="px-4 py-3 text-center font-medium text-sky-200">
                {formatProbability(prediction.value)}
              </td>
              <td className="px-4 py-3 text-center text-slate-300">
                {prediction.outcome === null
                  ? "—"
                  : prediction.outcome === 1
                    ? "Hit"
                    : "Miss"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
