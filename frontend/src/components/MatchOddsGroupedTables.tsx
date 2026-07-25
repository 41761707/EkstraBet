"use client";

import { useState } from "react";

import {
  nextOddsSortState,
  ODDS_MARKET_EVENT_IDS,
  ODDS_SORT_BOOKMAKER_KEY,
  resolveOddsSortValue,
  sortOddsRows,
  type MarketEventProbability,
  type OddsColumn,
  type OddsSortState,
} from "@/components/matchOddsTableModel";
import { formatOdds } from "@/lib/format";
import type { OddsItem } from "@/types/api";

interface MatchOddsGroupedTablesProps {
  odds: OddsItem[];
  /** Unit probabilities for all market events (USTALONE row). */
  predictions: MarketEventProbability[];
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

function ariaSortValue(
  sort: OddsSortState | null,
  key: string,
): "ascending" | "descending" | "none" {
  if (sort === null || sort.key !== key) {
    return "none";
  }
  return sort.direction === "asc" ? "ascending" : "descending";
}

function sortIndicator(sort: OddsSortState | null, key: string): string {
  if (sort === null || sort.key !== key) {
    return "";
  }
  return sort.direction === "asc" ? "↑" : "↓";
}

interface SortableHeaderProps {
  label: string;
  sortKey: string;
  sort: OddsSortState | null;
  align?: "left" | "center";
  onSort: (key: string) => void;
}

function SortableHeader({
  label,
  sortKey,
  sort,
  align = "left",
  onSort,
}: SortableHeaderProps) {
  const indicator = sortIndicator(sort, sortKey);
  const isActive = sort !== null && sort.key === sortKey;

  return (
    <th
      className={`whitespace-nowrap px-3 py-3 font-medium ${align === "center" ? "text-center" : "text-left"}`}
      aria-sort={ariaSortValue(sort, sortKey)}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 ${
          isActive ? "text-slate-200" : "text-slate-400"
        } ${align === "center" ? "justify-center" : ""}`}
      >
        <span>{label}</span>
        {indicator ? (
          <span aria-hidden="true" className="text-sky-300">
            {indicator}
          </span>
        ) : null}
      </button>
    </th>
  );
}

interface OddsTableProps {
  title: string;
  bookmakers: readonly string[];
  columns: OddsColumn[];
  lookup: Map<string, number>;
  predictions: MarketEventProbability[];
}

function OddsTable({
  title,
  bookmakers,
  columns,
  lookup,
  predictions,
}: OddsTableProps) {
  const [sort, setSort] = useState<OddsSortState | null>(null);
  const baseRows = ["USTALONE", ...bookmakers];
  const rows =
    sort === null
      ? baseRows
      : sortOddsRows(baseRows, sort, columns, lookup, predictions);

  const handleSort = (key: string) => {
    setSort((current) => nextOddsSortState(current, key));
  };

  return (
    <div className="min-w-0 rounded-xl border border-slate-700/80">
      <p className="border-b border-slate-700/80 bg-slate-900/80 px-4 py-3 text-sm font-medium text-slate-200">
        {title}
      </p>
      <table className="w-full text-sm">
        <thead className="bg-slate-900/60 text-left text-slate-400">
          <tr>
            <SortableHeader
              label="Bukmacher"
              sortKey={ODDS_SORT_BOOKMAKER_KEY}
              sort={sort}
              onSort={handleSort}
            />
            {columns.map((column) => (
              <SortableHeader
                key={column.key}
                label={column.label}
                sortKey={column.key}
                sort={sort}
                align="center"
                onSort={handleSort}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((bookmaker) => (
            <tr
              key={bookmaker}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="whitespace-nowrap px-3 py-3 font-medium text-white">
                {bookmaker}
              </td>
              {columns.map((column) => {
                const value = resolveOddsSortValue(
                  bookmaker,
                  column.eventId,
                  lookup,
                  predictions,
                );
                return (
                  <td
                    key={column.key}
                    className="whitespace-nowrap px-3 py-3 text-center font-semibold text-emerald-300"
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
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
      <OddsTable
        title="Porównanie kursów z estymacją na rezultat:"
        bookmakers={bookmakers}
        columns={[
          {
            key: "home",
            label: "Gospodarz",
            eventId: ODDS_MARKET_EVENT_IDS.home,
          },
          {
            key: "draw",
            label: "Remis",
            eventId: ODDS_MARKET_EVENT_IDS.draw,
          },
          {
            key: "away",
            label: "Gość",
            eventId: ODDS_MARKET_EVENT_IDS.away,
          },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
      <OddsTable
        title="Porównanie kursów z estymacją na OU:"
        bookmakers={bookmakers}
        columns={[
          {
            key: "under",
            label: "UNDER 2.5",
            eventId: ODDS_MARKET_EVENT_IDS.under,
          },
          {
            key: "over",
            label: "OVER 2.5",
            eventId: ODDS_MARKET_EVENT_IDS.over,
          },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
      <OddsTable
        title="Porównanie kursów z estymacją na BTTS:"
        bookmakers={bookmakers}
        columns={[
          {
            key: "bttsYes",
            label: "BTTS TAK",
            eventId: ODDS_MARKET_EVENT_IDS.bttsYes,
          },
          {
            key: "bttsNo",
            label: "BTTS NIE",
            eventId: ODDS_MARKET_EVENT_IDS.bttsNo,
          },
        ]}
        lookup={lookup}
        predictions={predictions}
      />
    </div>
  );
}
