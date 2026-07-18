import { ChatChartRenderer } from "@/components/chat/ChatChartRenderer";
import type { ChatAnswer } from "@/types/api";

interface ChatAnswerViewProps {
  answer: ChatAnswer;
}

function formatParams(
  params?: Record<string, string | number | boolean | null>,
): string {
  if (!params) {
    return "";
  }

  const entries = Object.entries(params).filter(
    ([, value]) => value !== null && value !== "",
  );
  if (entries.length === 0) {
    return "";
  }

  return entries
    .map(([key, value]) => `${key}=${String(value)}`)
    .join("&");
}

export function ChatAnswerView({ answer }: ChatAnswerViewProps) {
  return (
    <div className="space-y-4">
      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-100">
        {answer.answerText}
      </p>

      {answer.chart ? <ChatChartRenderer chart={answer.chart} /> : null}

      {answer.table ? (
        <section className="overflow-hidden rounded-xl border border-slate-700/80 bg-slate-950/70">
          <div className="border-b border-slate-800 px-4 py-3">
            <h3 className="text-sm font-semibold text-white">
              {answer.table.title}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  {answer.table.columns.map((column) => (
                    <th key={column} className="px-3 py-2 font-medium">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {answer.table.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} className="px-3 py-2">
                        {cell ?? "-"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {answer.warnings.length > 0 ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-100">
          {answer.warnings.map((warning, index) => (
            <p key={`${index}-${warning}`}>{warning}</p>
          ))}
        </div>
      ) : null}

      {answer.dataSources.length > 0 ? (
        <details className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs text-slate-400">
          <summary className="cursor-pointer text-slate-300">
            Źródła danych
          </summary>
          <ul className="mt-2 space-y-1">
            {answer.dataSources.map((source, index) => (
              <li key={`${source.endpoint}-${index}`}>
                <span className="text-slate-200">{source.label}</span>:{" "}
                <code>{source.endpoint}</code>
                {formatParams(source.params) ? (
                  <div className="mt-0.5 pl-3 text-slate-500">
                    query: <code>{formatParams(source.params)}</code>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
