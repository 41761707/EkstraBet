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

function PositionDistribution({
  probabilities,
}: {
  probabilities: number[];
}) {
  if (probabilities.length === 0) {
    return (
      <p className="text-sm text-slate-500">Brak rozkładu pozycji.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead className="text-left text-slate-500">
          <tr>
            <th className="px-2 py-1 font-medium">Poz.</th>
            <th className="px-2 py-1 font-medium">Prawdopodobieństwo</th>
          </tr>
        </thead>
        <tbody>
          {probabilities.map((probability, index) => (
            <tr
              key={`pos-${index + 1}`}
              className="border-t border-slate-800/60"
            >
              <td className="px-2 py-1 text-slate-400">{index + 1}</td>
              <td className="px-2 py-1 text-slate-300">
                {formatProbability(probability)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProjectionRow({
  row,
  seasonId,
  leagueId,
}: {
  row: SeasonProjectionStandingRow;
  seasonId: number;
  leagueId: number;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <tr className="border-t border-slate-800/80 hover:bg-slate-900/50">
        <td className="px-3 py-2 text-slate-400">
          <button
            type="button"
            onClick={() => setIsExpanded((open) => !open)}
            className="inline-flex items-center gap-1 text-left text-sky-300 transition hover:text-sky-200"
            aria-expanded={isExpanded}
          >
            <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
            {formatProjectionPoints(row.expected_position)}
          </button>
        </td>
        <td className="px-3 py-2 font-medium">
          <Link
            href={teamHref(row.team_id, seasonId, leagueId)}
            className="text-white transition hover:text-sky-200"
          >
            {row.team_name}
          </Link>
        </td>
        <td className="px-3 py-2 text-center text-slate-300">
          {row.current_points}
        </td>
        <td className="px-3 py-2 text-center font-semibold text-sky-200">
          {formatProjectionPoints(row.expected_points)}
        </td>
        <td className="px-3 py-2 text-center text-slate-300">
          {formatProjectionPoints(row.points_stddev)}
        </td>
        <td className="px-3 py-2 text-center text-slate-300">
          {formatProjectionPoints(row.points_p05)}–
          {formatProjectionPoints(row.points_p95)}
        </td>
        <td className="px-3 py-2 text-center text-slate-300">
          {formatProjectionPoints(row.points_min)}–
          {formatProjectionPoints(row.points_max)}
        </td>
      </tr>
      {isExpanded ? (
        <tr className="border-t border-slate-800/60 bg-slate-950/40">
          <td colSpan={7} className="px-3 py-3">
            <p className="mb-2 text-xs text-slate-500">
              Najbardziej prawdopodobna pozycja: {row.most_likely_position}.
              Rozkład pozycji końcowej (1…N).
            </p>
            <PositionDistribution
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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
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
          {sorted.map((row) => (
            <ProjectionRow
              key={row.team_id}
              row={row}
              seasonId={seasonId}
              leagueId={leagueId}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
