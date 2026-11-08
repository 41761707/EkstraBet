import Link from "next/link";
import {
  shouldShowBotColumn,
  shouldShowTopColumn,
  sortStandingsByExpectedPosition,
} from "@/components/leagues/projectedSeasonStandingsModel";
import { zoneKindForPosition } from "@/components/standingsTableModel";
import { ZonePositionBadge, ZoneTableFrame } from "@/components/zoneMarks";
import { formatProbability } from "@/lib/format";
import type {
  SeasonProjectionSpecialSlots,
  SeasonProjectionStandingRow,
  StandingZone,
} from "@/types/api";

interface ProjectedSeasonOutcomesTableProps {
  standings: SeasonProjectionStandingRow[];
  specialSlots: SeasonProjectionSpecialSlots | null;
  seasonId: number;
  leagueId: number;
  zones?: readonly StandingZone[];
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

function OutcomeRow({
  row,
  tablePosition,
  seasonId,
  leagueId,
  showTop,
  showBot,
  zoneKind,
}: {
  row: SeasonProjectionStandingRow;
  tablePosition: number;
  seasonId: number;
  leagueId: number;
  showTop: boolean;
  showBot: boolean;
  zoneKind: string | null;
}) {
  return (
    <tr className="border-t border-border hover:bg-surface-muted">
      <td className="px-3 py-2 text-muted">
        <ZonePositionBadge position={tablePosition} zoneKind={zoneKind} />
      </td>
      <td className="px-3 py-2 font-medium">
        <Link
          href={teamHref(row.team_id, seasonId, leagueId)}
          className="text-text transition hover:text-accent-text"
        >
          {row.team_name}
        </Link>
      </td>
      <td className="px-3 py-2 text-center font-semibold text-accent-text">
        {formatProbability(row.champion_probability)}
      </td>
      {showTop ? (
        <td className="px-3 py-2 text-center text-muted">
          {formatProbability(row.top_probability)}
        </td>
      ) : null}
      {showBot ? (
        <td className="px-3 py-2 text-center text-muted">
          {formatProbability(row.bot_probability)}
        </td>
      ) : null}
    </tr>
  );
}

export function ProjectedSeasonOutcomesTable({
  standings,
  specialSlots,
  seasonId,
  leagueId,
  zones = [],
}: ProjectedSeasonOutcomesTableProps) {
  const sorted = sortStandingsByExpectedPosition(standings);
  const showTop = shouldShowTopColumn(specialSlots);
  const showBot = shouldShowBotColumn(specialSlots);

  if (sorted.length === 0) {
    return null;
  }

  return (
    <ZoneTableFrame zones={zones}>
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-3 py-3 font-medium">#</th>
            <th className="px-3 py-3 font-medium">Drużyna</th>
            <th className="px-3 py-3 text-center font-medium">Mistrz</th>
            {showTop && specialSlots !== null ? (
              <th className="px-3 py-3 text-center font-medium">
                Puchary (TOP {specialSlots.top_slots})
              </th>
            ) : null}
            {showBot && specialSlots !== null ? (
              <th className="px-3 py-3 text-center font-medium">
                Spadek (BOT {specialSlots.bot_slots})
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, index) => {
            const tablePosition = index + 1;
            return (
              <OutcomeRow
                key={row.team_id}
                row={row}
                tablePosition={tablePosition}
                seasonId={seasonId}
                leagueId={leagueId}
                showTop={showTop}
                showBot={showBot}
                zoneKind={zoneKindForPosition(zones, tablePosition)}
              />
            );
          })}
        </tbody>
      </table>
    </ZoneTableFrame>
  );
}
