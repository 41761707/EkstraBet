"use client";

import Link from "next/link";
import { useState } from "react";
import {
  formatProjectionPoints,
  sortStandingsByExpectedPosition,
} from "@/components/leagues/projectedSeasonStandingsModel";
import { formatProbability } from "@/lib/format";
import type { SeasonProjectionStandingRow } from "@/types/api";

interface ProjectedSeasonStandingsTableProps {
  standings: SeasonProjectionStandingRow[];
  seasonId: number;
  leagueId: number;
}

function teamHref(
  teamId: number,
  seasonId: number,
  leagueId: number,
): string {
  const params = new URLSearchParams({
    season_id: String(seasonId),
    league_id: String(leagueId),
  });
  return `/teams/${teamId}?${params.toString()}`;
}

export function ProjectedPositionChance({
  tablePosition,
  probability,
}: {
  tablePosition: number;
  probability: number | null;
}) {
  return (
    <p className="text-sm text-muted">
      Szansa na {tablePosition}. miejsce: {formatProbability(probability)}
    </p>
  );
}

export function ProjectedPositionChanceList({
  probabilities,
}: {
  probabilities: number[];
}) {
  if (probabilities.length === 0) {
    return <p className="text-sm text-subtle">Brak rozkładu pozycji.</p>;
  }

  return (
    <div className="flex flex-col gap-1">
      {probabilities.map((probability, index) => (
        <ProjectedPositionChance
          key={index + 1}
          tablePosition={index + 1}
          probability={probability}
        />
      ))}
    </div>
  );
}

function ProjectionRow({
  row,
  tablePosition,
  seasonId,
  leagueId,
}: {
  row: SeasonProjectionStandingRow;
  tablePosition: number;
  seasonId: number;
  leagueId: number;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <tr className="border-t border-border hover:bg-surface-muted">
        <td className="px-3 py-2 text-muted">
          <button
            type="button"
            onClick={() => setIsExpanded((open) => !open)}
            className="inline-flex items-center gap-1 text-left text-accent-text transition hover:text-accent-text-hover"
            aria-expanded={isExpanded}
          >
            <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
            {tablePosition}
          </button>
        </td>
        <td className="px-3 py-2 font-medium">
          <Link
            href={teamHref(row.team_id, seasonId, leagueId)}
            className="text-text transition hover:text-accent-text"
          >
            {row.team_name}
          </Link>
        </td>
        <td className="px-3 py-2 text-center text-muted">
          {row.current_points}
        </td>
        <td className="px-3 py-2 text-center font-semibold text-accent-text">
          {formatProjectionPoints(row.expected_points)}
        </td>
        <td className="px-3 py-2 text-center text-muted">
          {formatProjectionPoints(row.points_stddev)}
        </td>
        <td className="px-3 py-2 text-center text-muted">
          {formatProjectionPoints(row.points_p05)}–
          {formatProjectionPoints(row.points_p95)}
        </td>
        <td className="px-3 py-2 text-center text-muted">
          {formatProjectionPoints(row.points_min)}–
          {formatProjectionPoints(row.points_max)}
        </td>
      </tr>
      {isExpanded ? (
        <tr className="border-t border-border bg-surface-muted">
          <td colSpan={7} className="px-3 py-3">
            <p className="mb-2 text-xs text-subtle">
              Najbardziej prawdopodobna pozycja: {row.most_likely_position}.
              Szansa na każde miejsce końcowe (1…{row.position_probabilities.length}).
            </p>
            <ProjectedPositionChanceList
              probabilities={row.position_probabilities}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function ProjectedSeasonStandingsTable({
  standings,
  seasonId,
  leagueId,
}: ProjectedSeasonStandingsTableProps) {
  const sorted = sortStandingsByExpectedPosition(standings);

  if (sorted.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-3 py-3 font-medium">#</th>
            <th className="px-3 py-3 font-medium">Drużyna</th>
            <th className="px-3 py-3 text-center font-medium">Pkt</th>
            <th className="px-3 py-3 text-center font-medium">xPts</th>
            <th className="px-3 py-3 text-center font-medium">SD</th>
            <th className="px-3 py-3 text-center font-medium">P05–P95</th>
            <th className="px-3 py-3 text-center font-medium">Min–Max</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, index) => (
            <ProjectionRow
              key={row.team_id}
              row={row}
              tablePosition={index + 1}
              seasonId={seasonId}
              leagueId={leagueId}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
