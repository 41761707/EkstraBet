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
  query: string;
  isLocked: boolean;
  resultTeamIds: readonly number[];
  teamNameDisplay: TeamNameDisplayPreference;
  onQueryChange: (query: string) => void;
  onToggle: (teamId: number) => void;
}

const CHIP_BASE =
  "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs";
const LIST_BUTTON_BASE =
  "flex w-full items-center justify-between rounded-lg border px-3 py-2 " +
  "text-left text-sm transition";

export function TyperLmLongTermTeamPicker({
  candidates,
  selectedIds,
  selectionSize,
  query,
  isLocked,
  resultTeamIds,
  teamNameDisplay,
  onQueryChange,
  onToggle,
}: TyperLmLongTermTeamPickerProps) {
  const visible = filterLongTermCandidates(candidates, query, teamNameDisplay);
  const chips = selectedTeams(candidates, selectedIds);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-text">
          Wybrane {formatLongTermSelectionCounter(selectedIds.length, selectionSize)}
        </p>
      </div>
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
          onChange={(event) => onQueryChange(event.target.value)}
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
}: {
  teams: readonly LongTermTeam[];
  selectedIds: readonly number[];
  resultTeamIds: readonly number[];
  isLocked: boolean;
  teamNameDisplay: TeamNameDisplayPreference;
  onToggle: (teamId: number) => void;
}) {
  if (teams.length === 0) {
    return (
      <p className="text-sm text-muted">Brak drużyn dla podanego wyszukiwania.</p>
    );
  }
  return (
    <ul className="max-h-72 space-y-1 overflow-y-auto">
      {teams.map((team) => {
        const isSelected = selectedIds.includes(team.team_id);
        return (
          <li key={team.team_id}>
            <button
              type="button"
              disabled={isLocked}
              aria-pressed={isSelected}
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
  teamId: number;
  resultTeamIds: readonly number[];
  isSelected: boolean;
}) {
  if (!isSelected) {
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
