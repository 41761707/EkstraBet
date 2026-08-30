import { formatMatchDateTime } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import { candidateOddsLabel } from "@/lib/typerLmAdmin";
import type { TyperAdminCandidate } from "@/types/api";

interface TyperLmAdminCandidateRowProps {
  candidate: TyperAdminCandidate;
  isSelected: boolean;
  isSaving: boolean;
  pendingUnpublishId: number | null;
  teamNameDisplay: TeamNameDisplayPreference;
  onToggle: () => void;
  onRequestUnpublish: () => void;
  onConfirmUnpublish: () => void;
  onCancelUnpublish: () => void;
}

export function TyperLmAdminCandidateRow({
  candidate,
  isSelected,
  isSaving,
  pendingUnpublishId,
  teamNameDisplay,
  onToggle,
  onRequestUnpublish,
  onConfirmUnpublish,
  onCancelUnpublish,
}: TyperLmAdminCandidateRowProps) {
  const homeName = formatTeamName(
    candidate.home_team.name,
    candidate.home_team.shortcut,
    teamNameDisplay,
  );
  const awayName = formatTeamName(
    candidate.away_team.name,
    candidate.away_team.shortcut,
    teamNameDisplay,
  );
  const isPendingUnpublish = pendingUnpublishId === candidate.match_id;

  return (
    <li className="space-y-2 rounded-lg border border-border bg-surface-muted px-3 py-3">
      <label className="flex cursor-pointer items-start gap-3 text-sm text-text">
        <input
          type="checkbox"
          checked={isSelected}
          disabled={candidate.is_published || isSaving}
          onChange={onToggle}
          className="mt-1 rounded border-border bg-surface"
        />
        <span className="min-w-0 flex-1">
          <span className="block font-medium">
            {homeName} — {awayName}
          </span>
          <time
            className="block text-xs text-muted"
            dateTime={candidate.game_date}
          >
            {formatMatchDateTime(candidate.game_date)}
          </time>
          <span className="mt-1 block text-xs text-muted">
            {candidateOddsLabel(candidate)}
          </span>
          {candidate.is_published ? (
            <span className="mt-1 block text-xs font-medium text-accent-text">
              Opublikowany
            </span>
          ) : null}
        </span>
      </label>
      {candidate.is_published ? (
        <UnpublishControls
          isSaving={isSaving}
          isPending={isPendingUnpublish}
          onRequest={onRequestUnpublish}
          onConfirm={onConfirmUnpublish}
          onCancel={onCancelUnpublish}
        />
      ) : null}
    </li>
  );
}

interface UnpublishControlsProps {
  isSaving: boolean;
  isPending: boolean;
  onRequest: () => void;
  onConfirm: () => void;
  onCancel: () => void;
}

function UnpublishControls({
  isSaving,
  isPending,
  onRequest,
  onConfirm,
  onCancel,
}: UnpublishControlsProps) {
  if (!isPending) {
    return (
      <button
        type="button"
        disabled={isSaving}
        onClick={onRequest}
        className="text-sm text-danger-text hover:underline disabled:opacity-50"
      >
        Wycofaj publikację
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted">
        Wycofać, jeśli nikt jeszcze nie typował?
      </span>
      <button
        type="button"
        disabled={isSaving}
        onClick={onConfirm}
        className={
          "rounded-md border border-danger-border bg-danger-bg px-2 py-1 " +
          "text-danger-text disabled:opacity-50"
        }
      >
        Potwierdź wycofanie
      </button>
      <button
        type="button"
        disabled={isSaving}
        onClick={onCancel}
        className="text-muted hover:text-text disabled:opacity-50"
      >
        Anuluj
      </button>
    </div>
  );
}
