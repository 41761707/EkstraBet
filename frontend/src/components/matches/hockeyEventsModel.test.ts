import { describe, expect, it } from "vitest";

import type { HockeyMatchEvent } from "@/types/api";
import {
  groupHockeyEventsByPeriod,
  hockeyEventSecondaryText,
} from "@/components/matches/hockeyEventsModel";

function sampleEvent(
  overrides: Partial<HockeyMatchEvent> = {},
): HockeyMatchEvent {
  return {
    id: 1,
    team_id: 10,
    team_name: "Tampa Bay Lightning",
    player_id: 100,
    player_name: "Kucherov N.",
    event_id: 181,
    event_name: "Strzelec bramki",
    period: 1,
    event_time: "05:12",
    description: "Point B.",
    is_power_play: false,
    is_empty_net: false,
    side: "home",
    ...overrides,
  };
}

describe("groupHockeyEventsByPeriod", () => {
  it("keeps Streamlit period order and skips empty periods", () => {
    const events = [
      sampleEvent({ id: 1, period: 3, event_time: "01:00" }),
      sampleEvent({ id: 2, period: 1, event_time: "05:12" }),
      sampleEvent({ id: 3, period: 5, event_time: "00:00:01" }),
    ];

    const groups = groupHockeyEventsByPeriod(events);

    expect(groups.map((group) => group.label)).toEqual([
      "Tercja 1",
      "Tercja 3",
      "Rzuty karne",
    ]);
    expect(groups[0]?.events[0]?.id).toBe(2);
  });
});

describe("hockeyEventSecondaryText", () => {
  it("appends description when present", () => {
    expect(hockeyEventSecondaryText(sampleEvent())).toBe(
      "Kucherov N. (Point B.)",
    );
  });

  it("returns only the player name without description", () => {
    expect(
      hockeyEventSecondaryText(sampleEvent({ description: null })),
    ).toBe("Kucherov N.");
  });
});
