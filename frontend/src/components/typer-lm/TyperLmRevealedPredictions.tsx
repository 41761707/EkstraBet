"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { getTyperRevealedPredictions } from "@/lib/apiClient";
import { formatMatchDateTime } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { revealedPredictionsLoadErrorMessage } from "@/lib/typerLmRevealed";
import type {
  TyperRevealedPredictionsResponse,
  TyperRound,
} from "@/types/api";

import { TyperLmRevealedPredictionsTable } from "./TyperLmRevealedPredictionsTable";
import { TyperLmRoundPicker } from "./TyperLmRoundPicker";

export const REVEALED_POLL_INTERVAL_MS = 60_000;

interface TyperLmRevealedPredictionsProps {
  seasonId: number;
  rounds: TyperRound[];
  selectedRound: number | null;
  currentUserUuid: string;
  teamNameDisplay: TeamNameDisplayPreference;
  onSelectRound: (roundNumber: number) => void;
}

export function TyperLmRevealedPredictions({
  seasonId,
  rounds,
  selectedRound,
  currentUserUuid,
  teamNameDisplay,
  onSelectRound,
}: TyperLmRevealedPredictionsProps) {
  const loadState = useRevealedPredictions(seasonId, selectedRound);
  const publishedMatchCount =
    rounds.find((round) => round.round_number === selectedRound)?.matches.length ?? 0;

  return (
    <TyperLmRevealedPredictionsPanel
      rounds={rounds}
      selectedRound={selectedRound}
      publishedMatchCount={publishedMatchCount}
      data={loadState.data}
      isLoading={loadState.isLoading}
      isRefreshing={loadState.isRefreshing}
      errorMessage={loadState.errorMessage}
      lastLoadedAt={loadState.lastLoadedAt}
      currentUserUuid={currentUserUuid}
      teamNameDisplay={teamNameDisplay}
      onSelectRound={onSelectRound}
      onRefresh={loadState.refresh}
    />
  );
}

export interface TyperLmRevealedPredictionsPanelProps {
  rounds: TyperRound[];
  selectedRound: number | null;
  publishedMatchCount: number;
  data: TyperRevealedPredictionsResponse | null;
  isLoading: boolean;
  isRefreshing: boolean;
  errorMessage: string | null;
  lastLoadedAt: number | null;
  currentUserUuid: string;
  teamNameDisplay: TeamNameDisplayPreference;
  onSelectRound: (roundNumber: number) => void;
  onRefresh: () => void;
}

export function TyperLmRevealedPredictionsPanel({
  rounds,
  selectedRound,
  publishedMatchCount,
  data,
  isLoading,
  isRefreshing,
  errorMessage,
  lastLoadedAt,
  currentUserUuid,
  teamNameDisplay,
  onSelectRound,
  onRefresh,
}: TyperLmRevealedPredictionsPanelProps) {
  if (rounds.length === 0) {
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
        rounds={rounds}
        selectedRound={selectedRound}
        onSelect={onSelectRound}
      />
      <RevealedToolbar
        startedMatchCount={data?.matches.length ?? 0}
        publishedMatchCount={publishedMatchCount}
        isBusy={isLoading || isRefreshing}
        onRefresh={onRefresh}
      />
      <RevealedBody
        data={data}
        isLoading={isLoading}
        errorMessage={errorMessage}
        lastLoadedAt={lastLoadedAt}
        currentUserUuid={currentUserUuid}
        teamNameDisplay={teamNameDisplay}
        onRefresh={onRefresh}
      />
    </div>
  );
}

function RevealedToolbar({
  startedMatchCount,
  publishedMatchCount,
  isBusy,
  onRefresh,
}: {
  startedMatchCount: number;
  publishedMatchCount: number;
  isBusy: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="space-y-1">
        <p className="text-sm text-muted">Widoczne po rozpoczęciu meczu</p>
        <p className="text-sm text-text">
          Rozpoczęte mecze: {startedMatchCount} / {publishedMatchCount}
        </p>
      </div>
      <button
        type="button"
        disabled={isBusy}
        onClick={onRefresh}
        className={
          "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
          "text-on-accent disabled:opacity-50"
        }
      >
        Odśwież
      </button>
    </div>
  );
}

function RevealedBody({
  data,
  isLoading,
  errorMessage,
  lastLoadedAt,
  currentUserUuid,
  teamNameDisplay,
  onRefresh,
}: {
  data: TyperRevealedPredictionsResponse | null;
  isLoading: boolean;
  errorMessage: string | null;
  lastLoadedAt: number | null;
  currentUserUuid: string;
  teamNameDisplay: TeamNameDisplayPreference;
  onRefresh: () => void;
}) {
  return (
    <div className="space-y-4">
      {errorMessage ? (
        <RevealedError
          errorMessage={errorMessage}
          lastLoadedAt={data === null ? null : lastLoadedAt}
          showRetry={data === null}
          onRefresh={onRefresh}
        />
      ) : null}
      {isLoading && data === null ? (
        <StatusMessage variant="info" title="Ładowanie typów uczestników" />
      ) : null}
      {data !== null && data.matches.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak rozpoczętych meczów"
          message={
            "Typy uczestników pojawią się po kickoffie wybranego spotkania."
          }
        />
      ) : null}
      {data !== null && data.matches.length > 0 ? (
        <TyperLmRevealedPredictionsTable
          matches={data.matches}
          participants={data.participants}
          currentUserUuid={currentUserUuid}
          teamNameDisplay={teamNameDisplay}
        />
      ) : null}
    </div>
  );
}

function RevealedError({
  errorMessage,
  lastLoadedAt,
  showRetry,
  onRefresh,
}: {
  errorMessage: string;
  lastLoadedAt: number | null;
  showRetry: boolean;
  onRefresh: () => void;
}) {
  const lastLoadedLabel =
    lastLoadedAt === null
      ? null
      : `Ostatnia aktualizacja: ${formatMatchDateTime(
          new Date(lastLoadedAt).toISOString(),
        )}`;
  return (
    <div className="space-y-3">
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać typów uczestników"
        message={
          lastLoadedLabel === null
            ? errorMessage
            : `${errorMessage} ${lastLoadedLabel}`
        }
      />
      {showRetry ? (
        <button
          type="button"
          onClick={onRefresh}
          className={
            "rounded-lg bg-accent px-3 py-2 text-sm font-medium text-on-accent"
          }
        >
          Spróbuj ponownie
        </button>
      ) : null}
    </div>
  );
}

interface RevealedLoadSetters {
  setData: (value: TyperRevealedPredictionsResponse | null) => void;
  setErrorMessage: (value: string | null) => void;
  setIsLoading: (value: boolean) => void;
  setIsRefreshing: (value: boolean) => void;
  setLastLoadedAt: (value: number | null) => void;
}

async function loadRevealedPredictions(
  seasonId: number,
  roundNumber: number,
  mode: "replace" | "refresh",
  setters: RevealedLoadSetters,
  generationRef: { current: number },
  inFlightRef: { current: boolean },
): Promise<void> {
  if (mode === "refresh" && inFlightRef.current) {
    return;
  }
  const requestId = ++generationRef.current;
  inFlightRef.current = true;
  if (mode === "replace") {
    setters.setIsLoading(true);
    setters.setData(null);
    setters.setErrorMessage(null);
    // timestamp należy do poprzedniej rundy — nie pokazuj go przy pustym stanie
    setters.setLastLoadedAt(null);
  } else {
    setters.setIsRefreshing(true);
  }
  try {
    const payload = await getTyperRevealedPredictions(seasonId, roundNumber);
    if (requestId !== generationRef.current) {
      return;
    }
    setters.setData(payload);
    setters.setErrorMessage(null);
    setters.setLastLoadedAt(Date.now());
  } catch (error) {
    if (requestId !== generationRef.current) {
      return;
    }
    setters.setErrorMessage(revealedPredictionsLoadErrorMessage(error));
  } finally {
    if (requestId !== generationRef.current) {
      return;
    }
    inFlightRef.current = false;
    setters.setIsLoading(false);
    setters.setIsRefreshing(false);
  }
}

function useRevealedPredictions(
  seasonId: number,
  roundNumber: number | null,
) {
  const [data, setData] = useState<TyperRevealedPredictionsResponse | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(roundNumber !== null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState<number | null>(null);
  const generationRef = useRef(0);
  const inFlightRef = useRef(false);
  const settersRef = useRef<RevealedLoadSetters | null>(null);
  settersRef.current = {
    setData,
    setErrorMessage,
    setIsLoading,
    setIsRefreshing,
    setLastLoadedAt,
  };
  const paramsRef = useRef({ seasonId, roundNumber });
  paramsRef.current = { seasonId, roundNumber };
  const dataRef = useRef(data);
  dataRef.current = data;

  const refresh = useCallback(() => {
    const params = paramsRef.current;
    const setters = settersRef.current;
    if (params.roundNumber === null || setters === null) {
      return;
    }
    // bez danych retry ma pokazać loading, a nie zostawić sam komunikat błędu
    const mode = dataRef.current === null ? "replace" : "refresh";
    void loadRevealedPredictions(
      params.seasonId,
      params.roundNumber,
      mode,
      setters,
      generationRef,
      inFlightRef,
    );
  }, []);

  useEffect(() => {
    if (roundNumber === null) {
      setData(null);
      setErrorMessage(null);
      setIsLoading(false);
      return;
    }
    const setters = settersRef.current;
    if (setters === null) {
      return;
    }
    void loadRevealedPredictions(
      seasonId,
      roundNumber,
      "replace",
      setters,
      generationRef,
      inFlightRef,
    );
    return () => {
      generationRef.current += 1;
    };
  }, [seasonId, roundNumber]);

  useEffect(() => {
    if (roundNumber === null) {
      return;
    }
    const timer = window.setInterval(refresh, REVEALED_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [roundNumber, refresh]);

  return { data, errorMessage, isLoading, isRefreshing, lastLoadedAt, refresh };
}
