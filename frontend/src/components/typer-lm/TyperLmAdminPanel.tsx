"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { GROUP_STAGE_MATCH_COUNT } from "@/lib/typerLmAdmin";
import type { LeagueRound, TyperAdminCandidate } from "@/types/api";

import { TyperLmAdminAuditLookup } from "./TyperLmAdminAuditLookup";
import { TyperLmAdminCandidateList } from "./TyperLmAdminCandidateList";
import { TyperLmAdminRoundControls } from "./TyperLmAdminRoundControls";
import { useTyperLmAdminPublications } from "./useTyperLmAdminPublications";

interface TyperLmAdminPanelProps {
  seasonId: number;
  initialRoundNumber?: number;
  initialCandidates?: TyperAdminCandidate[] | null;
  initialGroupMatchCount?: number;
  knockoutRounds?: readonly LeagueRound[];
  knockoutRoundsError?: string;
}

export function TyperLmAdminPanel({
  seasonId,
  initialRoundNumber = 1,
  initialCandidates = null,
  initialGroupMatchCount = GROUP_STAGE_MATCH_COUNT,
  knockoutRounds = [],
  knockoutRoundsError,
}: TyperLmAdminPanelProps) {
  const { preferences } = usePreferences();
  const publications = useTyperLmAdminPublications({
    seasonId,
    initialRoundNumber,
    initialCandidates,
    initialGroupMatchCount,
  });
  const [pendingUnpublishId, setPendingUnpublishId] = useState<number | null>(
    null,
  );

  return (
    <section className="space-y-6 rounded-xl border border-border bg-surface p-4">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-text">Panel administratora</h2>
        <p className="text-sm text-muted">
          Publikuj zestaw meczów nawet bez kursów Superbet. Kursy są tylko
          informacją i dopiszą się później z tabeli odds.
        </p>
      </header>
      <TyperLmAdminRoundControls
        selectedRound={publications.roundNumber}
        knockoutRounds={knockoutRounds}
        knockoutRoundsError={knockoutRoundsError}
        isSaving={publications.isSaving}
        onSelectRound={publications.selectRound}
      />
      {publications.errorMessage ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wykonać operacji"
          message={publications.errorMessage}
        />
      ) : null}
      <TyperLmAdminCandidateList
        roundNumber={publications.roundNumber}
        candidates={publications.candidates}
        selectedIds={publications.selectedIds}
        groupMatchCount={publications.groupMatchCount}
        isLoading={publications.isLoading}
        isSaving={publications.isSaving}
        errorMessage={publications.errorMessage}
        canPublish={publications.canPublish}
        isConfirmingPublish={publications.isConfirmingPublish}
        pendingUnpublishId={pendingUnpublishId}
        teamNameDisplay={preferences.teamNameDisplay}
        onToggle={publications.toggleCandidate}
        onRequestPublish={() => publications.setIsConfirmingPublish(true)}
        onConfirmPublish={publications.confirmPublish}
        onCancelPublish={() => publications.setIsConfirmingPublish(false)}
        onRequestUnpublish={setPendingUnpublishId}
        onConfirmUnpublish={(matchId) => {
          setPendingUnpublishId(null);
          void publications.unpublishMatch(matchId);
        }}
        onCancelUnpublish={() => setPendingUnpublishId(null)}
      />
      <TyperLmAdminAuditLookup seasonId={seasonId} />
    </section>
  );
}

interface TyperLmAdminSectionProps {
  isAdmin: boolean;
  seasonId: number;
  initialRoundNumber?: number;
  initialCandidates?: TyperAdminCandidate[] | null;
  initialGroupMatchCount?: number;
  knockoutRounds?: readonly LeagueRound[];
  knockoutRoundsError?: string;
}

export function TyperLmAdminSection({
  isAdmin,
  seasonId,
  initialRoundNumber,
  initialCandidates,
  initialGroupMatchCount,
  knockoutRounds,
  knockoutRoundsError,
}: TyperLmAdminSectionProps) {
  if (!isAdmin) {
    return null;
  }
  return (
    <TyperLmAdminPanel
      seasonId={seasonId}
      initialRoundNumber={initialRoundNumber}
      initialCandidates={initialCandidates}
      initialGroupMatchCount={initialGroupMatchCount}
      knockoutRounds={knockoutRounds}
      knockoutRoundsError={knockoutRoundsError}
    />
  );
}
