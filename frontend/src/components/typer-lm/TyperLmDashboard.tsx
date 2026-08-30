"use client";

import { useEffect, useRef, useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { ApiError, saveTyperPrediction } from "@/lib/apiClient";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  addPendingMatchId,
  applySavedPrediction,
  canSaveTyperOutcome,
  isTyperMatchLockedForUi,
  lockTyperMatch,
  removePendingMatchId,
  selectInitialRoundNumber,
  TYPER_LOCK_TICK_MS,
  typerSaveErrorMessage,
  updateDashboardMatch,
} from "@/lib/typerLm";
import type {
  TyperDashboardResponse,
  TyperLeaderboardRow,
  TyperMatch,
  TyperOutcome,
} from "@/types/api";

import { TyperLmLeaderboard } from "./TyperLmLeaderboard";
import { TyperLmMatchCard } from "./TyperLmMatchCard";
import { TyperLmRoundPicker } from "./TyperLmRoundPicker";
import { TyperLmViewTabs, type TyperLmTab } from "./TyperLmViewTabs";

interface TyperLmDashboardProps {
  dashboard: TyperDashboardResponse;
  leaderboard: TyperLeaderboardRow[];
  leaderboardError?: string;
  currentUserUuid: string;
  currentUserDisplayName: string;
}

function useNowMs(intervalMs: number = TYPER_LOCK_TICK_MS): number | null {
  const [nowMs, setNowMs] = useState<number | null>(null);

  useEffect(() => {
    setNowMs(Date.now());
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);

  return nowMs;
}

export function TyperLmDashboard({
  dashboard: initialDashboard,
  leaderboard,
  leaderboardError,
  currentUserUuid,
  currentUserDisplayName,
}: TyperLmDashboardProps) {
  const [tab, setTab] = useState<TyperLmTab>("round");
  const nowMs = useNowMs();
  const { preferences } = usePreferences();
  const predictions = useTyperPredictions(
    initialDashboard,
    {
      uuid: currentUserUuid,
      displayName: currentUserDisplayName,
    },
    nowMs,
  );
  const selectedRound = predictions.dashboard.rounds.find(
    (round) => round.round_number === predictions.selectedRound,
  );

  return (
    <div className="space-y-6">
      <TyperLmViewTabs activeTab={tab} onChange={setTab} />
      {tab === "ranking" ? (
        leaderboardError ? (
          <StatusMessage
            variant="error"
            title="Nie udało się załadować rankingu"
            message={leaderboardError}
          />
        ) : (
          <TyperLmLeaderboard
            rows={leaderboard}
            currentUserUuid={currentUserUuid}
          />
        )
      ) : (
        <RoundPanel
          dashboard={predictions.dashboard}
          selectedRound={predictions.selectedRound}
          selectedMatches={selectedRound?.matches ?? []}
          pendingMatchIds={predictions.pendingMatchIds}
          nowMs={nowMs}
          errors={predictions.errors}
          teamNameDisplay={preferences.teamNameDisplay}
          onSelectRound={predictions.setSelectedRound}
          onSelectOutcome={predictions.saveOutcome}
        />
      )}
    </div>
  );
}

interface RoundPanelProps {
  dashboard: TyperDashboardResponse;
  selectedRound: number | null;
  selectedMatches: TyperMatch[];
  pendingMatchIds: ReadonlySet<number>;
  nowMs: number | null;
  errors: Partial<Record<number, string>>;
  teamNameDisplay: TeamNameDisplayPreference;
  onSelectRound: (roundNumber: number) => void;
  onSelectOutcome: (match: TyperMatch, outcome: TyperOutcome) => void;
}

function RoundPanel({
  dashboard,
  selectedRound,
  selectedMatches,
  pendingMatchIds,
  nowMs,
  errors,
  teamNameDisplay,
  onSelectRound,
  onSelectOutcome,
}: RoundPanelProps) {
  if (dashboard.rounds.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak opublikowanych meczów"
        message="Administrator nie opublikował jeszcze zestawu do typowania."
      />
    );
  }

  return (
    <div className="space-y-4">
      <TyperLmRoundPicker
        rounds={dashboard.rounds}
        selectedRound={selectedRound}
        onSelect={onSelectRound}
      />
      {selectedMatches.map((match) => (
        <TyperLmMatchCard
          key={match.match_id}
          match={match}
          teamNameDisplay={teamNameDisplay}
          isPending={pendingMatchIds.has(match.match_id)}
          nowMs={nowMs}
          errorMessage={errors[match.match_id]}
          onSelectOutcome={(outcome) => onSelectOutcome(match, outcome)}
        />
      ))}
    </div>
  );
}

function useTyperPredictions(
  initialDashboard: TyperDashboardResponse,
  actor: { uuid: string; displayName: string },
  nowMs: number | null,
) {
  const [dashboard, setDashboard] = useState(initialDashboard);
  const [selectedRound, setSelectedRound] = useState(() =>
    selectInitialRoundNumber(initialDashboard.rounds),
  );
  const [pendingMatchIds, setPendingMatchIds] = useState<Set<number>>(
    () => new Set(),
  );
  const pendingMatchIdsRef = useRef<Set<number>>(new Set());
  const [errors, setErrors] = useState<Partial<Record<number, string>>>({});

  async function saveOutcome(match: TyperMatch, outcome: TyperOutcome) {
    const isPending = pendingMatchIdsRef.current.has(match.match_id);
    if (!canSaveTyperOutcome(match, outcome, isPending, nowMs)) {
      if (isTyperMatchLockedForUi(match, nowMs)) {
        setDashboard((current) =>
          updateDashboardMatch(current, match.match_id, lockTyperMatch),
        );
      }
      return;
    }
    pendingMatchIdsRef.current = addPendingMatchId(
      pendingMatchIdsRef.current,
      match.match_id,
    );
    setPendingMatchIds(pendingMatchIdsRef.current);
    setErrors((current) => {
      const next = { ...current };
      delete next[match.match_id];
      return next;
    });
    try {
      const saved = await saveTyperPrediction(match.match_id, outcome);
      setDashboard((current) =>
        updateDashboardMatch(current, match.match_id, (row) =>
          applySavedPrediction(row, saved, actor),
        ),
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setDashboard((current) =>
          updateDashboardMatch(current, match.match_id, lockTyperMatch),
        );
      }
      setErrors((current) => ({
        ...current,
        [match.match_id]: typerSaveErrorMessage(error),
      }));
    } finally {
      pendingMatchIdsRef.current = removePendingMatchId(
        pendingMatchIdsRef.current,
        match.match_id,
      );
      setPendingMatchIds(pendingMatchIdsRef.current);
    }
  }

  return {
    dashboard,
    selectedRound,
    setSelectedRound,
    pendingMatchIds,
    errors,
    saveOutcome,
  };
}
