import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyMatchLineupsPanel } from "@/components/matches/HockeyMatchLineupsPanel";
import type {
  HockeyLineupLine,
  HockeyLineupPlayer,
  HockeyMatchLineups,
  HockeyTeamLineup,
} from "@/types/api";

const HOME_TEAM_ID = 10;
const AWAY_TEAM_ID = 20;
const HOME_TEAM_NAME = "Columbus Blue Jackets";
const AWAY_TEAM_NAME = "Philadelphia Flyers";

function samplePlayer(
  overrides: Partial<HockeyLineupPlayer> = {},
): HockeyLineupPlayer {
  return {
    player_id: 1,
    player_name: "Player",
    team_id: HOME_TEAM_ID,
    position: "C",
    number: 19,
    line: 1,
    ...overrides,
  };
}

function emptyLines(): HockeyLineupLine[] {
  return [1, 2, 3, 4].map((line) => ({ line, players: [] }));
}

function teamLineup(
  teamId: number,
  teamName: string,
  lines: HockeyLineupLine[],
): HockeyTeamLineup {
  return { team_id: teamId, team_name: teamName, lines };
}

function firstLinePlayers(): HockeyLineupPlayer[] {
  return [
    samplePlayer({
      player_id: 1898,
      player_name: "Fantilli A.",
      position: "C",
      number: 19,
    }),
    samplePlayer({
      player_id: 1432,
      player_name: "Marchment M.",
      position: "LW",
      number: 17,
    }),
    samplePlayer({
      player_id: 1776,
      player_name: "Marchenko K.",
      position: "RW",
      number: 86,
    }),
    samplePlayer({
      player_id: 199,
      player_name: "Werenski Z.",
      position: "D",
      number: 8,
    }),
    samplePlayer({
      player_id: 551,
      player_name: "Severson D.",
      position: "D",
      number: 78,
    }),
    samplePlayer({
      player_id: 1334,
      player_name: "Merzlikins E.",
      position: "G",
      number: 90,
    }),
  ];
}

function lineupsWithHomeFirstLine(): HockeyMatchLineups {
  const homeLines = emptyLines();
  homeLines[0] = { line: 1, players: firstLinePlayers() };
  return {
    home: teamLineup(HOME_TEAM_ID, HOME_TEAM_NAME, homeLines),
    away: teamLineup(AWAY_TEAM_ID, AWAY_TEAM_NAME, emptyLines()),
  };
}

function renderPanel(lineups: HockeyMatchLineups): string {
  return renderToStaticMarkup(
    <HockeyMatchLineupsPanel
      lineups={lineups}
      homeTeamName={HOME_TEAM_NAME}
      awayTeamName={AWAY_TEAM_NAME}
    />,
  );
}

describe("HockeyMatchLineupsPanel", () => {
  it("renders first-line names, team names and line labels", () => {
    const html = renderPanel(lineupsWithHomeFirstLine());

    expect(html).toContain("Pierwsza linia");
    expect(html).toContain(HOME_TEAM_NAME);
    expect(html).toContain(AWAY_TEAM_NAME);
    expect(html).toContain("Fantilli A.");
    expect(html).toContain("Marchment M.");
    expect(html).toContain("Marchenko K.");
    expect(html).toContain("Werenski Z.");
    expect(html).toContain("Severson D.");
    expect(html).toContain("Merzlikins E.");
    const tableOrder = [
      "Merzlikins E.",
      "Werenski Z.",
      "Severson D.",
      "Marchment M.",
      "Fantilli A.",
      "Marchenko K.",
    ];
    const indexes = tableOrder.map((name) => html.indexOf(name));
    expect(indexes.every((index) => index >= 0)).toBe(true);
    expect([...indexes].sort((a, b) => a - b)).toEqual(indexes);
  });

  it("shows an empty state when line 4 has no players", () => {
    // static markup zawsze pokazuje linię 1; puste linie 1-4 dają ten sam empty state
    const html = renderPanel({
      home: teamLineup(HOME_TEAM_ID, HOME_TEAM_NAME, emptyLines()),
      away: teamLineup(AWAY_TEAM_ID, AWAY_TEAM_NAME, emptyLines()),
    });

    expect(html).toContain("Czwarta linia");
    expect(html).toContain("Brak zawodników");
    expect(html).toContain("Ta linia nie ma wpisów w składzie.");
  });
});
