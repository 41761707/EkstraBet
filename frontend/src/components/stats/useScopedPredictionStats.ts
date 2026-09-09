import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import {
  areScopedDateFiltersValid,
  isAnalyticsEmpty,
  resetScopedPredictionStatsFilters,
  shouldFetchScopedPredictionAnalytics,
  shouldFetchScopedPredictionStats,
  toModelAnalyticsQuery,
  withDefaultScopedModelIds,
  type ScopedPredictionStatsFiltersState,
  type ScopedPredictionStatsScope,
} from "@/components/stats/scopedPredictionStatsModel";
import {
  ApiError,
  getModelAnalytics,
  getModelsGroupedByFamily,
  type ModelsByFamily,
} from "@/lib/apiClient";
import { FOOTBALL_SPORT_ID, type ModelAnalyticsResponse } from "@/types/api";

export type ScopedPredictionStatsStatus =
  | "idle"
  | "loading"
  | "error"
  | "empty"
  | "ready";

export interface UseScopedPredictionStatsResult {
  status: ScopedPredictionStatsStatus;
  error: string | null;
  analytics: ModelAnalyticsResponse | null;
  modelsByFamily: ModelsByFamily;
  appliedFilters: ScopedPredictionStatsFiltersState;
  applyFilters: (filters: ScopedPredictionStatsFiltersState) => void;
}

const LOAD_ERROR = "Nie udało się pobrać statystyk predykcji.";

const EMPTY_MODELS_BY_FAMILY: ModelsByFamily = {
  result: [],
  ou: [],
  btts: [],
};

interface ScopedPredictionStatsStore {
  hasLoadedModels: boolean;
  hasLoadedOnce: boolean;
  loading: boolean;
  error: string | null;
  analytics: ModelAnalyticsResponse | null;
  modelsByFamily: ModelsByFamily;
  appliedFilters: ScopedPredictionStatsFiltersState;
}

type StoreSetter = Dispatch<SetStateAction<ScopedPredictionStatsStore>>;

function createInitialStore(): ScopedPredictionStatsStore {
  return {
    hasLoadedModels: false,
    hasLoadedOnce: false,
    loading: false,
    error: null,
    analytics: null,
    modelsByFamily: EMPTY_MODELS_BY_FAMILY,
    appliedFilters: resetScopedPredictionStatsFilters(EMPTY_MODELS_BY_FAMILY),
  };
}

/** Lazy-loads models then analytics on expander open; Apply refetches analytics. */
export function useScopedPredictionStats(
  scope: ScopedPredictionStatsScope,
  isOpen: boolean,
): UseScopedPredictionStatsResult {
  const [store, setStore] = useState(createInitialStore);
  const requestIdRef = useRef(0);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      // Apply nie żyje w efekcie — bez tej flagi setStore po nawigacji trafia w odmontowany hook
      cancelledRef.current = true;
    };
  }, []);

  useEffect(() => {
    requestIdRef.current += 1;
    setStore(createInitialStore());
  }, [scope.leagueId, scope.seasonId, scope.teamId]);

  useEffect(() => {
    if (!shouldFetchScopedPredictionStats(isOpen, store.hasLoadedModels)) {
      return;
    }
    let cancelled = false;
    void loadModels(() => cancelled, setStore);
    return () => {
      cancelled = true;
    };
  }, [
    isOpen,
    store.hasLoadedModels,
    scope.leagueId,
    scope.seasonId,
    scope.teamId,
  ]);

  useEffect(() => {
    if (
      !shouldFetchScopedPredictionAnalytics(
        isOpen,
        store.hasLoadedModels,
        store.hasLoadedOnce,
      )
    ) {
      return;
    }
    let cancelled = false;
    const requestId = ++requestIdRef.current;
    setStore((current) => ({ ...current, loading: true, error: null }));
    void loadAnalyticsOnly(
      scope,
      store.appliedFilters,
      requestId,
      requestIdRef,
      () => cancelled,
      setStore,
    );
    return () => {
      cancelled = true;
    };
    // Apply vs ten fetch rozstrzyga requestId — appliedFilters nie może restartować etapu
    // eslint-disable-next-line react-hooks/exhaustive-deps -- patrz komentarz powyżej
  }, [
    isOpen,
    store.hasLoadedModels,
    store.hasLoadedOnce,
    scope.leagueId,
    scope.seasonId,
    scope.teamId,
  ]);

  return {
    status: resolveStatus(store),
    error: store.error,
    analytics: store.analytics,
    modelsByFamily: store.modelsByFamily,
    appliedFilters: store.appliedFilters,
    applyFilters: (filters) => {
      applyScopedFilters(
        scope,
        filters,
        store.modelsByFamily,
        store.hasLoadedModels,
        requestIdRef,
        cancelledRef,
        setStore,
      );
    },
  };
}

function applyScopedFilters(
  scope: ScopedPredictionStatsScope,
  filters: ScopedPredictionStatsFiltersState,
  modelsByFamily: ModelsByFamily,
  hasLoadedModels: boolean,
  requestIdRef: { current: number },
  cancelledRef: { current: boolean },
  setStore: StoreSetter,
): void {
  if (!hasLoadedModels || cancelledRef.current) {
    return;
  }
  if (!areScopedDateFiltersValid(filters.dateFrom, filters.dateTo)) {
    return;
  }
  const nextFilters = withDefaultScopedModelIds(filters, modelsByFamily);
  const requestId = ++requestIdRef.current;
  setStore((current) => ({
    ...current,
    appliedFilters: nextFilters,
    loading: true,
    error: null,
  }));
  void loadAnalyticsOnly(
    scope,
    nextFilters,
    requestId,
    requestIdRef,
    () => cancelledRef.current,
    setStore,
  );
}

function resolveStatus(
  store: ScopedPredictionStatsStore,
): ScopedPredictionStatsStatus {
  if (store.error) {
    return "error";
  }
  if (store.loading) {
    return "loading";
  }
  if (!store.hasLoadedOnce) {
    return "idle";
  }
  if (store.analytics === null || isAnalyticsEmpty(store.analytics)) {
    return "empty";
  }
  return "ready";
}

function messageFromLoadError(loadError: unknown): string {
  if (loadError instanceof ApiError && loadError.message.trim()) {
    return `${LOAD_ERROR} ${loadError.message}`;
  }
  if (loadError instanceof Error && loadError.message.trim()) {
    return `${LOAD_ERROR} ${loadError.message}`;
  }
  return LOAD_ERROR;
}

function isCurrentRequest(
  requestId: number,
  requestIdRef: { current: number },
): boolean {
  return requestIdRef.current === requestId;
}

function shouldIgnoreAnalyticsResult(
  cancelled: () => boolean,
  requestId: number,
  requestIdRef: { current: number },
): boolean {
  return cancelled() || !isCurrentRequest(requestId, requestIdRef);
}

async function loadModels(
  cancelled: () => boolean,
  setStore: StoreSetter,
): Promise<void> {
  setStore((current) => ({ ...current, loading: true, error: null }));
  try {
    const modelsByFamily = await getModelsGroupedByFamily(FOOTBALL_SPORT_ID);
    const appliedFilters = resetScopedPredictionStatsFilters(modelsByFamily);
    if (cancelled()) {
      return;
    }
    // loading zostaje true — etap analytics dociąga dane albo ustawi błąd
    setStore((current) => ({
      ...current,
      hasLoadedModels: true,
      modelsByFamily,
      appliedFilters,
    }));
  } catch (loadError) {
    if (cancelled()) {
      return;
    }
    setStore((current) => ({
      ...current,
      loading: false,
      error: messageFromLoadError(loadError),
    }));
  }
}

async function loadAnalyticsOnly(
  scope: ScopedPredictionStatsScope,
  filters: ScopedPredictionStatsFiltersState,
  requestId: number,
  requestIdRef: { current: number },
  cancelled: () => boolean,
  setStore: StoreSetter,
): Promise<void> {
  try {
    const analytics = await getModelAnalytics(
      toModelAnalyticsQuery(scope, filters),
    );
    if (shouldIgnoreAnalyticsResult(cancelled, requestId, requestIdRef)) {
      return;
    }
    setStore((current) => ({
      ...current,
      hasLoadedOnce: true,
      loading: false,
      error: null,
      analytics,
      appliedFilters: filters,
    }));
  } catch (loadError) {
    if (shouldIgnoreAnalyticsResult(cancelled, requestId, requestIdRef)) {
      return;
    }
    setStore((current) => ({
      ...current,
      loading: false,
      error: messageFromLoadError(loadError),
    }));
  }
}
