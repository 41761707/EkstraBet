import { StatusMessage } from "@/components/StatusMessage";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { publicationCounterLabel } from "@/lib/typerLmAdmin";
import type { TyperAdminCandidate } from "@/types/api";

import { TyperLmAdminCandidateRow } from "./TyperLmAdminCandidateRow";

interface TyperLmAdminCandidateListProps {
  roundNumber: number;
  candidates: TyperAdminCandidate[];
  selectedIds: readonly number[];
  isLoading: boolean;
  isSaving: boolean;
  errorMessage?: string | null;
  canPublish: boolean;
  isConfirmingPublish: boolean;
  pendingUnpublishId: number | null;
  groupMatchCount?: number;
  teamNameDisplay: TeamNameDisplayPreference;
  onToggle: (candidate: TyperAdminCandidate) => void;
  onRequestPublish: () => void;
  onConfirmPublish: () => void;
  onCancelPublish: () => void;
  onRequestUnpublish: (matchId: number) => void;
  onConfirmUnpublish: (matchId: number) => void;
  onCancelUnpublish: () => void;
}

export function TyperLmAdminCandidateList({
  roundNumber,
  candidates,
  selectedIds,
  isLoading,
  isSaving,
  errorMessage,
  canPublish,
  isConfirmingPublish,
  pendingUnpublishId,
  groupMatchCount,
  teamNameDisplay,
  onToggle,
  onRequestPublish,
  onConfirmPublish,
  onCancelPublish,
  onRequestUnpublish,
  onConfirmUnpublish,
  onCancelUnpublish,
}: TyperLmAdminCandidateListProps) {
  const selectedSet = new Set(selectedIds);
  const counter = publicationCounterLabel(
    candidates,
    selectedIds,
    roundNumber,
    groupMatchCount,
  );

  if (isLoading) {
    return (
      <StatusMessage variant="info" title="Ładowanie kandydatów rundy" />
    );
  }

  if (candidates.length === 0) {
    if (errorMessage) {
      return null;
    }
    return (
      <StatusMessage
        variant="empty"
        title="Brak meczów w tej rundzie"
        message={
          "Wybierz inną kolejkę albo rundę pucharową z zaimportowanym " +
          "terminarzem."
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Wybrano do publikacji:{" "}
        <span className="font-medium text-text">{counter}</span>
      </p>
      <ul className="space-y-2">
        {candidates.map((candidate) => (
          <TyperLmAdminCandidateRow
            key={candidate.match_id}
            candidate={candidate}
            isSelected={selectedSet.has(candidate.match_id)}
            isSaving={isSaving}
            pendingUnpublishId={pendingUnpublishId}
            teamNameDisplay={teamNameDisplay}
            onToggle={() => onToggle(candidate)}
            onRequestUnpublish={() => onRequestUnpublish(candidate.match_id)}
            onConfirmUnpublish={() => onConfirmUnpublish(candidate.match_id)}
            onCancelUnpublish={onCancelUnpublish}
          />
        ))}
      </ul>
      <PublishControls
        selectedCount={selectedIds.length}
        canPublish={canPublish}
        isSaving={isSaving}
        isConfirming={isConfirmingPublish}
        onRequest={onRequestPublish}
        onConfirm={onConfirmPublish}
        onCancel={onCancelPublish}
      />
    </div>
  );
}

interface PublishControlsProps {
  selectedCount: number;
  canPublish: boolean;
  isSaving: boolean;
  isConfirming: boolean;
  onRequest: () => void;
  onConfirm: () => void;
  onCancel: () => void;
}

function PublishControls({
  selectedCount,
  canPublish,
  isSaving,
  isConfirming,
  onRequest,
  onConfirm,
  onCancel,
}: PublishControlsProps) {
  if (isConfirming) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-text">
          Opublikować atomowo {selectedCount} meczów? Brak kursów nie blokuje
          zapisu.
        </p>
        <button
          type="button"
          disabled={isSaving}
          onClick={onConfirm}
          className={
            "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
            "text-on-accent disabled:opacity-50"
          }
        >
          Potwierdź publikację
        </button>
        <button
          type="button"
          disabled={isSaving}
          onClick={onCancel}
          className="text-sm text-muted hover:text-text disabled:opacity-50"
        >
          Anuluj
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      disabled={!canPublish || isSaving}
      onClick={onRequest}
      className={
        "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
        "text-on-accent disabled:opacity-50"
      }
    >
      Opublikuj zestaw
    </button>
  );
}
