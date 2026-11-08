import Link from "next/link";
import { formatPointAdjustment } from "@/components/standingsTableModel";
import { ZonePositionBadge, ZoneTableFrame } from "@/components/zoneMarks";
import type { StandingZone, TraditionalStandingRow } from "@/types/api";

const EMPTY_ZONES: StandingZone[] = [];

interface StandingsTableProps {
  standings: TraditionalStandingRow[];
  seasonId?: number;
  leagueId?: number;
  zones?: StandingZone[];
}

function teamHref(
  teamId: number,
  seasonId?: number,
  leagueId?: number,
): string {
  const params = new URLSearchParams();
  if (seasonId) {
    params.set("season_id", String(seasonId));
  }
  if (leagueId) {
    params.set("league_id", String(leagueId));
  }
  const query = params.toString();
  return query ? `/teams/${teamId}?${query}` : `/teams/${teamId}`;
}

function PositionCell({
  position,
  zoneKind,
}: {
  position: number;
  zoneKind: string | null;
}) {
  return (
    <td className="px-3 py-2 text-muted">
      <ZonePositionBadge position={position} zoneKind={zoneKind} />
    </td>
  );
}

function PointsCell({ row }: { row: TraditionalStandingRow }) {
  const note = formatPointAdjustment(
    row.points_adjustment,
    row.adjustment_reason,
  );

  return (
    <td className="px-3 py-2 text-center">
      <span className="font-semibold text-accent-text">{row.points}</span>
      {note ? (
        <span
          className="mt-0.5 block text-xs font-normal text-muted"
          title={note}
        >
          {note}
        </span>
      ) : null}
    </td>
  );
}

export function StandingsTable({
  standings,
  seasonId,
  leagueId,
  zones = EMPTY_ZONES,
}: StandingsTableProps) {
  if (standings.length === 0) {
    return null;
  }

  return (
    <ZoneTableFrame zones={zones}>
      <table className="min-w-full text-sm">
          <thead className="bg-surface-muted text-left text-muted">
            <tr>
              <th className="px-3 py-3 font-medium">#</th>
              <th className="px-3 py-3 font-medium">Team</th>
              <th className="px-3 py-3 text-center font-medium">MP</th>
              <th className="px-3 py-3 text-center font-medium">W</th>
              <th className="px-3 py-3 text-center font-medium">D</th>
              <th className="px-3 py-3 text-center font-medium">L</th>
              <th className="px-3 py-3 text-center font-medium">GF</th>
              <th className="px-3 py-3 text-center font-medium">GA</th>
              <th className="px-3 py-3 text-center font-medium">GD</th>
              <th className="px-3 py-3 text-center font-medium">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((row) => (
              <tr
                key={row.team_id}
                className="border-t border-border hover:bg-surface-muted"
              >
                <PositionCell
                  position={row.position}
                  zoneKind={row.zone_kind}
                />
                <td className="px-3 py-2 font-medium">
                  <Link
                    href={teamHref(row.team_id, seasonId, leagueId)}
                    className="text-text transition hover:text-accent-text"
                  >
                    {row.team_name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.played}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.wins}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.draws}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.losses}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.goals_for}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.goals_against}
                </td>
                <td className="px-3 py-2 text-center text-muted">
                  {row.goal_difference}
                </td>
                <PointsCell row={row} />
              </tr>
            ))}
        </tbody>
      </table>
    </ZoneTableFrame>
  );
}
