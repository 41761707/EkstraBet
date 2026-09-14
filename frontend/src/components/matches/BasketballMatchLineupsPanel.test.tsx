import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BasketballMatchLineupsPanel } from "@/components/matches/BasketballMatchLineupsPanel";
import type {
  BasketballLineupPlayer,
  BasketballMatchLineups,
  BasketballTeamLineup,
} from "@/types/api";

const HOME_TEAM_ID = 917;
const AWAY_TEAM_ID = 923;
const HOME_TEAM_NAME = "New Orleans Pelicans";
const AWAY_TEAM_NAME = "Portland Trail Blazers";

function player(
  overrides: Partial<BasketballLineupPlayer> &
    Pick<BasketballLineupPlayer, "player_id" | "player_name">,
): BasketballLineupPlayer {
  return {
    team_id: HOME_TEAM_ID,
    number: null,
    starter: true,
    ...overrides,
  };
}

function team(
  teamId: number,
  teamName: string,
  players: BasketballLineupPlayer[],
): BasketballTeamLineup {
  return {
    team_id: teamId,
    team_name: teamName,
    players,
  };
}

function pelicansRoster(): BasketballLineupPlayer[] {
  return [
    player({ player_id: 1, player_name: "Fears J.", number: 0, starter: true }),
    player({ player_id: 2, player_name: "Jones H.", number: 2, starter: true }),
    player({
      player_id: 22,
      player_name: "Queen D.",
      number: 22,
      starter: true,
    }),
    player({
      player_id: 25,
      player_name: "Murphy T.",
      number: 25,
      starter: true,
    }),
    player({ player_id: 41, player_name: "Bey S.", number: 41, starter: true }),
    player({
      player_id: 3,
      player_name: "Poole J.",
      number: 3,
      starter: false,
    }),
  ];
}

function renderPanel(lineups: BasketballMatchLineups): string {
  return renderToStaticMarkup(
    <BasketballMatchLineupsPanel
      lineups={lineups}
      homeTeamName={HOME_TEAM_NAME}
      awayTeamName={AWAY_TEAM_NAME}
    />,
  );
}

describe("BasketballMatchLineupsPanel", () => {
  it("renders team names, roster rows and starter marks", () => {
    const html = renderPanel({
      home: team(HOME_TEAM_ID, HOME_TEAM_NAME, pelicansRoster()),
      away: team(AWAY_TEAM_ID, AWAY_TEAM_NAME, []),
    });

    expect(html).toContain(HOME_TEAM_NAME);
    expect(html).toContain(AWAY_TEAM_NAME);
    expect(html).toContain("Fears J.");
    expect(html).toContain("Jones H.");
    expect(html).toContain("Queen D.");
    expect(html).toContain("Murphy T.");
    expect(html).toContain("Bey S.");
    expect(html).toContain("Poole J.");
    expect(html).toContain("⭐");
    expect(html).toContain("Ustawienie starterów na boisku");
    expect(html).toContain("Brak zawodników");
  });

  it("shows an empty state when a team has no players", () => {
    const html = renderPanel({
      home: team(HOME_TEAM_ID, HOME_TEAM_NAME, []),
      away: team(AWAY_TEAM_ID, AWAY_TEAM_NAME, []),
    });

    expect(html).toContain("Brak zawodników");
    expect(html).toContain("Skład tej drużyny nie jest dostępny.");
  });
});
