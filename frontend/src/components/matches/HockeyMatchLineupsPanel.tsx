"use client";

import { useState } from "react";

import { HockeyRink } from "@/components/matches/HockeyRink";
import {
  goalieStartLabels,
  HOCKEY_LINE_TABS,
  linePlayers,
  lineupSourceLabel,
  lineupStatusLabel,
  playersOnLineSheet,
  predictionStageLabel,
  rinkMarkersForLine,
  sortPlayersForLineTable,
  type GoalieStartLabel,
} from "@/components/matches/hockeyLineupModel";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  HockeyLineupPlayer,
  HockeyMatchLineups,
  HockeyPredictionStage,
  HockeyTeamLineup,
} from "@/types/api";

interface HockeyMatchLineupsPanelProps {
  lineups: HockeyMatchLineups;
  homeTeamName: string;
  awayTeamName: string;
  predictionStage?: HockeyPredictionStage | null;
}

type HockeyLineNumber = (typeof HOCKEY_LINE_TABS)[number]["line"];

const LINE_TAB_ACTIVE_CLASS = "border-accent text-accent-text-hover";
const LINE_TAB_IDLE_CLASS = "border-transparent text-muted hover:text-text";
const PROBABLE_BADGE_CLASS =
  "rounded border border-warning-border bg-warning-bg px-1.5 py-0.5 text-xs font-medium text-warning-text";
const CONFIRMED_BADGE_CLASS =
  "rounded border border-success-border bg-success-bg px-1.5 py-0.5 text-xs font-medium text-success-text";
const STAGE_BADGE_CLASS =
  "rounded border border-info-border bg-info-bg px-1.5 py-0.5 text-xs font-medium text-info-text";

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

function GoalieStartList({ goalies }: { goalies: GoalieStartLabel[] }) {
  if (goalies.length === 0) {
    return null;
  }
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted">
      {goalies.map((goalie) => (
        <li key={goalie.playerId}>
          <span className="font-medium text-text">{goalie.playerName}</span>
          {` ${goalie.percent}`}
        </li>
      ))}
    </ul>
  );
}

function LineupStatusBadge({ team }: { team: HockeyTeamLineup }) {
  const statusLabel = lineupStatusLabel(team.lineup_status);
  if (!statusLabel) {
    return null;
  }
  const sourceLabel = lineupSourceLabel(team.source);
  const badgeClass =
    team.lineup_status === "confirmed"
      ? CONFIRMED_BADGE_CLASS
      : PROBABLE_BADGE_CLASS;

  return (
    <div className="space-y-2">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <span className={badgeClass}>{statusLabel}</span>
        {sourceLabel ? (
          <span className="text-muted">Źródło: {sourceLabel}</span>
        ) : null}
      </p>
      <GoalieStartList goalies={goalieStartLabels(team)} />
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
  const sheetPlayers = playersOnLineSheet(linePlayers(team, activeLine), activeLine);
  const tablePlayers = sortPlayersForLineTable(sheetPlayers, activeLine);

  return (
    <section className="min-w-0 space-y-3">
      <h3 className="text-lg font-semibold text-text">{teamName}</h3>
      <LineupStatusBadge team={team} />
      <HockeyLineTabButtons activeLine={activeLine} onChange={setActiveLine} />
      {sheetPlayers.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak zawodników"
          message="Ta linia nie ma wpisów w składzie."
        />
      ) : (
        <>
          <HockeyLineupTable players={tablePlayers} />
          <HockeyRink markers={rinkMarkersForLine(sheetPlayers)} />
        </>
      )}
    </section>
  );
}

export function HockeyMatchLineupsPanel({
  lineups,
  homeTeamName,
  awayTeamName,
  predictionStage = null,
}: HockeyMatchLineupsPanelProps) {
  const stageLabel = predictionStageLabel(predictionStage);

  return (
    <div className="space-y-4">
      {stageLabel ? <p className={STAGE_BADGE_CLASS}>{stageLabel}</p> : null}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <HockeyTeamLineupColumn team={lineups.home} teamName={homeTeamName} />
        <HockeyTeamLineupColumn team={lineups.away} teamName={awayTeamName} />
      </div>
    </div>
  );
}
