"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  classifyLongTermPick,
  filterLongTermCandidates,
  formatLongTermSelectionCounter,
  formatLongTermTeamName,
  selectedTeams,
} from "@/lib/typerLmLongTerm";
import type { LongTermTeam } from "@/types/api";

interface TyperLmLongTermTeamPickerProps {
  candidates: readonly LongTermTeam[];
  selectedIds: readonly number[];
  selectionSize: number;
  query?: string;
  isLocked: boolean;
  resultTeamIds: readonly number[];
  teamNameDisplay: TeamNameDisplayPreference;
  onQueryChange?: (query: string) => void;
  onToggle: (teamId: number) => void;
}

const DROPDOWN_PLACEHOLDER = "Wybierz drużynę";
const CHIP_BASE =
  "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs";
const LIST_BUTTON_BASE =
  "flex w-full items-center justify-between rounded-lg border px-3 py-2 " +
  "text-left text-sm transition";
const DROPDOWN_PANEL_CLASS =
  "absolute z-50 mt-1 w-full rounded-xl border border-border bg-surface " +
  "p-2 shadow-xl";

export function TyperLmLongTermTeamPicker({
  candidates,
  selectedIds,
  selectionSize,
  query = "",
  isLocked,
  resultTeamIds,
  teamNameDisplay,
  onQueryChange,
  onToggle,
}: TyperLmLongTermTeamPickerProps) {
  if (selectionSize === 1) {
    return (
      <SingleTeamDropdown
        candidates={candidates}
        selectedIds={selectedIds}
        isLocked={isLocked}
        resultTeamIds={resultTeamIds}
        teamNameDisplay={teamNameDisplay}
        onToggle={onToggle}
      />
    );
  }

  const visible = filterLongTermCandidates(candidates, query, teamNameDisplay);
  const chips = selectedTeams(candidates, selectedIds);

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-text">
        Wybrane {formatLongTermSelectionCounter(selectedIds.length, selectionSize)}
      </p>
      <SelectedTeamChips
        teams={chips}
        resultTeamIds={resultTeamIds}
        isLocked={isLocked}
        teamNameDisplay={teamNameDisplay}
        onToggle={onToggle}
      />
      <label className="flex flex-col gap-1 text-sm text-muted">
        Szukaj drużyny
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange?.(event.target.value)}
          className={`w-full rounded-md ${INPUT_CLASS_NAME}`}
          disabled={isLocked}
          autoComplete="off"
        />
      </label>
      <CandidateTeamList
        teams={visible}
        selectedIds={selectedIds}
        resultTeamIds={resultTeamIds}
        isLocked={isLocked}
        teamNameDisplay={teamNameDisplay}
        onToggle={onToggle}
      />
    </div>
  );
}

function SingleTeamDropdown({
  candidates,
  selectedIds,
  isLocked,
  resultTeamIds,
  teamNameDisplay,
  onToggle,
}: Omit<
  TyperLmLongTermTeamPickerProps,
  "selectionSize" | "query" | "onQueryChange"
>) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const selected = selectedTeams(candidates, selectedIds)[0] ?? null;
  const label = selected
    ? formatLongTermTeamName(selected, teamNameDisplay)
    : DROPDOWN_PLACEHOLDER;

  usePickerDismiss(isOpen, rootRef, setIsOpen);

  useEffect(() => {
    if (!isOpen) {
      setQuery("");
    }
  }, [isOpen]);

  function chooseTeam(teamId: number) {
    if (!selectedIds.includes(teamId)) {
      onToggle(teamId);
    }
    setQuery("");
    setIsOpen(false);
  }

  return (
    <div ref={rootRef} className={isOpen ? "relative z-50" : "relative"}>
      <button
        type="button"
        disabled={isLocked}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listId}
        aria-label={DROPDOWN_PLACEHOLDER}
        onClick={() => setIsOpen((open) => !open)}
        className={
          `flex w-full cursor-pointer items-center justify-between gap-2 ` +
          `rounded-md text-left text-sm ${INPUT_CLASS_NAME} ` +
          "disabled:cursor-not-allowed disabled:opacity-60"
        }
      >
        <span className={selected ? "text-text" : "text-subtle"}>{label}</span>
        <span className="flex items-center gap-2">
          <PickStatusMark
            teamId={selected?.team_id ?? null}
            resultTeamIds={resultTeamIds}
            isSelected={selected !== null}
          />
          <ChevronIcon isOpen={isOpen} />
        </span>
      </button>
      {isOpen ? (
        <DropdownPanel
          listId={listId}
          candidates={candidates}
          selectedIds={selectedIds}
          query={query}
          teamNameDisplay={teamNameDisplay}
          onQueryChange={setQuery}
          onChoose={chooseTeam}
        />
      ) : null}
    </div>
  );
}

function DropdownPanel({
  listId,
  candidates,
  selectedIds,
  query,
  teamNameDisplay,
  onQueryChange,
  onChoose,
}: {
  listId: string;
  candidates: readonly LongTermTeam[];
  selectedIds: readonly number[];
  query: string;
  teamNameDisplay: TeamNameDisplayPreference;
  onQueryChange: (query: string) => void;
  onChoose: (teamId: number) => void;
}) {
  const visible = filterLongTermCandidates(candidates, query, teamNameDisplay);
  return (
    <div className={DROPDOWN_PANEL_CLASS}>
      <label className="flex flex-col gap-1 px-1 pb-2 text-sm text-muted">
        Szukaj drużyny
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className={`w-full rounded-md ${INPUT_CLASS_NAME}`}
          autoComplete="off"
        />
      </label>
      <CandidateTeamList
        listId={listId}
        teams={visible}
        selectedIds={selectedIds}
        resultTeamIds={[]}
        isLocked={false}
        teamNameDisplay={teamNameDisplay}
        onToggle={onChoose}
      />
    </div>
  );
}

function SelectedTeamChips({
  teams,
  resultTeamIds,
  isLocked,
  teamNameDisplay,
  onToggle,
}: {
  teams: readonly LongTermTeam[];
  resultTeamIds: readonly number[];
  isLocked: boolean;
  teamNameDisplay: TeamNameDisplayPreference;
  onToggle: (teamId: number) => void;
}) {
  if (teams.length === 0) {
    return <p className="text-sm text-muted">Nie wybrano jeszcze drużyn.</p>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {teams.map((team) => (
        <li key={team.team_id}>
          <button
            type="button"
            disabled={isLocked}
            onClick={() => onToggle(team.team_id)}
            className={`${CHIP_BASE} ${chipToneClass(team.team_id, resultTeamIds)} disabled:opacity-70`}
            aria-label={`Usuń ${formatLongTermTeamName(team, teamNameDisplay)}`}
          >
            {formatLongTermTeamName(team, teamNameDisplay)}
            {isLocked ? null : <span aria-hidden="true">×</span>}
          </button>
        </li>
      ))}
    </ul>
  );
}

function CandidateTeamList({
  teams,
  selectedIds,
  resultTeamIds,
  isLocked,
  teamNameDisplay,
  onToggle,
  listId,
}: {
  teams: readonly LongTermTeam[];
  selectedIds: readonly number[];
  resultTeamIds: readonly number[];
  isLocked: boolean;
  teamNameDisplay: TeamNameDisplayPreference;
  onToggle: (teamId: number) => void;
  listId?: string;
}) {
  if (teams.length === 0) {
    return (
      <p className="text-sm text-muted">Brak drużyn dla podanego wyszukiwania.</p>
    );
  }
  return (
    <ul
      id={listId}
      role={listId ? "listbox" : undefined}
      className="max-h-72 space-y-1 overflow-y-auto"
    >
      {teams.map((team) => {
        const isSelected = selectedIds.includes(team.team_id);
        return (
          <li key={team.team_id}>
            <button
              type="button"
              disabled={isLocked}
              role={listId ? "option" : undefined}
              aria-selected={listId ? isSelected : undefined}
              aria-pressed={listId ? undefined : isSelected}
              onClick={() => onToggle(team.team_id)}
              className={`${LIST_BUTTON_BASE} ${
                isSelected
                  ? "border-accent bg-accent-soft text-text"
                  : "border-border bg-surface text-text hover:bg-surface-muted"
              } disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <span>{formatLongTermTeamName(team, teamNameDisplay)}</span>
              <PickStatusMark
                teamId={team.team_id}
                resultTeamIds={resultTeamIds}
                isSelected={isSelected}
              />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function PickStatusMark({
  teamId,
  resultTeamIds,
  isSelected,
}: {
  teamId: number | null;
  resultTeamIds: readonly number[];
  isSelected: boolean;
}) {
  if (!isSelected || teamId === null) {
    return null;
  }
  const status = classifyLongTermPick(teamId, resultTeamIds);
  if (status === "pending") {
    return null;
  }
  return (
    <span className="text-xs text-muted">
      {status === "hit" ? "trafienie" : "pudło"}
    </span>
  );
}

function chipToneClass(
  teamId: number,
  resultTeamIds: readonly number[],
): string {
  const status = classifyLongTermPick(teamId, resultTeamIds);
  if (status === "hit") {
    return "border-success-border bg-success-bg text-success-text";
  }
  if (status === "miss") {
    return "border-danger-border bg-danger-bg text-danger-text";
  }
  return "border-accent bg-accent-soft text-text";
}

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={
        `h-4 w-4 shrink-0 text-subtle transition ${isOpen ? "rotate-180" : ""}`
      }
      aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function usePickerDismiss(
  isOpen: boolean,
  rootRef: RefObject<HTMLDivElement | null>,
  setIsOpen: (open: boolean) => void,
) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (rootRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, rootRef, setIsOpen]);
}
