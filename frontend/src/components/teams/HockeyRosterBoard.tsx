"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { LineShiftMark } from "@/components/teams/HockeyLineupChanges";
import {
  lineShiftsByPlayer,
  type LineShiftMarker,
} from "@/components/teams/lineupChangeLabels";
import {
  placePowerPlayUnit,
  playersOnPowerPlay,
  type PowerPlayUnit,
} from "@/components/teams/hockeyPowerPlaySlots";
import {
  countingFor,
  formatRosterStat,
  nextRosterSortState,
  rosterPlayerLabel,
  ROSTER_STAT_WINDOWS,
  sortRosterPlayers,
  type RosterSortKey,
  type RosterSortState,
  type RosterStatKey,
  type RosterStatWindow,
} from "@/components/teams/hockeyRosterStats";
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

const SKATER_COLUMNS: { key: RosterStatKey; label: string; title: string }[] = [
  { key: "games_played", label: "M", title: "Mecze" },
  { key: "goals", label: "G", title: "Gole" },
  { key: "assists", label: "A", title: "Asysty" },
  { key: "points", label: "Pkt", title: "Punkty" },
  { key: "shots_on_goal", label: "SOG", title: "Strzały na bramkę" },
  { key: "shots_per_game", label: "SOG/M", title: "Średnia strzałów na mecz" },
  { key: "average_toi", label: "TOI", title: "Średni czas na lodzie" },
];

const GOALIE_COLUMNS: { key: RosterStatKey; label: string; title: string }[] = [
  { key: "save_percentage", label: "SV%", title: "Skuteczność obron" },
  {
    key: "goals_against_average",
    label: "GAA",
    title: "Gole stracone na 60 minut",
  },
];

type StatColumn = { key: RosterStatKey; label: string; title: string };

export function HockeyRosterBoard({ roster }: { roster: HockeyTeamRoster }) {
  const [unitId, setUnitId] = useState<UnitId>("1");
  const [statsScope, setStatsScope] = useState<StatsScope>("unit");
  const [statsWindow, setStatsWindow] = useState<RosterStatWindow>("season");
  const sheet = sheetFor(roster, unitId);
  const shifts = lineShiftsByPlayer(roster.lineup_changes);
  const statsPlayers = statsScope === "unit" ? sheet.unitPlayers : allPlayers(roster);

  return (
    <div className="space-y-6">
      <UnitTabs unitId={unitId} onSelect={setUnitId} />
      <LineFormation
        wings={sheet.wings}
        back={sheet.back}
        showBack={sheet.showBack}
        overflow={sheet.overflow}
        shifts={shifts}
      />
      <GoalieRow
        players={playersIn(roster, "G")}
        windowId={statsWindow}
        shifts={shifts}
      />
      <RosterGroup
        title="Poza składem"
        players={playersIn(roster, "outside")}
      />
      <StatsPanel
        scope={statsScope}
        windowId={statsWindow}
        players={statsPlayers}
        onScope={setStatsScope}
        onWindow={setStatsWindow}
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
  shifts,
}: {
  wings: (HockeyRosterPlayer | null)[];
  back: (HockeyRosterPlayer | null)[];
  showBack: boolean;
  overflow: HockeyRosterPlayer[];
  shifts: ReadonlyMap<number, LineShiftMarker>;
}) {
  return (
    <div className="space-y-4">
      <div className="mx-auto grid max-w-3xl grid-cols-3 gap-3">
        {wings.map((player, index) => (
          <SkaterCard
            key={player?.player_id ?? `wing-${index}`}
            player={player}
            position={WING_SLOTS[index]}
            shift={shiftFor(player, shifts)}
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
              shift={shiftFor(player, shifts)}
            />
          ))}
        </div>
      ) : null}
      {overflow.length > 0 ? (
        <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-3">
          {overflow.map((player) => (
            <div key={player.player_id} className="w-40">
              <SkaterCard
                player={player}
                position={player.position || "—"}
                shift={shiftFor(player, shifts)}
              />
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
  shift,
}: {
  player: HockeyRosterPlayer | null;
  position: string;
  shift: LineShiftMarker | null;
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
      <div className="font-medium text-text">{rosterPlayerLabel(player)}</div>
      <div className="text-xs text-muted">
        {player.number === null ? "—" : `#${player.number}`}
      </div>
      {shift ? <LineShiftMark marker={shift} /> : null}
    </div>
  );
}

function shiftFor(
  player: HockeyRosterPlayer | null,
  shifts: ReadonlyMap<number, LineShiftMarker>,
): LineShiftMarker | null {
  if (!player) {
    return null;
  }
  return shifts.get(player.player_id) ?? null;
}

function GoalieRow({
  players,
  windowId,
  shifts,
}: {
  players: HockeyRosterPlayer[];
  windowId: RosterStatWindow;
  shifts: ReadonlyMap<number, LineShiftMarker>;
}) {
  if (players.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-text">Bramkarze</h3>
      <div className="flex flex-wrap justify-center gap-3">
        {orderedGoalies(players).map((player) => (
          <GoalieCard
            key={player.player_id}
            player={player}
            windowId={windowId}
            shift={shiftFor(player, shifts)}
          />
        ))}
      </div>
    </section>
  );
}

function GoalieCard({
  player,
  windowId,
  shift,
}: {
  player: HockeyRosterPlayer;
  windowId: RosterStatWindow;
  shift: LineShiftMarker | null;
}) {
  const role = goalieRole(player.line);
  const border = role === "Podstawowy" ? "border-accent" : "border-border";
  const counting = countingFor(player, windowId);
  return (
    <div className={`min-w-40 rounded-xl border bg-surface px-4 py-3 text-center ${border}`}>
      <div className="text-xs text-muted">G</div>
      {role ? <GoalieRoleBadge role={role} /> : null}
      <div className="font-medium text-text">{rosterPlayerLabel(player)}</div>
      <div className="text-xs text-muted">
        {player.number === null ? "—" : `#${player.number}`}
      </div>
      {shift ? <LineShiftMark marker={shift} /> : null}
      <div className="mt-1 text-sm text-text">
        {formatRosterStat(player, counting, "save_percentage")}
        <span className="text-muted"> SV%</span>
      </div>
      <div className="text-sm text-text">
        {formatRosterStat(player, counting, "goals_against_average")}
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
      <RosterTable players={players} windowId="season" />
    </section>
  );
}

function StatsPanel({
  scope,
  windowId,
  players,
  onScope,
  onWindow,
}: {
  scope: StatsScope;
  windowId: RosterStatWindow;
  players: HockeyRosterPlayer[];
  onScope: (scope: StatsScope) => void;
  onWindow: (windowId: RosterStatWindow) => void;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-text">Statystyki</h3>
          <div className="flex gap-2" role="group" aria-label="Okno statystyk">
            {ROSTER_STAT_WINDOWS.map((item) => (
              <ScopeButton
                key={item.id}
                label={item.label}
                title={item.title}
                active={windowId === item.id}
                onClick={() => onWindow(item.id)}
              />
            ))}
          </div>
        </div>
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
        <RosterTable players={players} windowId={windowId} />
      )}
    </section>
  );
}

function ScopeButton({
  label,
  active,
  title,
  onClick,
}: {
  label: string;
  active: boolean;
  title?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-pressed={active}
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

const IDENTITY_COLUMNS: {
  key: RosterSortKey;
  label: string;
  title: string;
  align: "left" | "center";
}[] = [
  { key: "name", label: "Zawodnik", title: "Zawodnik", align: "left" },
  { key: "position", label: "Poz", title: "Pozycja", align: "left" },
  { key: "number", label: "#", title: "Numer", align: "center" },
];

function RosterTable({
  players,
  windowId,
}: {
  players: HockeyRosterPlayer[];
  windowId: RosterStatWindow;
}) {
  const [sort, setSort] = useState<RosterSortState | null>(null);
  const columns = columnsFor(players);
  const rows = sort === null ? players : sortRosterPlayers(players, windowId, sort);

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            {IDENTITY_COLUMNS.map((column) => (
              <SortableHeader
                key={column.key}
                label={column.label}
                title={column.title}
                sortKey={column.key}
                sort={sort}
                align={column.align}
                onSort={(key) => setSort((current) => nextRosterSortState(current, key))}
              />
            ))}
            {columns.map((column) => (
              <SortableHeader
                key={column.key}
                label={column.label}
                title={column.title}
                sortKey={column.key}
                sort={sort}
                align="center"
                onSort={(key) => setSort((current) => nextRosterSortState(current, key))}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((player) => (
            <RosterRow
              key={player.player_id}
              columns={columns}
              player={player}
              windowId={windowId}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SortableHeader({
  label,
  title,
  sortKey,
  sort,
  align,
  onSort,
}: {
  label: string;
  title: string;
  sortKey: RosterSortKey;
  sort: RosterSortState | null;
  align: "left" | "center";
  onSort: (key: RosterSortKey) => void;
}) {
  const isActive = sort !== null && sort.key === sortKey;
  const indicator = !isActive || sort === null ? "" : sort.direction === "asc" ? "↑" : "↓";
  const justify = align === "center" ? "justify-center" : "";

  return (
    <th
      aria-sort={ariaSort(sort, sortKey)}
      className={`px-3 py-2 font-medium ${align === "center" ? "text-center" : "text-left"}`}
    >
      <button
        type="button"
        title={title}
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 rounded px-1 py-0.5 hover:text-text ${
          isActive ? "text-text" : "text-muted"
        } ${justify}`}
      >
        <span>{label}</span>
        {indicator ? (
          <span aria-hidden="true" className="text-accent-text">
            {indicator}
          </span>
        ) : null}
      </button>
    </th>
  );
}

function ariaSort(
  sort: RosterSortState | null,
  key: RosterSortKey,
): "ascending" | "descending" | "none" {
  if (sort === null || sort.key !== key) {
    return "none";
  }
  return sort.direction === "asc" ? "ascending" : "descending";
}

function RosterRow({
  columns,
  player,
  windowId,
}: {
  columns: StatColumn[];
  player: HockeyRosterPlayer;
  windowId: RosterStatWindow;
}) {
  const counting = countingFor(player, windowId);
  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2 font-medium text-text">
        <span>{rosterPlayerLabel(player)}</span>
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
          {formatRosterStat(player, counting, column.key)}
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

