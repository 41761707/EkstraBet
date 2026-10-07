"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import {
  placePowerPlayUnit,
  playersOnPowerPlay,
  type PowerPlayUnit,
} from "@/components/teams/hockeyPowerPlaySlots";
import type { HockeyRosterPlayer, HockeyTeamRoster } from "@/types/api";

const LINE_UNITS = [
  { id: "1", label: "1. piątka", forwardGroup: "F1", defenseGroup: "D1" },
  { id: "2", label: "2. piątka", forwardGroup: "F2", defenseGroup: "D2" },
  { id: "3", label: "3. piątka", forwardGroup: "F3", defenseGroup: "D3" },
  { id: "4", label: "4. linia", forwardGroup: "F4", defenseGroup: null },
] as const;

const POWER_PLAY_UNITS = [
  { id: "pp1", label: "Power Play 1", unit: 1 },
  { id: "pp2", label: "Power Play 2", unit: 2 },
] as const;

const UNIT_TABS = [
  ...LINE_UNITS.map((unit) => ({ id: unit.id, label: unit.label })),
  ...POWER_PLAY_UNITS.map((unit) => ({ id: unit.id, label: unit.label })),
];

type UnitId = (typeof UNIT_TABS)[number]["id"];
type StatsScope = "unit" | "roster";

const WING_SLOTS = ["LW", "C", "RW"] as const;
const GOALIE_POSITION = "G";
const GOALIE_ROLES = {
  1: "Podstawowy",
  2: "Rezerwowy",
} as const;

const SKATER_COLUMNS: { key: StatKey; label: string; title: string }[] = [
  { key: "games_played", label: "M", title: "Mecze" },
  { key: "goals", label: "G", title: "Gole" },
  { key: "assists", label: "A", title: "Asysty" },
  { key: "points", label: "Pkt", title: "Punkty" },
  { key: "shots_on_goal", label: "SOG", title: "Strzały na bramkę" },
  { key: "average_toi", label: "TOI", title: "Średni czas na lodzie" },
];

const GOALIE_COLUMNS: { key: StatKey; label: string; title: string }[] = [
  { key: "save_percentage", label: "SV%", title: "Skuteczność obron" },
  {
    key: "goals_against_average",
    label: "GAA",
    title: "Gole stracone na 60 minut",
  },
];

type StatKey =
  | "games_played"
  | "goals"
  | "assists"
  | "points"
  | "shots_on_goal"
  | "average_toi"
  | "save_percentage"
  | "goals_against_average";

type StatColumn = { key: StatKey; label: string; title: string };

export function HockeyRosterBoard({ roster }: { roster: HockeyTeamRoster }) {
  const [unitId, setUnitId] = useState<UnitId>("1");
  const [statsScope, setStatsScope] = useState<StatsScope>("unit");
  const sheet = sheetFor(roster, unitId);
  const statsPlayers = statsScope === "unit" ? sheet.unitPlayers : allPlayers(roster);

  return (
    <div className="space-y-6">
      <UnitTabs unitId={unitId} onSelect={setUnitId} />
      <LineFormation
        wings={sheet.wings}
        back={sheet.back}
        showBack={sheet.showBack}
        overflow={sheet.overflow}
      />
      <GoalieRow players={playersIn(roster, "G")} />
      <RosterGroup
        title="Poza składem"
        players={playersIn(roster, "outside")}
      />
      <StatsPanel
        scope={statsScope}
        players={statsPlayers}
        onScope={setStatsScope}
      />
      <RosterGroup
        title="Kontuzjowani"
        players={playersIn(roster, "injured")}
      />
    </div>
  );
}

function UnitTabs({
  unitId,
  onSelect,
}: {
  unitId: UnitId;
  onSelect: (unitId: UnitId) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-3" role="tablist">
      {UNIT_TABS.map((unit) => {
        const isActive = unit.id === unitId;
        return (
          <button
            key={unit.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelect(unit.id)}
            className={`rounded-full px-3 py-1.5 text-sm transition ${
              isActive
                ? "bg-accent text-on-accent"
                : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
            }`}
          >
            {unit.label}
          </button>
        );
      })}
    </div>
  );
}

function LineFormation({
  wings,
  back,
  showBack,
  overflow,
}: {
  wings: (HockeyRosterPlayer | null)[];
  back: (HockeyRosterPlayer | null)[];
  showBack: boolean;
  overflow: HockeyRosterPlayer[];
}) {
  return (
    <div className="space-y-4">
      <div className="mx-auto grid max-w-3xl grid-cols-3 gap-3">
        {wings.map((player, index) => (
          <SkaterCard
            key={player?.player_id ?? `wing-${index}`}
            player={player}
            position={WING_SLOTS[index]}
          />
        ))}
      </div>
      {showBack ? (
        <div className="mx-auto grid max-w-xl grid-cols-2 gap-8">
          {back.map((player, index) => (
            <SkaterCard
              key={player?.player_id ?? `pair-${index}`}
              player={player}
              position="D"
            />
          ))}
        </div>
      ) : null}
      {overflow.length > 0 ? (
        <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-3">
          {overflow.map((player) => (
            <div key={player.player_id} className="w-40">
              <SkaterCard player={player} position={player.position || "—"} />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function SkaterCard({
  player,
  position,
}: {
  player: HockeyRosterPlayer | null;
  position: string;
}) {
  if (!player) {
    return (
      <div
        className={[
          "rounded-xl border border-dashed border-border px-3 py-4",
          "text-center text-sm text-muted",
        ].join(" ")}
      >
        {position}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-3 text-center">
      <div className="text-xs text-muted">{player.position || position}</div>
      <div className="font-medium text-text">{playerLabel(player)}</div>
      <div className="text-xs text-muted">
        {player.number === null ? "—" : `#${player.number}`}
      </div>
    </div>
  );
}

function GoalieRow({ players }: { players: HockeyRosterPlayer[] }) {
  if (players.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-text">Bramkarze</h3>
      <div className="flex flex-wrap justify-center gap-3">
        {orderedGoalies(players).map((player) => (
          <GoalieCard key={player.player_id} player={player} />
        ))}
      </div>
    </section>
  );
}

function GoalieCard({ player }: { player: HockeyRosterPlayer }) {
  const role = goalieRole(player.line);
  const border = role === "Podstawowy" ? "border-accent" : "border-border";
  return (
    <div className={`min-w-40 rounded-xl border bg-surface px-4 py-3 text-center ${border}`}>
      <div className="text-xs text-muted">G</div>
      {role ? <GoalieRoleBadge role={role} /> : null}
      <div className="font-medium text-text">{playerLabel(player)}</div>
      <div className="text-xs text-muted">
        {player.number === null ? "—" : `#${player.number}`}
      </div>
      <div className="mt-1 text-sm text-text">
        {statText(player, "save_percentage")}
        <span className="text-muted"> SV%</span>
      </div>
      <div className="text-sm text-text">
        {statText(player, "goals_against_average")}
        <span className="text-muted"> GAA</span>
      </div>
    </div>
  );
}

function GoalieRoleBadge({ role }: { role: string }) {
  const className = role === "Podstawowy"
    ? "bg-accent-soft text-accent-text"
    : "border border-border text-muted";
  return (
    <div className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>
      {role}
    </div>
  );
}

function orderedGoalies(players: HockeyRosterPlayer[]): HockeyRosterPlayer[] {
  return [...players].sort((left, right) => goalieRank(left.line) - goalieRank(right.line));
}

function goalieRole(line: number | null): string | null {
  if (line === 1 || line === 2) {
    return GOALIE_ROLES[line];
  }
  return null;
}

function goalieRank(line: number | null): number {
  if (line === 1) {
    return 0;
  }
  if (line === 2) {
    return 1;
  }
  return 2;
}

function RosterGroup({
  title,
  players,
}: {
  title: string;
  players: HockeyRosterPlayer[];
}) {
  if (players.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      <RosterTable players={players} />
    </section>
  );
}

function StatsPanel({
  scope,
  players,
  onScope,
}: {
  scope: StatsScope;
  players: HockeyRosterPlayer[];
  onScope: (scope: StatsScope) => void;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-text">Statystyki</h3>
        <div className="flex gap-2">
          <ScopeButton
            label="Wybrana linia"
            active={scope === "unit"}
            onClick={() => onScope("unit")}
          />
          <ScopeButton
            label="Cały skład"
            active={scope === "roster"}
            onClick={() => onScope("roster")}
          />
        </div>
      </div>
      {players.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak zawodników"
          message="Ta linia nie ma jeszcze wpisanych zawodników."
        />
      ) : (
        <RosterTable players={players} />
      )}
    </section>
  );
}

function ScopeButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-sm transition ${
        active
          ? "bg-accent text-on-accent"
          : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
      }`}
    >
      {label}
    </button>
  );
}

function RosterTable({ players }: { players: HockeyRosterPlayer[] }) {
  const columns = columnsFor(players);
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Zawodnik</th>
            <th className="px-3 py-2 font-medium">Poz</th>
            <th className="px-3 py-2 text-center font-medium">#</th>
            {columns.map((column) => (
              <th
                key={column.key}
                title={column.title}
                className="px-3 py-2 text-center font-medium"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((player) => (
            <RosterRow key={player.player_id} columns={columns} player={player} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RosterRow({
  columns,
  player,
}: {
  columns: StatColumn[];
  player: HockeyRosterPlayer;
}) {
  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2 font-medium text-text">
        <span>{playerLabel(player)}</span>
        <InjuryBadge player={player} />
        {player.injury_note ? (
          <span className="mt-0.5 block text-xs font-normal text-muted">
            {player.injury_note}
          </span>
        ) : null}
      </td>
      <td className="px-3 py-2 text-muted">{player.position || "—"}</td>
      <td className="px-3 py-2 text-center text-text">
        {player.number === null ? "—" : player.number}
      </td>
      {columns.map((column) => (
        <td key={column.key} className="px-3 py-2 text-center text-text">
          {statText(player, column.key)}
        </td>
      ))}
    </tr>
  );
}

function InjuryBadge({ player }: { player: HockeyRosterPlayer }) {
  if (!player.is_injured) {
    return null;
  }

  const label = player.injury_status
    ? `Kontuzja: ${player.injury_status}`
    : "Kontuzja";

  return (
    <span
      className={[
        "ml-2 rounded border border-danger-border bg-danger-bg",
        "px-1.5 py-0.5 text-xs font-medium text-danger-text",
      ].join(" ")}
    >
      {label}
    </span>
  );
}

interface RosterSheet {
  wings: (HockeyRosterPlayer | null)[];
  back: (HockeyRosterPlayer | null)[];
  showBack: boolean;
  unitPlayers: HockeyRosterPlayer[];
  overflow: HockeyRosterPlayer[];
}

function sheetFor(roster: HockeyTeamRoster, unitId: UnitId): RosterSheet {
  const powerPlay = POWER_PLAY_UNITS.find((unit) => unit.id === unitId);
  if (powerPlay) {
    return powerPlaySheet(roster, powerPlay.unit);
  }
  const unit = LINE_UNITS.find((item) => item.id === unitId) ?? LINE_UNITS[0];
  const forwards = playersIn(roster, unit.forwardGroup);
  const defense = unit.defenseGroup ? playersIn(roster, unit.defenseGroup) : [];
  return {
    wings: placeWings(forwards),
    back: placePair(defense),
    showBack: unit.defenseGroup !== null,
    unitPlayers: [...forwards, ...defense],
    overflow: [],
  };
}

function powerPlaySheet(
  roster: HockeyTeamRoster,
  unit: PowerPlayUnit,
): RosterSheet {
  const unitPlayers = playersOnPowerPlay(roster, unit);
  const placed = placePowerPlayUnit(unitPlayers);
  return {
    wings: placed.wings,
    back: placed.back,
    showBack: true,
    unitPlayers,
    overflow: placed.overflow,
  };
}

function placeWings(
  players: HockeyRosterPlayer[],
): (HockeyRosterPlayer | null)[] {
  const slots: (HockeyRosterPlayer | null)[] = [null, null, null];
  const rest: HockeyRosterPlayer[] = [];
  for (const player of players) {
    const index = wingIndex(player.position);
    if (index >= 0 && slots[index] === null) {
      slots[index] = player;
      continue;
    }
    rest.push(player);
  }
  for (const player of rest) {
    const open = slots.findIndex((slot) => slot === null);
    if (open >= 0) {
      slots[open] = player;
    }
  }
  return slots;
}

function wingIndex(position: string): number {
  const code = position.trim().toUpperCase();
  return WING_SLOTS.findIndex((slot) => slot === code);
}

function placePair(
  players: HockeyRosterPlayer[],
): (HockeyRosterPlayer | null)[] {
  return [players[0] ?? null, players[1] ?? null];
}

function playersIn(roster: HockeyTeamRoster, groupId: string) {
  return roster.groups.find((group) => group.group_id === groupId)?.players ?? [];
}

function allPlayers(roster: HockeyTeamRoster): HockeyRosterPlayer[] {
  return roster.groups.flatMap((group) => group.players);
}

function columnsFor(players: HockeyRosterPlayer[]): StatColumn[] {
  // Bramkarz w „Poza składem” albo „Kontuzjowani” też dostaje SV% i GAA.
  if (players.some(isGoalie)) {
    return [...SKATER_COLUMNS, ...GOALIE_COLUMNS];
  }
  return SKATER_COLUMNS;
}

function isGoalie(player: HockeyRosterPlayer): boolean {
  return player.position.trim().toUpperCase() === GOALIE_POSITION;
}

function isGoalieStat(key: StatKey): boolean {
  return key === "save_percentage" || key === "goals_against_average";
}

function playerLabel(player: HockeyRosterPlayer): string {
  if (player.common_name) {
    return player.common_name;
  }
  return `${player.first_name} ${player.last_name}`.trim();
}

function statText(player: HockeyRosterPlayer, key: StatKey): string {
  if (isGoalieStat(key) && !isGoalie(player)) {
    return "—";
  }
  if (key === "average_toi") {
    return player.average_toi ?? "—";
  }
  if (key === "save_percentage") {
    return player.save_percentage === null
      ? "—"
      : `${player.save_percentage.toFixed(2)}%`;
  }
  if (key === "goals_against_average") {
    return player.goals_against_average === null
      ? "—"
      : player.goals_against_average.toFixed(2);
  }
  return String(player[key]);
}
