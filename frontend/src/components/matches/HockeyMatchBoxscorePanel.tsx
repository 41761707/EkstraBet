"use client";

import { useState } from "react";

import {
  goalieSortValue,
  nextBoxscoreSort,
  skaterSortValue,
  sortBoxscoreRows,
  type BoxscoreSortState,
  type BoxscoreSortValue,
  type GoalieSortKey,
  type SkaterSortKey,
} from "@/components/matches/hockeyBoxscoreSort";
import { HockeyGameRatingCharts } from "@/components/matches/HockeyGameRatingCharts";
import {
  formatDisplayedRating,
  RATING_BASELINE,
} from "@/components/matches/hockeyGameRatingModel";
import type {
  HockeyGameRating,
  HockeyGoalieBoxscoreRow,
  HockeyMatchBoxscore,
  HockeySkaterBoxscoreRow,
} from "@/types/api";

interface HockeyMatchBoxscorePanelProps {
  boxscore: HockeyMatchBoxscore;
  rating?: HockeyGameRating | null;
}

type ColumnAlign = "left" | "center";
type ColumnKind = "player" | "team" | "stat";

interface BoxscoreColumn<Row, Key extends string> {
  key: Key;
  label: string;
  title: string;
  align: ColumnAlign;
  kind: ColumnKind;
  display: (row: Row) => string;
  tone?: (row: Row) => string;
}

interface BoxscoreIdentity {
  player_id: number;
  team_id: number;
}

type RatedGoalieRow = HockeyGoalieBoxscoreRow & { rating: number | null };
type RatedSkaterRow = HockeySkaterBoxscoreRow & { rating: number | null };

const MISSING_RATING = "—";

function formatValue(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return String(value);
}

function plusMinusClassName(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) {
    return "text-text";
  }
  if (value > 0) {
    return "bg-success-bg font-semibold text-success-text";
  }
  return "bg-danger-bg font-semibold text-danger-text";
}

const RATING_GREEN_FROM = 6;

function ratingClassName(contribution: number | null | undefined): string {
  if (contribution === null || contribution === undefined) {
    return "text-text";
  }
  const shown = Number((contribution + RATING_BASELINE).toFixed(1));
  if (shown >= RATING_GREEN_FROM) {
    return "bg-success-bg font-semibold text-success-text";
  }
  if (shown < RATING_BASELINE) {
    return "bg-danger-bg font-semibold text-danger-text";
  }
  return "text-text";
}

function formatAccuracy(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

const GOALIE_COLUMNS: readonly BoxscoreColumn<RatedGoalieRow, GoalieSortKey>[] = [
  {
    key: "team_name",
    label: "Drużyna",
    title: "Drużyna",
    align: "left",
    kind: "team",
    display: (row) => row.team_name,
  },
  {
    key: "player_name",
    label: "Zawodnik",
    title: "Zawodnik",
    align: "left",
    kind: "player",
    display: (row) => row.player_name,
  },
  {
    key: "points",
    label: "Pkt",
    title: "Punkty",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.points),
  },
  {
    key: "rating",
    label: "Ocena",
    title: "Ocena meczu",
    align: "center",
    kind: "stat",
    display: (row) => formatRatingCell(row.rating),
    tone: (row) => ratingClassName(row.rating),
  },
  {
    key: "penalty_minutes",
    label: "Kary (MIN)",
    title: "Minuty kar",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.penalty_minutes),
  },
  {
    key: "time_on_ice",
    label: "TOI",
    title: "Czas na lodzie",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.time_on_ice),
  },
  {
    key: "shots_against",
    label: "Strzały",
    title: "Strzały na bramkę",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.shots_against),
  },
  {
    key: "shots_saved",
    label: "Obronione",
    title: "Obronione strzały",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.shots_saved),
  },
  {
    key: "saves_accuracy",
    label: "Obrony (%)",
    title: "Skuteczność obron",
    align: "center",
    kind: "stat",
    display: (row) => formatAccuracy(row.saves_accuracy),
  },
];

const SKATER_COLUMNS: readonly BoxscoreColumn<RatedSkaterRow, SkaterSortKey>[] = [
  {
    key: "team_name",
    label: "Drużyna",
    title: "Drużyna",
    align: "left",
    kind: "team",
    display: (row) => row.team_name,
  },
  {
    key: "player_name",
    label: "Zawodnik",
    title: "Zawodnik",
    align: "left",
    kind: "player",
    display: (row) => row.player_name,
  },
  {
    key: "goals",
    label: "B",
    title: "Bramki",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.goals),
  },
  {
    key: "assists",
    label: "A",
    title: "Asysty",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.assists),
  },
  {
    key: "points",
    label: "Pkt",
    title: "Punkty",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.points),
  },
  {
    key: "rating",
    label: "Ocena",
    title: "Ocena meczu",
    align: "center",
    kind: "stat",
    display: (row) => formatRatingCell(row.rating),
    tone: (row) => ratingClassName(row.rating),
  },
  {
    key: "plus_minus",
    label: "+/-",
    title: "Plus/minus",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.plus_minus),
    tone: (row) => plusMinusClassName(row.plus_minus),
  },
  {
    key: "penalty_minutes",
    label: "Kary (MIN)",
    title: "Minuty kar",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.penalty_minutes),
  },
  {
    key: "shots_on_goal",
    label: "SOG",
    title: "Strzały na bramkę",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.shots_on_goal),
  },
  {
    key: "time_on_ice",
    label: "TOI",
    title: "Czas na lodzie",
    align: "center",
    kind: "stat",
    display: (row) => formatValue(row.time_on_ice),
  },
];

function formatRatingCell(value: number | null): string {
  if (value === null) {
    return MISSING_RATING;
  }
  return formatDisplayedRating(value);
}

function totalsByPlayer(rating: HockeyGameRating | null): Map<number, number> {
  const totals = new Map<number, number>();
  if (!rating) {
    return totals;
  }
  for (const team of rating.teams) {
    for (const player of team.players) {
      totals.set(player.player_id, player.total);
    }
  }
  return totals;
}

function withRating<Row extends { player_id: number }>(
  rows: Row[],
  totals: Map<number, number>,
): Array<Row & { rating: number | null }> {
  return rows.map((row) => ({
    ...row,
    rating: totals.get(row.player_id) ?? null,
  }));
}

function textClass(kind: ColumnKind): string {
  if (kind === "player") {
    return "font-medium text-text";
  }
  if (kind === "team") {
    return "text-muted";
  }
  return "text-text";
}

export function HockeyMatchBoxscorePanel({
  boxscore,
  rating = null,
}: HockeyMatchBoxscorePanelProps) {
  const totals = totalsByPlayer(rating ?? null);
  const goalies = withRating(boxscore.goalies, totals);
  const skaters = withRating(boxscore.skaters, totals);

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-text">Bramkarze</h3>
        <SortableBoxscoreTable
          rows={goalies}
          columns={GOALIE_COLUMNS}
          valueOf={goalieSortValue}
          emptyMessage="Brak statystyk bramkarzy dla tego meczu."
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-text">Zawodnicy</h3>
        <SortableBoxscoreTable
          rows={skaters}
          columns={SKATER_COLUMNS}
          valueOf={skaterSortValue}
          emptyMessage="Brak statystyk zawodników z pola dla tego meczu."
        />
      </section>
      {rating ? <HockeyGameRatingCharts rating={rating} /> : null}
    </div>
  );
}

function SortableBoxscoreTable<Row extends BoxscoreIdentity, Key extends string>({
  rows,
  columns,
  valueOf,
  emptyMessage,
}: {
  rows: Row[];
  columns: readonly BoxscoreColumn<Row, Key>[];
  valueOf: (row: Row, key: Key) => BoxscoreSortValue;
  emptyMessage: string;
}) {
  const [sort, setSort] = useState<BoxscoreSortState<Key> | null>(null);
  if (rows.length === 0) {
    return <p className="text-sm text-muted">{emptyMessage}</p>;
  }

  const ordered = sort === null ? rows : sortBoxscoreRows(rows, sort, valueOf);

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">#</th>
            {columns.map((column) => (
              <SortableHeader
                key={column.key}
                column={column}
                sort={sort}
                onSort={(key) => setSort((current) => nextBoxscoreSort(current, key))}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((row, index) => (
            <tr
              key={`${row.player_id}-${row.team_id}`}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-3 py-2 text-subtle">{index + 1}</td>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-3 py-2 ${column.align === "center" ? "text-center" : ""} ${
                    column.tone?.(row) ?? textClass(column.kind)
                  }`}
                >
                  {column.display(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SortableHeader<Row, Key extends string>({
  column,
  sort,
  onSort,
}: {
  column: BoxscoreColumn<Row, Key>;
  sort: BoxscoreSortState<Key> | null;
  onSort: (key: Key) => void;
}) {
  const isActive = sort !== null && sort.key === column.key;
  const indicator = !isActive || sort === null ? "" : sort.direction === "asc" ? "↑" : "↓";
  const justify = column.align === "center" ? "justify-center" : "";

  return (
    <th
      aria-sort={ariaSort(sort, column.key)}
      className={`px-3 py-2 font-medium ${column.align === "center" ? "text-center" : "text-left"}`}
    >
      <button
        type="button"
        title={column.title}
        onClick={() => onSort(column.key)}
        className={[
          "inline-flex items-center gap-1 whitespace-nowrap rounded px-1 py-0.5",
          "hover:text-text",
          isActive ? "text-text" : "text-muted",
          justify,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <span>{column.label}</span>
        {indicator ? (
          <span aria-hidden="true" className="text-accent-text">
            {indicator}
          </span>
        ) : null}
      </button>
    </th>
  );
}

function ariaSort<Key extends string>(
  sort: BoxscoreSortState<Key> | null,
  key: Key,
): "ascending" | "descending" | "none" {
  if (sort === null || sort.key !== key) {
    return "none";
  }
  return sort.direction === "asc" ? "ascending" : "descending";
}
