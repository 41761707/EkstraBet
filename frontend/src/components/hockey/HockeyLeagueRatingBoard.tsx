"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ExpandableSection } from "@/components/ExpandableSection";
import { formatDisplayedRating } from "@/components/matches/hockeyGameRatingModel";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getHockeyRatingBoard } from "@/lib/apiClient";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type {
  HockeyRatingAverage,
  HockeyRatingBoard,
  HockeyRatingGame,
  HockeyRatingPositionGames,
} from "@/types/api";

const WINDOWS = [
  { label: "Cały sezon", value: 0 },
  { label: "Ostatnie 5 meczów", value: 5 },
  { label: "Ostatnie 10 meczów", value: 10 },
] as const;

const EMPTY_TITLE = "Brak zapisanych ocen";
const EMPTY_MESSAGE = "Oceny pojawią się po naliczeniu skryptem.";

const POSITION_CHARTS = [
  { key: "forward", title: "Napastnicy" },
  { key: "defense", title: "Obrońcy" },
  { key: "goalie", title: "Bramkarze" },
] as const;

type RatingWindow = (typeof WINDOWS)[number]["value"];

/** Season rating lists under the predicted-event section. */
export function HockeyLeagueRatingBoard({ seasonId }: { seasonId: number }) {
  const [window, setWindow] = useState<RatingWindow>(0);
  const [board, setBoard] = useState<HockeyRatingBoard | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setErrorMessage(null);
      try {
        const response = await getHockeyRatingBoard(seasonId, window);
        if (!cancelled) {
          setBoard(response);
        }
      } catch (error) {
        if (!cancelled) {
          setBoard(null);
          setErrorMessage(
            error instanceof ApiError
              ? error.message
              : "Nie udało się połączyć z API backendu.",
          );
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [seasonId, window]);

  return (
    <ExpandableSection title="Oceny meczowe">
      <div className="space-y-4">
        <WindowSelect window={window} onChange={setWindow} />
        <p className="text-sm text-muted">
          Ocena 5 jest oceną wyjściową dla każdego zawodnika. Wartości powyżej oznaczają występ lepszy od średniej, natomiast wartości poniżej - gorszy.
        </p>
        <BoardBody board={board} errorMessage={errorMessage} />
      </div>
    </ExpandableSection>
  );
}

function WindowSelect({
  window,
  onChange,
}: {
  window: RatingWindow;
  onChange: (window: RatingWindow) => void;
}) {
  return (
    <label className="flex flex-wrap items-center gap-3 text-sm text-muted">
      <span className="font-medium text-text">Zakres</span>
      <select
        className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
        value={window}
        onChange={(event) =>
          onChange(Number(event.target.value) as RatingWindow)
        }
      >
        {WINDOWS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function BoardBody({
  board,
  errorMessage,
}: {
  board: HockeyRatingBoard | null;
  errorMessage: string | null;
}) {
  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać ocen"
        message={errorMessage}
      />
    );
  }
  if (!board) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted">Ładowanie ocen...</p>
        <h4 className="text-sm font-semibold text-text">Najlepsza średnia</h4>
        <h4 className="text-sm font-semibold text-text">Najgorsza średnia</h4>
        <h4 className="text-sm font-semibold text-text">Napastnicy</h4>
        <h4 className="text-sm font-semibold text-text">Obrońcy</h4>
        <h4 className="text-sm font-semibold text-text">Bramkarze</h4>
        <h4 className="text-sm font-semibold text-text">Najgorsze mecze</h4>
      </div>
    );
  }
  if (boardIsEmpty(board)) {
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_TITLE}
        message={EMPTY_MESSAGE}
      />
    );
  }
  return <HockeyRatingBoardCharts board={board} />;
}

interface RatingBarRow {
  key: string;
  name: string;
  href?: string;
  detail: string;
  value: number;
}

/** Bar charts for averages and for each position's best and worst nights. */
export function HockeyRatingBoardCharts({
  board,
}: {
  board: HockeyRatingBoard;
}) {
  const averageScale = signedScale([
    ...board.averages.map((row) => row.average),
    ...board.worst_averages.map((row) => row.average),
  ]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <SignedRatingChart
          title="Najlepsza średnia"
          scale={averageScale}
          rows={board.averages.map(averageRow)}
        />
        <SignedRatingChart
          title="Najgorsza średnia"
          scale={averageScale}
          rows={board.worst_averages.map(averageRow)}
        />
      </div>
      {POSITION_CHARTS.map((position) => (
        <PositionNightCharts
          key={position.key}
          title={position.title}
          games={board[position.key]}
        />
      ))}
    </div>
  );
}

function PositionNightCharts({
  title,
  games,
}: {
  title: string;
  games: HockeyRatingPositionGames;
}) {
  const scale = signedScale([
    ...games.best_games.map((row) => row.total),
    ...games.worst_games.map((row) => row.total),
  ]);

  return (
    <section className="space-y-3">
      <h4 className="text-base font-semibold text-text">{title}</h4>
      <div className="grid gap-4 lg:grid-cols-2">
        <SignedRatingChart
          title="Najlepsze mecze"
          scale={scale}
          rows={games.best_games.map(gameRow)}
        />
        <SignedRatingChart
          title="Najgorsze mecze"
          scale={scale}
          rows={games.worst_games.map(gameRow)}
        />
      </div>
    </section>
  );
}

function boardIsEmpty(board: HockeyRatingBoard): boolean {
  const nights = [board.forward, board.defense, board.goalie];
  const nightsEmpty = nights.every(
    (games) => games.best_games.length === 0 && games.worst_games.length === 0,
  );
  return (
    board.averages.length === 0 &&
    board.worst_averages.length === 0 &&
    nightsEmpty
  );
}

function SignedRatingChart({
  title,
  rows,
  scale,
}: {
  title: string;
  rows: RatingBarRow[];
  scale: number;
}) {
  return (
    <section className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <h5 className="text-sm font-semibold text-text">{title}</h5>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">Brak ocen w tym zakresie.</p>
      ) : (
        rows.map((row) => (
          <SignedRatingBar key={row.key} row={row} scale={scale} />
        ))
      )}
    </section>
  );
}

function SignedRatingBar({
  row,
  scale,
}: {
  row: RatingBarRow;
  scale: number;
}) {
  const width = (Math.abs(row.value) / scale) * 50;
  const isNegative = row.value < 0;
  const name = row.href ? (
    <Link
      href={row.href}
      className="block truncate text-xs font-semibold text-accent-text hover:text-accent-text-hover"
    >
      {row.name}
    </Link>
  ) : (
    <span className="block truncate text-xs text-text">{row.name}</span>
  );

  return (
    <div
      className="grid items-center gap-2"
      style={{ gridTemplateColumns: "minmax(0,14rem) minmax(0,1fr) auto" }}
    >
      <div className="min-w-0">
        {name}
        <p className="truncate text-[10px] text-muted">{row.detail}</p>
      </div>
      <div className="relative h-6 overflow-hidden rounded-md bg-chart-track">
        <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px bg-border" />
        {row.value === 0 ? null : (
          <div
            className="absolute inset-y-0"
            style={{
              width: `${width}%`,
              backgroundColor: isNegative
                ? CHART_COLOR_NEGATIVE
                : CHART_COLOR_POSITIVE,
              ...(isNegative ? { right: "50%" } : { left: "50%" }),
            }}
          />
        )}
      </div>
      <span className="text-xs tabular-nums text-text">
        {formatDisplayedRating(row.value)}
      </span>
    </div>
  );
}

function averageRow(row: HockeyRatingAverage): RatingBarRow {
  return {
    key: String(row.player_id),
    name: row.player_name,
    detail: `${row.team_name} · ${gamesLabel(row.games)}`,
    value: row.average,
  };
}

function gameRow(row: HockeyRatingGame): RatingBarRow {
  return {
    key: `${row.match_id}-${row.player_id}`,
    name: row.player_name,
    href: `/matches/${row.match_id}`,
    detail: `${row.match_date} · ${row.opponent_name}`,
    value: row.total,
  };
}

function signedScale(values: readonly number[]): number {
  let scale = 1;
  for (const value of values) {
    scale = Math.max(scale, Math.abs(value));
  }
  return scale;
}

function gamesLabel(games: number): string {
  const mod10 = games % 10;
  const mod100 = games % 100;
  if (games === 1) {
    return "1 mecz";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${games} mecze`;
  }
  return `${games} meczów`;
}
