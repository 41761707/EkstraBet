import { formatOdds } from "@/lib/format";
import type { MatchPredictionItem, OddsItem } from "@/types/api";

interface MatchOddsGroupedTablesProps {
  odds: OddsItem[];
  predictions: MatchPredictionItem[];
}

const BOOKMAKER_ORDER = [
  "Superbet",
  "Betclic",
  "Fortuna",
  "STS",
  "LvBet",
  "Betfan",
  "Etoto",
  "Fuksiarz",
  "Betters",
] as const;

const EVENT_IDS = {
  home: 1,
  draw: 2,
  away: 3,
  over: 8,
  under: 12,
  bttsYes: 6,
  bttsNo: 172,
} as const;

function predictionOdds(
  predictions: MatchPredictionItem[],
  eventId: number,
): number | null {
  const prediction = predictions.find((item) => item.event_id === eventId);
  if (!prediction || prediction.value === null || prediction.value <= 0) {
    return null;
  }
  return Number((1 / prediction.value).toFixed(2));
}

function buildOddsLookup(odds: OddsItem[]): Map<string, number> {
  const lookup = new Map<string, number>();
  for (const item of odds) {
    lookup.set(`${item.bookmaker_name}:${item.event_id}`, item.odds);
  }
  return lookup;
}

function formatCell(value: number | null | undefined): string {
  if (value === null || value === undefined || value <= 0) {
    return "0";
  }
  return formatOdds(value);
}

interface OddsTableProps {
  title: string;
  bookmakers: readonly string[];
  columns: { key: string; label: string; eventId: number }[];
  lookup: Map<string, number>;
  predictions: MatchPredictionItem[];
}

function OddsTable({
  title,
  bookmakers,
  columns,
  lookup,
  predictions,
}: OddsTableProps) {
  const rows = ["USTALONE", ...bookmakers];

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <p className="border-b border-slate-700/80 bg-slate-900/80 px-4 py-3 text-sm font-medium text-slate-200">
        {title}
      </p>
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/60 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Bukmacher</th>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-4 py-3 text-center font-medium"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((bookmaker) => (
            <tr
              key={bookmaker}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-3 font-medium text-white">{bookmaker}</td>
              {columns.map((column) => {
                const value =
                  bookmaker === "USTALONE"
                    ? predictionOdds(predictions, column.eventId)
                    : lookup.get(`${bookmaker}:${column.eventId}`) ?? null;
                return (
                  <td
                    key={column.key}
                    className="px-4 py-3 text-center font-semibold text-emerald-300"
                  >
                    {formatCell(value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MatchOddsGroupedTables({
  odds,
  predictions,
}: MatchOddsGroupedTablesProps) {
  if (odds.length === 0 && predictions.length === 0) {
    return null;
  }

  const lookup = buildOddsLookup(odds);
  const bookmakers = BOOKMAKER_ORDER.filter((name) =>
    odds.some((item) => item.bookmaker_name === name),
  );

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <OddsTable
        title="Porównanie kursów z estymacją na rezultat:"
        bookmakers={bookmakers}
        columns={[
          { key: "home", label: "Gospodarz", eventId: EVENT_IDS.home },
          { key: "draw", label: "Remis", eventId: EVENT_IDS.draw },
          { key: "away", label: "Gość", eventId: EVENT_IDS.away },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
      <OddsTable
        title="Porównanie kursów z estymacją na OU:"
        bookmakers={bookmakers}
        columns={[
          { key: "under", label: "UNDER 2.5", eventId: EVENT_IDS.under },
          { key: "over", label: "OVER 2.5", eventId: EVENT_IDS.over },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
      <OddsTable
        title="Porównanie kursów z estymacją na BTTS:"
        bookmakers={bookmakers}
        columns={[
          { key: "bttsYes", label: "BTTS TAK", eventId: EVENT_IDS.bttsYes },
          { key: "bttsNo", label: "BTTS NIE", eventId: EVENT_IDS.bttsNo },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
    </div>
  );
}
