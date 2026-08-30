"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  deleteTyperPublication,
  getTyperAdminCandidates,
  publishTyperMatches,
} from "@/lib/apiClient";
import {
  adminCandidateLoadErrorMessage,
  canPublishSelection,
  defaultSelectedMatchIds,
  GROUP_STAGE_MATCH_COUNT,
  resolveGroupMatchCount,
  shouldApplyAdminLoad,
  toggleSelectedMatchId,
  tryBeginAdminMutation,
  typerAdminPublicationErrorMessage,
} from "@/lib/typerLmAdmin";
import type { TyperAdminCandidate } from "@/types/api";

interface UseTyperLmAdminPublicationsOptions {
  seasonId: number;
  initialRoundNumber: number;
  initialCandidates: TyperAdminCandidate[] | null;
  initialGroupMatchCount?: number;
}

interface CandidateLoaders {
  seasonId: number;
  setCandidates: (rows: TyperAdminCandidate[]) => void;
  setSelectedIds: (ids: number[]) => void;
  setErrorMessage: (message: string | null) => void;
  setIsLoading: (value: boolean) => void;
  setIsConfirmingPublish: (value: boolean) => void;
  setGroupMatchCount: (count: number) => void;
}

async function loadRoundCandidates(
  loaders: CandidateLoaders,
  nextRound: number,
  requestId: number,
  generationRef: { current: number },
): Promise<void> {
  loaders.setIsLoading(true);
  loaders.setErrorMessage(null);
  loaders.setIsConfirmingPublish(false);
  try {
    const payload = await getTyperAdminCandidates(loaders.seasonId, nextRound);
    if (!shouldApplyAdminLoad(requestId, generationRef.current)) {
      return;
    }
    loaders.setCandidates(payload.candidates);
    loaders.setSelectedIds(
      defaultSelectedMatchIds(payload.candidates, nextRound),
    );
    loaders.setGroupMatchCount(
      resolveGroupMatchCount(payload.group_match_count),
    );
  } catch (error) {
    if (!shouldApplyAdminLoad(requestId, generationRef.current)) {
      return;
    }
    loaders.setCandidates([]);
    loaders.setSelectedIds([]);
    loaders.setErrorMessage(adminCandidateLoadErrorMessage(error));
  } finally {
    if (shouldApplyAdminLoad(requestId, generationRef.current)) {
      loaders.setIsLoading(false);
    }
  }
}

async function runAdminMutation(
  inFlightRef: { current: boolean },
  setIsSaving: (value: boolean) => void,
  setErrorMessage: (message: string | null) => void,
  groupMatchCount: number,
  action: () => Promise<void>,
): Promise<void> {
  if (!tryBeginAdminMutation(inFlightRef)) {
    return;
  }
  setIsSaving(true);
  setErrorMessage(null);
  try {
    await action();
  } catch (error) {
    setErrorMessage(
      typerAdminPublicationErrorMessage(error, groupMatchCount),
    );
  } finally {
    inFlightRef.current = false;
    setIsSaving(false);
  }
}

function useStartCandidateLoad(
  seasonId: number,
  setters: Omit<CandidateLoaders, "seasonId">,
): (nextRound: number) => void {
  const generationRef = useRef(0);
  const loadersRef = useRef<CandidateLoaders | null>(null);
  loadersRef.current = { seasonId, ...setters };
  return useCallback((nextRound: number) => {
    const requestId = ++generationRef.current;
    const loaders = loadersRef.current;
    if (loaders === null) {
      return;
    }
    void loadRoundCandidates(loaders, nextRound, requestId, generationRef);
    // seasonId i settery bierzemy z refa, żeby nie restartować effectu
  }, []);
}

export function useTyperLmAdminPublications({
  seasonId,
  initialRoundNumber,
  initialCandidates,
  initialGroupMatchCount = GROUP_STAGE_MATCH_COUNT,
}: UseTyperLmAdminPublicationsOptions) {
  const router = useRouter();
  const [roundNumber, setRoundNumber] = useState(initialRoundNumber);
  const [candidates, setCandidates] = useState<TyperAdminCandidate[]>(
    initialCandidates ?? [],
  );
  const [selectedIds, setSelectedIds] = useState<number[]>(() =>
    defaultSelectedMatchIds(initialCandidates ?? [], initialRoundNumber),
  );
  const [groupMatchCount, setGroupMatchCount] = useState(
    resolveGroupMatchCount(initialGroupMatchCount),
  );
  const [isLoading, setIsLoading] = useState(initialCandidates === null);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isConfirmingPublish, setIsConfirmingPublish] = useState(false);
  const skipFirstFetch = useRef(initialCandidates !== null);
  const inFlightRef = useRef(false);
  const startLoad = useStartCandidateLoad(seasonId, {
    setCandidates,
    setSelectedIds,
    setErrorMessage,
    setIsLoading,
    setIsConfirmingPublish,
    setGroupMatchCount,
  });
  const mutations = buildAdminMutations({
    seasonId,
    roundNumber,
    selectedIds,
    groupMatchCount,
    candidates,
    inFlightRef,
    startLoad,
    setIsSaving,
    setErrorMessage,
    setIsConfirmingPublish,
    setSelectedIds,
    router,
  });

  function selectRound(nextRound: number) {
    if (inFlightRef.current) {
      return;
    }
    setRoundNumber(nextRound);
  }

  useEffect(() => {
    if (skipFirstFetch.current) {
      skipFirstFetch.current = false;
      return;
    }
    startLoad(roundNumber);
  }, [roundNumber, seasonId, startLoad]);

  return {
    roundNumber,
    candidates,
    selectedIds,
    groupMatchCount,
    isLoading,
    isSaving,
    errorMessage,
    isConfirmingPublish,
    canPublish: canPublishSelection(
      candidates,
      selectedIds,
      roundNumber,
      groupMatchCount,
    ),
    selectRound,
    toggleCandidate: mutations.toggleCandidate,
    setIsConfirmingPublish,
    confirmPublish: mutations.confirmPublish,
    unpublishMatch: mutations.unpublishMatch,
  };
}

interface AdminMutationOptions {
  seasonId: number;
  roundNumber: number;
  selectedIds: number[];
  groupMatchCount: number;
  candidates: TyperAdminCandidate[];
  inFlightRef: { current: boolean };
  startLoad: (nextRound: number) => void;
  setIsSaving: (value: boolean) => void;
  setErrorMessage: (message: string | null) => void;
  setIsConfirmingPublish: (value: boolean) => void;
  setSelectedIds: (value: number[] | ((current: number[]) => number[])) => void;
  router: { refresh: () => void };
}

function buildAdminMutations(options: AdminMutationOptions) {
  function toggleCandidate(candidate: TyperAdminCandidate) {
    if (candidate.is_published) {
      return;
    }
    options.setIsConfirmingPublish(false);
    options.setSelectedIds((current) =>
      toggleSelectedMatchId(current, candidate.match_id),
    );
  }

  async function confirmPublish() {
    const canPublish = canPublishSelection(
      options.candidates,
      options.selectedIds,
      options.roundNumber,
      options.groupMatchCount,
    );
    if (!canPublish) {
      return;
    }
    await runAdminMutation(
      options.inFlightRef,
      options.setIsSaving,
      options.setErrorMessage,
      options.groupMatchCount,
      async () => {
        await publishTyperMatches(
          options.seasonId,
          options.roundNumber,
          options.selectedIds,
        );
        options.setIsConfirmingPublish(false);
        options.startLoad(options.roundNumber);
        options.router.refresh();
      },
    );
  }

  async function unpublishMatch(matchId: number) {
    await runAdminMutation(
      options.inFlightRef,
      options.setIsSaving,
      options.setErrorMessage,
      options.groupMatchCount,
      async () => {
        await deleteTyperPublication(matchId);
        options.startLoad(options.roundNumber);
        options.router.refresh();
      },
    );
  }

  return { toggleCandidate, confirmPublish, unpublishMatch };
}
