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
      <p className="whitespace-pre-wrap text-sm leading-6 text-text">
        {answer.answerText}
      </p>

      {answer.chart ? <ChatChartRenderer chart={answer.chart} /> : null}

      {answer.table ? (
        <section className="overflow-hidden rounded-xl border border-border bg-surface">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-text">
              {answer.table.title}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-wide text-muted">
                <tr>
                  {answer.table.columns.map((column) => (
                    <th key={column} className="px-3 py-2 font-medium">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-text">
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
        <div className="rounded-lg border border-warning-border bg-warning-bg px-3 py-2 text-xs text-warning-text">
          {answer.warnings.map((warning, index) => (
            <p key={`${index}-${warning}`}>{warning}</p>
          ))}
        </div>
      ) : null}

      {answer.dataSources.length > 0 ? (
        <details className="rounded-lg border border-border bg-page/50 px-3 py-2 text-xs text-muted">
          <summary className="cursor-pointer text-muted">
            Źródła danych
          </summary>
          <ul className="mt-2 space-y-1">
            {answer.dataSources.map((source, index) => (
              <li key={`${source.endpoint}-${index}`}>
                <span className="text-text">{source.label}</span>:{" "}
                <code>{source.endpoint}</code>
                {formatParams(source.params) ? (
                  <div className="mt-0.5 pl-3 text-subtle">
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
