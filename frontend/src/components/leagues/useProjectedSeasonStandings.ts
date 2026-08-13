import { useEffect, useState } from "react";
import {
  defaultSeasonProjectionMode,
  shouldFetchProjectionModes,
  shouldFetchSeasonProjection,
} from "@/components/leagues/projectedSeasonStandingsModel";
import {
  ApiError,
  getSeasonProjection,
  getSeasonProjectionModes,
} from "@/lib/apiClient";
import type {
  SeasonProjectionMode,
  SeasonProjectionModeFlags,
  SeasonProjectionResponse,
} from "@/types/api";

const LOAD_ERROR = "Nie udało się pobrać projekcji sezonu.";

type ProjectionCache = Partial<
  Record<SeasonProjectionMode, SeasonProjectionResponse>
>;

function messageFromUnknown(loadError: unknown): string {
  return loadError instanceof Error ? loadError.message : LOAD_ERROR;
}

interface ProjectedSeasonStandingsState {
  loading: boolean;
  error: string | null;
  isNotFound: boolean;
  data: SeasonProjectionResponse | null;
  modeFlags: SeasonProjectionModeFlags | null;
  selectedMode: SeasonProjectionMode | null;
  selectMode: (mode: SeasonProjectionMode) => void;
}

export function useProjectedSeasonStandings(
  leagueId: number,
  seasonId: number,
  isOpen: boolean,
): ProjectedSeasonStandingsState {
  const [modeFlags, setModeFlags] = useState<SeasonProjectionModeFlags | null>(
    null,
  );
  const [selectedMode, setSelectedMode] = useState<SeasonProjectionMode | null>(
    null,
  );
  const [cache, setCache] = useState<ProjectionCache>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);

  useEffect(() => {
    setModeFlags(null);
    setSelectedMode(null);
    setCache({});
    setError(null);
    setIsNotFound(false);
  }, [leagueId, seasonId]);

  useEffect(() => {
    if (!shouldFetchProjectionModes(isOpen, modeFlags !== null)) {
      return;
    }
    let cancelled = false;
    void loadModeFlags({
      leagueId,
      seasonId,
      cancelled: () => cancelled,
      setModeFlags,
      setSelectedMode,
      setLoading,
      setError,
      setIsNotFound,
    });
    return () => {
      cancelled = true;
    };
  }, [isOpen, modeFlags, leagueId, seasonId]);

  useEffect(() => {
    const hasData = selectedMode !== null && cache[selectedMode] !== undefined;
    if (!shouldFetchSeasonProjection(isOpen, selectedMode, hasData)) {
      return;
    }
    const mode = selectedMode;
    if (mode === null) {
      return;
    }
    let cancelled = false;
    void loadProjection({
      leagueId,
      seasonId,
      mode,
      cancelled: () => cancelled,
      setCache,
      setLoading,
      setError,
      setIsNotFound,
    });
    return () => {
      cancelled = true;
    };
  }, [isOpen, selectedMode, cache, leagueId, seasonId]);

  return {
    loading,
    error,
    isNotFound,
    data: selectedMode ? (cache[selectedMode] ?? null) : null,
    modeFlags,
    selectedMode,
    selectMode: (mode: SeasonProjectionMode) => {
      setSelectedMode(mode);
      if (cache[mode] === undefined) {
        setLoading(true);
      }
    },
  };
}

async function loadModeFlags(args: {
  leagueId: number;
  seasonId: number;
  cancelled: () => boolean;
  setModeFlags: (flags: SeasonProjectionModeFlags) => void;
  setSelectedMode: (mode: SeasonProjectionMode | null) => void;
  setLoading: (value: boolean) => void;
  setError: (value: string | null) => void;
  setIsNotFound: (value: boolean) => void;
}): Promise<void> {
  args.setLoading(true);
  args.setError(null);
  args.setIsNotFound(false);
  try {
    const flags = await getSeasonProjectionModes(args.leagueId, args.seasonId);
    if (args.cancelled()) {
      return;
    }
    args.setModeFlags(flags);
    const nextMode = defaultSeasonProjectionMode(flags);
    args.setSelectedMode(nextMode);
    if (nextMode === null) {
      args.setIsNotFound(true);
      args.setLoading(false);
    }
  } catch (loadError) {
    if (args.cancelled()) {
      return;
    }
    args.setError(messageFromUnknown(loadError));
    args.setLoading(false);
  }
}

async function loadProjection(args: {
  leagueId: number;
  seasonId: number;
  mode: SeasonProjectionMode;
  cancelled: () => boolean;
  setCache: (
    update: (current: ProjectionCache) => ProjectionCache,
  ) => void;
  setLoading: (value: boolean) => void;
  setError: (value: string | null) => void;
  setIsNotFound: (value: boolean) => void;
}): Promise<void> {
  args.setLoading(true);
  args.setError(null);
  args.setIsNotFound(false);
  try {
    const response = await getSeasonProjection(
      args.leagueId,
      args.seasonId,
      args.mode,
    );
    if (!args.cancelled()) {
      args.setCache((current) => ({ ...current, [args.mode]: response }));
    }
  } catch (loadError) {
    if (args.cancelled()) {
      return;
    }
    if (loadError instanceof ApiError && loadError.status === 404) {
      args.setIsNotFound(true);
      return;
    }
    args.setError(messageFromUnknown(loadError));
  } finally {
    if (!args.cancelled()) {
      args.setLoading(false);
    }
  }
}
