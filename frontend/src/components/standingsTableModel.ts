import type { StandingZone } from "@/types/api";

const SOLID_BADGES: Record<string, string> = {
  champions_league: "bg-zone-cl text-on-zone",
  europa_league: "bg-zone-el text-on-zone",
  conference_league: "bg-zone-ecl text-on-zone",
  promotion: "bg-zone-promotion text-on-zone",
  promotion_playoff: "bg-zone-playoff text-on-zone",
  relegation: "bg-zone-relegation text-on-zone",
  relegation_playoff: "bg-zone-relegation-playoff text-on-zone",
};

/**
 * Classes for a zone badge.
 * Every known kind uses the same solid chip and light number.
 * Qualification stays in the legend label, not in a second frame.
 * Unknown kinds return null.
 */
export function zoneBadgeClass(zoneKind: string | null): string | null {
  if (zoneKind === null) {
    return null;
  }
  return SOLID_BADGES[zoneKind] ?? null;
}

/**
 * Visible note next to official points.
 * Null when the team has no adjustment.
 */
export function formatPointAdjustment(
  pointsAdjustment: number,
  adjustmentReason: string | null,
): string | null {
  if (pointsAdjustment === 0) {
    return null;
  }
  // U+2212, bo zwykły łącznik w „-4” wygląda jak myślnik, nie jak minus.
  const sign = pointsAdjustment < 0 ? "\u2212" : "+";
  const magnitude = Math.abs(pointsAdjustment);
  if (!adjustmentReason) {
    return `${sign}${magnitude} pkt`;
  }
  return `${sign}${magnitude} pkt (${adjustmentReason})`;
}

/** Zone kind covering a table position, or null when the place is neutral. */
export function zoneKindForPosition(
  zones: readonly StandingZone[],
  position: number,
): string | null {
  const match = zones.find(
    (zone) => position >= zone.position_from && position <= zone.position_to,
  );
  return match?.zone_kind ?? null;
}

/** Legend order. Does not mutate the input list. */
export function orderedStandingZones(
  zones: readonly StandingZone[],
): StandingZone[] {
  return [...zones].sort(
    (left, right) => left.sort_order - right.sort_order,
  );
}
