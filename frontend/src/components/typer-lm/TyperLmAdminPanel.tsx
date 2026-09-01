"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { GROUP_STAGE_MATCH_COUNT } from "@/lib/typerLmAdmin";
import type {
  LeagueRound,
  LongTermAutoResultResponse,
  LongTermMarketCard,
  TyperAdminCandidate,
} from "@/types/api";

import { TyperLmAdminAuditLookup } from "./TyperLmAdminAuditLookup";
import { TyperLmAdminCandidateList } from "./TyperLmAdminCandidateList";
import { TyperLmAdminRoundControls } from "./TyperLmAdminRoundControls";
import { TyperLmLongTermAdminPanel } from "./TyperLmLongTermAdminPanel";
import { useTyperLmAdminPublications } from "./useTyperLmAdminPublications";

interface TyperLmAdminPanelProps {
  seasonId: number;
  initialRoundNumber?: number;
  initialCandidates?: TyperAdminCandidate[] | null;
  initialGroupMatchCount?: number;
  knockoutRounds?: readonly LeagueRound[];
  knockoutRoundsError?: string;
  longTermMarkets?: readonly LongTermMarketCard[];
  longTermAutoResults?: Record<number, LongTermAutoResultResponse | null>;
}

export function TyperLmAdminPanel({
  seasonId,
  initialRoundNumber = 1,
  initialCandidates = null,
  initialGroupMatchCount = GROUP_STAGE_MATCH_COUNT,
  knockoutRounds = [],
  knockoutRoundsError,
  longTermMarkets = [],
  longTermAutoResults = {},
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
      <TyperLmLongTermAdminBlocks
        markets={longTermMarkets}
        autoResults={longTermAutoResults}
        teamNameDisplay={preferences.teamNameDisplay}
      />
    </section>
  );
}

function TyperLmLongTermAdminBlocks({
  markets,
  autoResults,
  teamNameDisplay,
}: {
  markets: readonly LongTermMarketCard[];
  autoResults: Record<number, LongTermAutoResultResponse | null>;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  if (markets.length === 0) {
    return null;
  }
  return (
    <>
      {markets.map((market) => (
        <TyperLmLongTermAdminPanel
          key={market.market_id}
          market={market}
          initialAutoResult={autoResults[market.market_id] ?? null}
          teamNameDisplay={teamNameDisplay}
        />
      ))}
    </>
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
  longTermMarkets?: readonly LongTermMarketCard[];
  longTermAutoResults?: Record<number, LongTermAutoResultResponse | null>;
}

export function TyperLmAdminSection({
  isAdmin,
  seasonId,
  initialRoundNumber,
  initialCandidates,
  initialGroupMatchCount,
  knockoutRounds,
  knockoutRoundsError,
  longTermMarkets,
  longTermAutoResults,
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
      longTermMarkets={longTermMarkets}
      longTermAutoResults={longTermAutoResults}
    />
  );
}
