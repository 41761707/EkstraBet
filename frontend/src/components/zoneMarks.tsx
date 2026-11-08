import type { ReactNode } from "react";
import {
  orderedStandingZones,
  zoneBadgeClass,
} from "@/components/standingsTableModel";
import type { StandingZone } from "@/types/api";

export function ZonePositionBadge({
  position,
  zoneKind,
}: {
  position: number;
  zoneKind: string | null;
}) {
  const badgeClass = zoneBadgeClass(zoneKind);
  if (!badgeClass) {
    return <>{position}</>;
  }

  return (
    <span
      className={
        "inline-flex h-6 min-w-6 items-center justify-center " +
        `rounded-md px-1 text-xs font-semibold ${badgeClass}`
      }
    >
      {position}
    </span>
  );
}

export function StandingsZoneLegend({
  zones,
}: {
  zones: readonly StandingZone[];
}) {
  const ordered = orderedStandingZones(zones);
  if (ordered.length === 0) {
    return null;
  }

  return (
    <ul
      className={
        "flex list-none flex-wrap gap-x-4 gap-y-2 border-t " +
        "border-border px-3 py-3 text-sm text-text"
      }
    >
      {ordered.map((zone) => {
        const badgeClass = zoneBadgeClass(zone.zone_kind);
        return (
          <li
            key={
              `${zone.sort_order}-${zone.position_from}-` +
              `${zone.zone_kind}-${zone.stage ?? "direct"}`
            }
            className="flex items-center gap-2"
          >
            <span
              aria-hidden="true"
              className={`inline-block h-3 w-3 shrink-0 rounded-sm ${
                badgeClass ?? "bg-surface-muted"
              }`}
            />
            {zone.label}
          </li>
        );
      })}
    </ul>
  );
}

export function ZoneTableFrame({
  zones,
  children,
}: {
  zones: readonly StandingZone[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="overflow-x-auto">{children}</div>
      <StandingsZoneLegend zones={zones} />
    </div>
  );
}
