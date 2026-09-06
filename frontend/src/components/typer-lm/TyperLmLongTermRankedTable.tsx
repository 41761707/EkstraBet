"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  formatLongTermStandingStats,
  formatLongTermTeamName,
  teamsById,
} from "@/lib/typerLmLongTerm";
import {
  classifyRankedPick,
  moveTeamInRanking,
  zoneForPosition,
  type RankedPickClassification,
  type RankedTableZone,
} from "@/lib/typerLmLongTermRanking";
import type { LongTermStandingTeam, LongTermTeam } from "@/types/api";

const POINTER_ACTIVATION_DISTANCE = 8;
const TOUCH_ACTIVATION_DELAY_MS = 250;
const TOUCH_ACTIVATION_TOLERANCE_PX = 8;
const RANKED_LIST_CLASS =
  "max-h-[min(70vh,42rem)] space-y-1 overflow-y-auto";
const DRAG_HANDLE_CLASS =
  "flex min-h-11 min-w-11 shrink-0 touch-none select-none items-center " +
  "justify-center";
export const RANKED_TOUCH_DRAG_HINT =
  "Na telefonie przytrzymaj uchwyt (kropki). Podświetlenie wskazuje aktualnie modyfikowaną pozycję.";
export const RANKED_ROW_ARMED_CLASS =
  "ring-2 ring-accent ring-offset-2 ring-offset-page";

export function rankedRowArmedClass(isArmed: boolean): string {
  return isArmed ? ` ${RANKED_ROW_ARMED_CLASS}` : "";
}
export const RANKED_SCREEN_READER_INSTRUCTIONS = {
  draggable:
    "Aby podnieść kafelek, naciśnij spację. Podczas przeciągania użyj " +
    "strzałek, aby zmienić pozycję. Naciśnij spację, aby upuścić, " +
    "albo Escape, aby anulować.",
};

const ZONE_ROW_CLASS: Record<RankedTableZone, string> = {
  top: "border-success-border bg-success-bg text-text",
  middle: "border-border bg-surface-muted text-text",
  bot: "border-danger-border bg-danger-bg text-text",
};

interface TyperLmLongTermRankedTableProps {
  candidates: readonly LongTermTeam[];
  teamIds: readonly number[];
  topZoneSize: number;
  botZoneSize: number;
  isLocked: boolean;
  resultTeamIds: readonly number[];
  teamNameDisplay: TeamNameDisplayPreference;
  onReorder: (teamIds: number[]) => void;
  standings?: readonly LongTermStandingTeam[];
}

export function TyperLmLongTermRankedTable({
  candidates,
  teamIds,
  topZoneSize,
  botZoneSize,
  isLocked,
  resultTeamIds,
  teamNameDisplay,
  onReorder,
  standings = [],
}: TyperLmLongTermRankedTableProps) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const [overId, setOverId] = useState<number | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const sensors = useSensors(
    useSensor(MouseSensor, {
      activationConstraint: { distance: POINTER_ACTIVATION_DISTANCE },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: TOUCH_ACTIVATION_DELAY_MS,
        tolerance: TOUCH_ACTIVATION_TOLERANCE_PX,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const rows = buildRankedRowModels(
    teamIds,
    candidates,
    standings,
    topZoneSize,
    botZoneSize,
    resultTeamIds,
    teamNameDisplay,
  );
  const list = (
    <RankedTableList
      rows={rows}
      isLocked={isLocked}
      pendingId={pendingId}
    />
  );

  if (isLocked) {
    return list;
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]}
      autoScroll={{ threshold: { x: 0, y: 0.15 } }}
      accessibility={{
        announcements: rankedTableAnnouncements(
          teamIds,
          new Map(rows.map((row) => [row.teamId, row.teamName])),
        ),
        screenReaderInstructions: RANKED_SCREEN_READER_INSTRUCTIONS,
      }}
      onDragPending={(event) => setPendingId(Number(event.id))}
      onDragAbort={() => setPendingId(null)}
      onDragStart={(event) => {
        setPendingId(null);
        handleRankedDragStart(event, setActiveId, setOverId);
      }}
      onDragOver={(event) => handleRankedDragOver(event, setOverId)}
      onDragCancel={() => {
        setActiveId(null);
        setOverId(null);
        setPendingId(null);
      }}
      onDragEnd={(event) => {
        setActiveId(null);
        setOverId(null);
        setPendingId(null);
        handleRankedDragEnd(event, teamIds, onReorder);
      }}
    >
      {list}
      <RankedDragOverlay
        row={overlayRowForDrag(
          rows.find((row) => row.teamId === activeId) ?? null,
          overId,
          teamIds,
          topZoneSize,
          botZoneSize,
        )}
      />
    </DndContext>
  );
}

function handleRankedDragStart(
  event: DragStartEvent,
  setActiveId: (teamId: number) => void,
  setOverId: (teamId: number) => void,
) {
  const teamId = Number(event.active.id);
  setActiveId(teamId);
  setOverId(teamId);
}

function handleRankedDragOver(
  event: DragOverEvent,
  setOverId: (teamId: number) => void,
) {
  if (event.over == null) {
    return;
  }
  setOverId(Number(event.over.id));
}

function handleRankedDragEnd(
  event: DragEndEvent,
  teamIds: readonly number[],
  onReorder: (teamIds: number[]) => void,
) {
  const { active, over } = event;
  if (over == null || active.id === over.id) {
    return;
  }
  const fromIndex = teamIds.indexOf(Number(active.id));
  const toIndex = teamIds.indexOf(Number(over.id));
  onReorder(moveTeamInRanking(teamIds, fromIndex, toIndex));
}

function overlayRowForDrag(
  row: RankedRowModel | null,
  overId: number | null,
  teamIds: readonly number[],
  topZoneSize: number,
  botZoneSize: number,
): RankedRowModel | null {
  if (row === null) {
    return null;
  }
  const position = overlayPositionForDrag(overId, teamIds);
  if (position == null) {
    return { ...row, showHandle: true };
  }
  const zone = zoneForPosition(
    position,
    teamIds.length,
    topZoneSize,
    botZoneSize,
  );
  return {
    ...row,
    position,
    zone,
    zoneLabel: zoneBadgeLabel(zone, topZoneSize, botZoneSize),
    showHandle: true,
  };
}

export function overlayPositionForDrag(
  overId: number | null,
  teamIds: readonly number[],
): number | null {
  if (overId == null) {
    return null;
  }
  const overIndex = teamIds.indexOf(overId);
  if (overIndex < 0) {
    return null;
  }
  return overIndex + 1;
}

export function rankedTableAnnouncements(
  teamIds: readonly number[],
  teamNames: ReadonlyMap<number, string>,
): Announcements {
  const count = teamIds.length;
  return {
    onDragStart({ active }) {
      return announcePickup(Number(active.id), teamIds, teamNames, count);
    },
    onDragOver({ active, over }) {
      return announceMove(Number(active.id), over?.id, teamIds, teamNames, count);
    },
    onDragEnd({ active, over }) {
      return announceDrop(Number(active.id), over?.id, teamIds, teamNames, count);
    },
    onDragCancel({ active }) {
      const name = teamNameForAnnouncement(Number(active.id), teamNames);
      return `Przeciąganie anulowane. ${name} wrócił na poprzednie miejsce.`;
    },
  };
}

function announcePickup(
  teamId: number,
  teamIds: readonly number[],
  names: ReadonlyMap<number, string>,
  count: number,
): string {
  const name = teamNameForAnnouncement(teamId, names);
  const position = teamIds.indexOf(teamId) + 1;
  return `Podniesiono ${name}. Pozycja ${position} z ${count}.`;
}

function announceMove(
  teamId: number,
  overId: unknown,
  teamIds: readonly number[],
  names: ReadonlyMap<number, string>,
  count: number,
): string | undefined {
  const name = teamNameForAnnouncement(teamId, names);
  if (overId == null) {
    return `Przeniesiono ${name} poza listę.`;
  }
  const position = teamIds.indexOf(Number(overId)) + 1;
  return `Przeniesiono ${name} na pozycję ${position} z ${count}.`;
}

function announceDrop(
  teamId: number,
  overId: unknown,
  teamIds: readonly number[],
  names: ReadonlyMap<number, string>,
  count: number,
): string {
  const name = teamNameForAnnouncement(teamId, names);
  if (overId == null) {
    return `Upuszczono ${name}.`;
  }
  const position = teamIds.indexOf(Number(overId)) + 1;
  return `Upuszczono ${name} na pozycji ${position} z ${count}.`;
}

function teamNameForAnnouncement(
  teamId: number,
  names: ReadonlyMap<number, string>,
): string {
  return names.get(teamId) ?? `#${teamId}`;
}

interface RankedRowModel {
  teamId: number;
  position: number;
  teamName: string;
  standingStats: string | null;
  zone: RankedTableZone;
  zoneLabel: string | null;
  hitLabel: string | null;
  showHandle: boolean;
}

function buildRankedRowModels(
  teamIds: readonly number[],
  candidates: readonly LongTermTeam[],
  standings: readonly LongTermStandingTeam[],
  topZoneSize: number,
  botZoneSize: number,
  resultTeamIds: readonly number[],
  teamNameDisplay: TeamNameDisplayPreference,
): RankedRowModel[] {
  const teams = teamsById(candidates);
  const statsById = standingStatsByTeamId(standings);
  const selectionSize = teamIds.length;
  return teamIds.map((teamId, index) =>
    buildRankedRowModel(
      teamId,
      index,
      selectionSize,
      topZoneSize,
      botZoneSize,
      teams,
      statsById,
      resultTeamIds,
      teamNameDisplay,
    ),
  );
}

function standingStatsByTeamId(
  standings: readonly LongTermStandingTeam[],
): Map<number, string> {
  return new Map(
    standings.map((team) => [team.team_id, formatLongTermStandingStats(team)]),
  );
}

function buildRankedRowModel(
  teamId: number,
  index: number,
  selectionSize: number,
  topZoneSize: number,
  botZoneSize: number,
  teams: Map<number, LongTermTeam>,
  statsById: Map<number, string>,
  resultTeamIds: readonly number[],
  teamNameDisplay: TeamNameDisplayPreference,
): RankedRowModel {
  const position = index + 1;
  const zone = zoneForPosition(
    position,
    selectionSize,
    topZoneSize,
    botZoneSize,
  );
  const team = teams.get(teamId);
  const classification = classifyRankedPick(
    teamId,
    position,
    resultTeamIds,
    selectionSize,
    topZoneSize,
    botZoneSize,
  );
  return {
    teamId,
    position,
    teamName: team
      ? formatLongTermTeamName(team, teamNameDisplay)
      : `#${teamId}`,
    standingStats: statsById.get(teamId) ?? null,
    zone,
    zoneLabel: zoneBadgeLabel(zone, topZoneSize, botZoneSize),
    hitLabel: rankedHitLabel(classification, zone),
    showHandle: false,
  };
}

function RankedTableList({
  rows,
  isLocked,
  pendingId,
}: {
  rows: readonly RankedRowModel[];
  isLocked: boolean;
  pendingId: number | null;
}) {
  const items = rows.map((row) => String(row.teamId));
  const list = (
    <div className="space-y-2">
      {isLocked ? null : (
        <p className="text-xs text-muted">{RANKED_TOUCH_DRAG_HINT}</p>
      )}
      <ol className={RANKED_LIST_CLASS}>
        {rows.map((row) =>
          isLocked ? (
            <StaticRankedRow key={row.teamId} row={row} />
          ) : (
            <SortableRankedRow
              key={row.teamId}
              row={row}
              isArmed={pendingId === row.teamId}
            />
          ),
        )}
      </ol>
    </div>
  );
  if (isLocked) {
    return list;
  }
  return (
    <SortableContext items={items} strategy={verticalListSortingStrategy}>
      {list}
    </SortableContext>
  );
}

function SortableRankedRow({
  row,
  isArmed,
}: {
  row: RankedRowModel;
  isArmed: boolean;
}) {
  const sortable = useSortable({ id: String(row.teamId) });
  return (
    <li
      ref={sortable.setNodeRef}
      style={{
        transform: CSS.Transform.toString(sortable.transform),
        transition: sortable.transition,
      }}
      className={sortable.isDragging ? "opacity-40" : undefined}
    >
      <RankedRowView
        row={{ ...row, showHandle: true }}
        sortable={sortable}
        isArmed={isArmed && !sortable.isDragging}
      />
    </li>
  );
}

function StaticRankedRow({ row }: { row: RankedRowModel }) {
  return (
    <li>
      <RankedRowView row={row} />
    </li>
  );
}

function RankedDragOverlay({ row }: { row: RankedRowModel | null }) {
  if (row === null) {
    return <DragOverlay dropAnimation={null} />;
  }
  return (
    <DragOverlay dropAnimation={null}>
      <RankedRowView row={{ ...row, showHandle: true }} isArmed={true} />
    </DragOverlay>
  );
}

function RankedRowView({
  row,
  sortable,
  isArmed = false,
}: {
  row: RankedRowModel;
  sortable?: ReturnType<typeof useSortable>;
  isArmed?: boolean;
}) {
  return (
    <div
      className={
        `flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ` +
        `transition-shadow ${ZONE_ROW_CLASS[row.zone]}` +
        rankedRowArmedClass(isArmed)
      }
    >
      <RankedDragHandle row={row} sortable={sortable} isArmed={isArmed} />
      <span className="w-6 shrink-0 text-xs font-semibold text-muted">
        {row.position}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{row.teamName}</span>
        {row.standingStats ? (
          <span className="block truncate text-xs text-muted">
            {row.standingStats}
          </span>
        ) : null}
      </span>
      {row.zoneLabel ? (
        <span className="shrink-0 text-xs font-medium">{row.zoneLabel}</span>
      ) : null}
      {row.hitLabel ? (
        <span className="shrink-0 text-xs text-muted">{row.hitLabel}</span>
      ) : null}
    </div>
  );
}

function RankedDragHandle({
  row,
  sortable,
  isArmed = false,
}: {
  row: RankedRowModel;
  sortable?: ReturnType<typeof useSortable>;
  isArmed?: boolean;
}) {
  if (!row.showHandle) {
    return null;
  }
  const tone = isArmed ? "text-accent-text" : "text-muted";
  if (sortable) {
    return (
      <button
        type="button"
        className={`${DRAG_HANDLE_CLASS} ${tone} cursor-grab active:cursor-grabbing`}
        aria-label={`Przeciągnij ${row.teamName}`}
        {...sortable.attributes}
        {...sortable.listeners}
      >
        <DragHandleIcon />
      </button>
    );
  }
  return (
    <span className={`${DRAG_HANDLE_CLASS} ${tone}`} aria-hidden="true">
      <DragHandleIcon />
    </span>
  );
}

function zoneBadgeLabel(
  zone: RankedTableZone,
  topZoneSize: number,
  botZoneSize: number,
): string | null {
  if (zone === "top") {
    return `TOP ${topZoneSize}`;
  }
  if (zone === "bot") {
    return `BOT ${botZoneSize}`;
  }
  return null;
}

function rankedHitLabel(
  classification: RankedPickClassification,
  zone: RankedTableZone,
): string | null {
  if (zone === "middle" || classification === "pending") {
    return null;
  }
  if (classification === "exact") {
    return "pozycja";
  }
  if (classification === "zone") {
    return "strefa";
  }
  return "pudło";
}

function DragHandleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="5" cy="4" r="1.2" fill="currentColor" />
      <circle cx="11" cy="4" r="1.2" fill="currentColor" />
      <circle cx="5" cy="8" r="1.2" fill="currentColor" />
      <circle cx="11" cy="8" r="1.2" fill="currentColor" />
      <circle cx="5" cy="12" r="1.2" fill="currentColor" />
      <circle cx="11" cy="12" r="1.2" fill="currentColor" />
    </svg>
  );
}
