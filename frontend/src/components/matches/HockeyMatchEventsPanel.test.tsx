import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyMatchEventsPanel } from "@/components/matches/HockeyMatchEventsPanel";
import type { HockeyMatchEvent } from "@/types/api";

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

describe("HockeyMatchEventsPanel", () => {
  it("renders home events on the left and away events on the right", () => {
    const html = renderToStaticMarkup(
      <HockeyMatchEventsPanel
        homeTeamName="Tampa Bay Lightning"
        awayTeamName="Winnipeg Jets"
        events={[
          sampleEvent(),
          sampleEvent({
            id: 2,
            team_id: 20,
            team_name: "Winnipeg Jets",
            player_name: "Scheifele M.",
            event_name: "Kara mniejsza",
            description: "Zahaczanie",
            side: "away",
          }),
        ]}
      />,
    );

    expect(html).toContain("Tercja 1");
    expect(html).toContain("05:12 (Strzelec bramki)");
    expect(html).toContain("Kucherov N. (Point B.)");
    expect(html).toContain("Scheifele M. (Zahaczanie)");
    expect(html).toContain("Tampa Bay Lightning");
    expect(html).toContain("Winnipeg Jets");
  });

  it("shows empty-net and power-play badges", () => {
    const html = renderToStaticMarkup(
      <HockeyMatchEventsPanel
        homeTeamName="Home"
        awayTeamName="Away"
        events={[
          sampleEvent({ is_power_play: true }),
          sampleEvent({
            id: 2,
            is_empty_net: true,
            description: "Do pustej bramki",
          }),
        ]}
      />,
    );

    expect(html).toContain("PP");
    expect(html).toContain("EN");
  });

  it("shows an empty state when no periods have events", () => {
    const html = renderToStaticMarkup(
      <HockeyMatchEventsPanel
        homeTeamName="Home"
        awayTeamName="Away"
        events={[]}
      />,
    );

    expect(html).toContain("Brak zdarzeń meczowych");
  });
});
