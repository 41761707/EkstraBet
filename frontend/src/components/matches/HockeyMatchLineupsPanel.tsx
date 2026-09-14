"use client";

import { useState } from "react";

import { HockeyRink } from "@/components/matches/HockeyRink";
import {
  HOCKEY_LINE_TABS,
  linePlayers,
  rinkMarkersForLine,
  sortPlayersForLineTable,
} from "@/components/matches/hockeyLineupModel";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  HockeyLineupPlayer,
  HockeyMatchLineups,
  HockeyTeamLineup,
} from "@/types/api";

interface HockeyMatchLineupsPanelProps {
  lineups: HockeyMatchLineups;
  homeTeamName: string;
  awayTeamName: string;
}

type HockeyLineNumber = (typeof HOCKEY_LINE_TABS)[number]["line"];

const LINE_TAB_ACTIVE_CLASS = "border-accent text-accent-text-hover";
const LINE_TAB_IDLE_CLASS = "border-transparent text-muted hover:text-text";

function formatJerseyNumber(value: number | null): string {
  return value === null ? "—" : String(value);
}

function HockeyLineupTable({ players }: { players: HockeyLineupPlayer[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Zawodnik</th>
            <th className="px-3 py-2 font-medium">Pozycja</th>
            <th className="px-3 py-2 text-center font-medium">Numer</th>
          </tr>
        </thead>
        <tbody>
          {players.map((player) => (
            <tr
              key={player.player_id}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-3 py-2 font-medium text-text">
                {player.player_name}
              </td>
              <td className="px-3 py-2 text-muted">{player.position}</td>
              <td className="px-3 py-2 text-center text-text">
                {formatJerseyNumber(player.number)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HockeyLineTabButtons({
  activeLine,
  onChange,
}: {
  activeLine: HockeyLineNumber;
  onChange: (line: HockeyLineNumber) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-1">
      {HOCKEY_LINE_TABS.map((tab) => {
        const isActive = tab.line === activeLine;
        return (
          <button
            key={tab.line}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(tab.line)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
              isActive ? LINE_TAB_ACTIVE_CLASS : LINE_TAB_IDLE_CLASS
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

function HockeyTeamLineupColumn({
  team,
  teamName,
}: {
  team: HockeyTeamLineup;
  teamName: string;
}) {
  const [activeLine, setActiveLine] = useState<HockeyLineNumber>(1);
  const players = linePlayers(team, activeLine);
  const tablePlayers = sortPlayersForLineTable(players, activeLine);

  return (
    <section className="min-w-0 space-y-3">
      <h3 className="text-lg font-semibold text-text">{teamName}</h3>
      <HockeyLineTabButtons activeLine={activeLine} onChange={setActiveLine} />
      {players.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak zawodników"
          message="Ta linia nie ma wpisów w składzie."
        />
      ) : (
        <>
          <HockeyLineupTable players={tablePlayers} />
          <HockeyRink markers={rinkMarkersForLine(players)} />
        </>
      )}
    </section>
  );
}

export function HockeyMatchLineupsPanel({
  lineups,
  homeTeamName,
  awayTeamName,
}: HockeyMatchLineupsPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <HockeyTeamLineupColumn team={lineups.home} teamName={homeTeamName} />
      <HockeyTeamLineupColumn team={lineups.away} teamName={awayTeamName} />
    </div>
  );
}
