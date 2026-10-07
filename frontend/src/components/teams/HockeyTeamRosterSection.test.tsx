import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyTeamRosterSection } from "@/components/teams/HockeyTeamRosterSection";
import type { HockeyRosterPlayer, HockeyTeamRoster } from "@/types/api";

function player(
  overrides: Partial<HockeyRosterPlayer> = {},
): HockeyRosterPlayer {
  return {
    player_id: 1,
    first_name: "Adam",
    last_name: "Center",
    common_name: "Center A.",
    country: "Canada",
    position: "C",
    number: 19,
    line: 1,
    pp_unit: null,
    is_injured: false,
    injury_status: null,
    injury_note: null,
    games_played: 10,
    goals: 4,
    assists: 6,
    points: 10,
    shots_on_goal: 28,
    average_toi: "18:12",
    save_percentage: null,
    goals_against_average: null,
    in_last_lineup: true,
    ...overrides,
  };
}

function rosterWithDisplacedGoalies(): HockeyTeamRoster {
  const base = roster();
  return {
    ...base,
    groups: [
      {
        group_id: "injured",
        players: [
          player({
            player_id: 9,
            common_name: "Hurt Skater",
            position: "C",
            is_injured: true,
            injury_note: "Lower body",
          }),
          player({
            player_id: 11,
            common_name: "Hurt Goalie",
            position: "G",
            is_injured: true,
            line: null,
            in_last_lineup: false,
            save_percentage: 91.5,
            goals_against_average: 2.4,
          }),
        ],
      },
      {
        group_id: "outside",
        players: [
          player({
            player_id: 6,
            common_name: "Scratch S.",
            position: "C",
            line: null,
            in_last_lineup: false,
          }),
          player({
            player_id: 12,
            common_name: "Elvis Merzlikins",
            position: "G",
            line: null,
            in_last_lineup: false,
            save_percentage: 90.1,
            goals_against_average: 2.15,
          }),
        ],
      },
    ],
  };
}

function sliceBetween(html: string, start: string, end: string): string {
  const after = html.split(start)[1] ?? "";
  if (!end) {
    return after;
  }
  return after.split(end)[0] ?? "";
}

function rowOf(html: string, name: string): string {
  return html.split("<tr").find((row) => row.includes(name)) ?? "";
}

function rosterWithGoalieDepth(): HockeyTeamRoster {
  const base = roster();
  return {
    ...base,
    groups: base.groups.map((group) => {
      if (group.group_id !== "G") {
        return group;
      }
      return {
        group_id: "G",
        players: [
          player({
            player_id: 31,
            common_name: "Backup B.",
            position: "G",
            line: 2,
            save_percentage: 90,
            goals_against_average: 2.5,
          }),
          player({
            player_id: 30,
            common_name: "Starter S.",
            position: "G",
            line: 1,
            save_percentage: 91,
            goals_against_average: 2.1,
          }),
        ],
      };
    }),
  };
}

function rosterWithSecondLine(): HockeyTeamRoster {
  const base = roster();
  return {
    ...base,
    groups: [
      ...base.groups,
      {
        group_id: "F2",
        players: [
          player({
            player_id: 20,
            common_name: "Second S.",
            line: 2,
          }),
        ],
      },
    ],
  };
}

function roster(): HockeyTeamRoster {
  return {
    team_id: 870,
    team_name: "Columbus Blue Jackets",
    goalkeepers: [],
    defensemen: [],
    forwards: [],
    injured_players: 1,
    groups: [
      {
        group_id: "F1",
        players: [player()],
      },
      {
        group_id: "G",
        players: [
          player({
            player_id: 5,
            common_name: "Goalie G.",
            position: "G",
            line: null,
            games_played: 8,
            goals: 0,
            assists: 0,
            points: 0,
            shots_on_goal: 0,
            average_toi: "58:10",
            save_percentage: 90,
            goals_against_average: 2,
          }),
        ],
      },
      {
        group_id: "injured",
        players: [
          player({
            player_id: 9,
            common_name: "Hurt H.",
            is_injured: true,
            injury_status: null,
            injury_note: "Lower body",
          }),
        ],
      },
      {
        group_id: "outside",
        players: [
          player({
            player_id: 6,
            common_name: "Scratch S.",
            line: null,
            in_last_lineup: false,
          }),
        ],
      },
    ],
  };
}

describe("HockeyTeamRosterSection", () => {
  it("renders lines, goalie rates, the injury badge and players outside the lineup", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection roster={roster()} />,
    );

    expect(html).toContain("Aktualny skład drużyny");
    expect(html).toContain("1. piątka");
    expect(html).toContain("2. piątka");
    expect(html).toContain("3. piątka");
    expect(html).toContain("4. linia");
    expect(html).toContain("Power Play 1");
    expect(html).toContain("Power Play 2");
    expect(html).toContain("Center A.");
    expect(html).toContain("Bramkarze");
    expect(html).toContain("90.00%");
    expect(html).toContain("2.00");
    const stats = sliceBetween(html, "Statystyki", "Kontuzjowani");
    expect(stats).toContain("Center A.");
    expect(stats).not.toContain("SV%");
    expect(stats).not.toContain("GAA");
    expect(html.indexOf("Statystyki")).toBeLessThan(html.indexOf("Kontuzjowani"));
    expect(html.indexOf("Poza składem")).toBeLessThan(html.indexOf("Statystyki"));
    expect(html).toContain("Kontuzja");
    expect(html).toContain("Lower body");
    expect(html).toContain("Poza składem");
    expect(html).toContain("Scratch S.");
    expect(html).toContain("Cały skład");
    expect(html).not.toContain("Para 2");
  });

  it("shows goalie rates for a goalie outside the lineup or injured", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection roster={rosterWithDisplacedGoalies()} />,
    );
    const outside = sliceBetween(html, "Poza składem", "Kontuzjowani");
    const injured = sliceBetween(html, "Kontuzjowani", "");

    expect(injured).toContain("SV%");
    expect(injured).toContain("GAA");
    expect(injured).toContain("Hurt Goalie");
    expect(injured).toContain("91.50%");
    expect(injured).toContain("2.40");
    expect(rowOf(injured, "Hurt Skater")).toContain("—");
    expect(rowOf(injured, "Hurt Skater")).not.toContain("%");

    expect(outside).toContain("SV%");
    expect(outside).toContain("GAA");
    expect(outside).toContain("Elvis Merzlikins");
    expect(outside).toContain("90.10%");
    expect(outside).toContain("2.15");
    expect(rowOf(outside, "Scratch S.")).toContain("—");
    expect(rowOf(outside, "Scratch S.")).not.toContain("%");
  });

  it("keeps the other lines behind their tabs", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection roster={rosterWithSecondLine()} />,
    );

    expect(html).toContain("1. piątka");
    expect(html).toContain("Center A.");
    expect(html).toContain("2. piątka");
    expect(html).not.toContain("Second S.");
  });

  it("labels the primary goalie from roster line ahead of the backup", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection roster={rosterWithGoalieDepth()} />,
    );
    const goalies = sliceBetween(html, "Bramkarze", "Statystyki");

    expect(goalies.indexOf("Starter S.")).toBeLessThan(goalies.indexOf("Backup B."));
    expect(goalies.indexOf("Podstawowy")).toBeLessThan(goalies.indexOf("Rezerwowy"));
    expect(goalies).toContain("border-accent");
  });

  it("shows an error instead of an empty roster", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection
        roster={null}
        errorMessage="Roster is available only for hockey teams"
      />,
    );

    expect(html).toContain("Nie udało się załadować składu");
    expect(html).not.toContain("1. piątka");
  });

  it("shows an empty state when the team has no roster rows", () => {
    const html = renderToStaticMarkup(
      <HockeyTeamRosterSection
        roster={{ ...roster(), groups: [], injured_players: 0 }}
      />,
    );

    expect(html).toContain("Brak składu");
    expect(html).not.toContain("Center A.");
  });
});
