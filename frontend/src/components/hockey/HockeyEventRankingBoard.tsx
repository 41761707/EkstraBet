import Link from "next/link";

import { formatPercent } from "@/lib/format";
import type {
  HockeyPlayerEventRanking,
  HockeyPlayerEventRankingRow,
} from "@/types/api";

const PODIUM_SIZE = 3;

interface HockeyEventRankingBoardProps {
  ranking: HockeyPlayerEventRanking;
}

interface HockeyEventRankingGridProps {
  rankings: HockeyPlayerEventRanking[];
}

export function HockeyEventRankingGrid({
  rankings,
}: HockeyEventRankingGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {rankings.map((ranking) => (
        <HockeyEventRankingBoard key={ranking.metric} ranking={ranking} />
      ))}
    </div>
  );
}

export function HockeyEventRankingBoard({
  ranking,
}: HockeyEventRankingBoardProps) {
  const podium = ranking.rows.slice(0, PODIUM_SIZE);
  const rest = ranking.rows.slice(PODIUM_SIZE);

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold text-text">{ranking.label}</h3>
      <p className="mt-1 text-xs text-muted">{ranking.hint}</p>
      {ranking.rows.length === 0 ? (
        <p className="mt-3 text-sm text-muted">Brak zawodników.</p>
      ) : (
        <div className="mt-3 space-y-3">
          <RankingPodium rows={podium} metric={ranking.metric} />
          {rest.length > 0 ? (
            <ol className="space-y-1">
              {rest.map((row) => (
                <RankingRow
                  key={row.player_id}
                  row={row}
                  metric={ranking.metric}
                />
              ))}
            </ol>
          ) : null}
        </div>
      )}
    </section>
  );
}

function RankingPodium({
  rows,
  metric,
}: {
  rows: HockeyPlayerEventRankingRow[];
  metric: HockeyPlayerEventRanking["metric"];
}) {
  return (
    <div className={`grid items-end gap-2 ${podiumColumns(rows.length)}`}>
      {rows.map((row) => (
        <PodiumCard key={row.player_id} row={row} metric={metric} />
      ))}
    </div>
  );
}

function podiumColumns(count: number): string {
  if (count <= 1) {
    return "grid-cols-1";
  }
  if (count === 2) {
    return "grid-cols-2";
  }
  return "grid-cols-3";
}

function PodiumCard({
  row,
  metric,
}: {
  row: HockeyPlayerEventRankingRow;
  metric: HockeyPlayerEventRanking["metric"];
}) {
  const isLeader = row.rank === 1;
  const shots = shotLabel(row, metric);

  return (
    <Link
      href={`/matches/${row.match_id}`}
      className={podiumCardClass(isLeader)}
    >
      <span className="text-xs font-semibold text-muted">{row.rank}</span>
      <span className="mt-1 line-clamp-2 w-full text-xs font-medium leading-tight text-text sm:text-sm">
        {row.player_name}
      </span>
      <span className="truncate text-xs text-muted">{teamLabel(row)}</span>
      <span className={podiumPercentClass(isLeader)}>
        {formatPercent(row.probability)}
      </span>
      <span className="truncate text-xs text-muted">
        {extractKickoffTime(row.game_date)} {opponentLabel(row)}
      </span>
      {shots ? <span className="text-xs text-muted">{shots}</span> : null}
    </Link>
  );
}

function podiumCardClass(isLeader: boolean): string {
  const shared = [
    "flex min-w-0 flex-col items-center rounded-lg border px-2 text-center",
    "transition hover:bg-surface",
  ].join(" ");
  if (isLeader) {
    return `${shared} min-h-32 border-accent bg-accent-soft py-3`;
  }
  return `${shared} min-h-24 border-border bg-surface-muted py-2`;
}

function podiumPercentClass(isLeader: boolean): string {
  if (isLeader) {
    return "mt-1 text-lg font-semibold text-accent-text";
  }
  return "mt-1 text-sm font-semibold text-text";
}

function RankingRow({
  row,
  metric,
}: {
  row: HockeyPlayerEventRankingRow;
  metric: HockeyPlayerEventRanking["metric"];
}) {
  const shots = shotLabel(row, metric);

  return (
    <li>
      <Link
        href={`/matches/${row.match_id}`}
        className="flex items-baseline justify-between gap-3 rounded-md px-2 py-1.5 text-sm transition hover:bg-surface-muted"
      >
        <span className="min-w-0 truncate text-text">
          <span className="mr-2 text-muted">{row.rank}</span>
          {row.player_name}
          <span className="text-muted"> {teamLabel(row)}</span>
        </span>
        <span className="shrink-0 text-right text-muted">
          {extractKickoffTime(row.game_date)} {opponentLabel(row)}
          <span className="ml-2 font-medium text-text">
            {formatPercent(row.probability)}
          </span>
          {shots ? <span className="ml-2">{shots}</span> : null}
        </span>
      </Link>
    </li>
  );
}

function teamLabel(row: HockeyPlayerEventRankingRow): string {
  return row.team_shortcut ?? row.team_name;
}

function opponentLabel(row: HockeyPlayerEventRankingRow): string {
  const name = row.opponent_shortcut ?? row.opponent_name;
  return row.is_home ? `vs ${name}` : `@ ${name}`;
}

function shotLabel(
  row: HockeyPlayerEventRankingRow,
  metric: HockeyPlayerEventRanking["metric"],
): string | null {
  if (metric !== "shot" || row.expected_shots == null) {
    return null;
  }
  if (!Number.isFinite(row.expected_shots)) {
    return null;
  }
  return `${row.expected_shots.toFixed(2)} SOG`;
}

function extractKickoffTime(gameDate: string): string {
  const timeMatch = /[T ](\d{2}:\d{2})/.exec(gameDate);
  return timeMatch?.[1] ?? "—";
}
