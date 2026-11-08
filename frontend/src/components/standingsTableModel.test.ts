import { describe, expect, it } from "vitest";

import {
  formatPointAdjustment,
  orderedStandingZones,
  zoneBadgeClass,
  zoneKindForPosition,
} from "@/components/standingsTableModel";
import type { StandingZone } from "@/types/api";

function zone(
  overrides: Partial<StandingZone> & Pick<StandingZone, "sort_order">,
): StandingZone {
  return {
    position_from: 1,
    position_to: 1,
    zone_kind: "champions_league",
    stage: "qualification",
    band: "top",
    label: "Awans – Liga Mistrzów (Kwalifikacje)",
    ...overrides,
  };
}

describe("zoneBadgeClass", () => {
  it("maps champions league to the solid CL badge", () => {
    expect(zoneBadgeClass("champions_league")).toBe(
      "bg-zone-cl text-on-zone",
    );
  });

  it("uses one solid badge for a cup zone", () => {
    expect(zoneBadgeClass("champions_league")).toBe(
      "bg-zone-cl text-on-zone",
    );
    expect(zoneBadgeClass("europa_league")).toBe("bg-zone-el text-on-zone");
  });

  it("maps every configured zone kind", () => {
    expect(zoneBadgeClass("europa_league")).toBe("bg-zone-el text-on-zone");
    expect(zoneBadgeClass("conference_league")).toBe(
      "bg-zone-ecl text-on-zone",
    );
    expect(zoneBadgeClass("promotion")).toBe(
      "bg-zone-promotion text-on-zone",
    );
    expect(zoneBadgeClass("promotion_playoff")).toBe(
      "bg-zone-playoff text-on-zone",
    );
    expect(zoneBadgeClass("relegation")).toBe(
      "bg-zone-relegation text-on-zone",
    );
    expect(zoneBadgeClass("relegation_playoff")).toBe(
      "bg-zone-relegation-playoff text-on-zone",
    );
  });

  it("uses the same solid badge for relegation", () => {
    expect(zoneBadgeClass("relegation")).toBe(
      "bg-zone-relegation text-on-zone",
    );
    expect(zoneBadgeClass("relegation_playoff")).toBe(
      "bg-zone-relegation-playoff text-on-zone",
    );
  });

  it("leaves an unknown or missing kind without a badge", () => {
    expect(zoneBadgeClass("midfield")).toBeNull();
    expect(zoneBadgeClass(null)).toBeNull();
  });
});

describe("formatPointAdjustment", () => {
  it("formats a deduction with a unicode minus and the reason", () => {
    expect(formatPointAdjustment(-4, "Decyzja związku")).toBe(
      "−4 pkt (Decyzja związku)",
    );
  });

  it("formats a positive correction with a plus", () => {
    expect(formatPointAdjustment(2, "powód")).toBe("+2 pkt (powód)");
  });

  it("hides the note when the adjustment is zero", () => {
    expect(formatPointAdjustment(0, "Decyzja związku")).toBeNull();
    expect(formatPointAdjustment(0, null)).toBeNull();
  });

  it("omits empty parentheses when the reason is missing", () => {
    expect(formatPointAdjustment(-4, null)).toBe("−4 pkt");
  });
});

describe("zoneKindForPosition", () => {
  const zones = [
    zone({
      sort_order: 1,
      position_from: 1,
      position_to: 2,
      zone_kind: "champions_league",
    }),
    zone({
      sort_order: 2,
      position_from: 3,
      position_to: 3,
      zone_kind: "europa_league",
    }),
    zone({
      sort_order: 3,
      position_from: 16,
      position_to: 18,
      zone_kind: "relegation",
    }),
  ];

  it("colors a projected place from the zone that covers it", () => {
    expect(zoneKindForPosition(zones, 1)).toBe("champions_league");
    expect(zoneKindForPosition(zones, 2)).toBe("champions_league");
    expect(zoneKindForPosition(zones, 3)).toBe("europa_league");
    expect(zoneKindForPosition(zones, 5)).toBeNull();
    expect(zoneKindForPosition(zones, 16)).toBe("relegation");
  });
});

describe("orderedStandingZones", () => {
  it("sorts the legend by sort_order without mutating the source", () => {
    const zones = [
      zone({ sort_order: 4, zone_kind: "relegation", label: "Spadek" }),
      zone({ sort_order: 1, label: "Awans – Liga Mistrzów (Kwalifikacje)" }),
      zone({ sort_order: 3, zone_kind: "conference_league" }),
    ];

    expect(orderedStandingZones(zones).map((item) => item.sort_order)).toEqual([
      1, 3, 4,
    ]);
    expect(zones.map((item) => item.sort_order)).toEqual([4, 1, 3]);
  });

  it("returns an empty list when there are no zones", () => {
    expect(orderedStandingZones([])).toEqual([]);
  });
});
