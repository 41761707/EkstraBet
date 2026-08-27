"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type ReactNode,
  type SetStateAction,
} from "react";

import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesContextValue,
  type PreferencesStorage,
  type TeamNameDisplayPreference,
  type ThemePreference,
  type UserPreferencesPatch,
  type UserPreferencesV1,
} from "@/lib/preferences";
import { createPreferencesApi } from "@/lib/preferencesApi";
import { createLocalPreferencesStorage } from "@/lib/preferencesStorage";
import {
  createPreferencesWriteQueue,
  hydrateAccountPreferences,
  persistPreferencesPatch,
  type PreferencesWriteQueue,
} from "@/lib/preferencesSync";
import {
  applyResolvedTheme,
  COLOR_SCHEME_DARK_QUERY,
  getSystemPrefersDark,
  nextExplicitTheme,
  resolveTheme,
} from "@/lib/theme";

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

const defaultStorage = createLocalPreferencesStorage();
const defaultApi = createPreferencesApi();

const USE_PREFERENCES_ERROR =
  "usePreferences must be used within PreferencesProvider";

interface PreferencesProviderProps {
  children: ReactNode;
  hasSession: boolean;
  storage?: PreferencesStorage;
  api?: PreferencesApi;
}

/**
 * Reads the current preference document from Context.
 * Throws when rendered outside `PreferencesProvider`.
 */
export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (value == null) {
    throw new Error(USE_PREFERENCES_ERROR);
  }
  return value;
}

export function PreferencesProvider({
  children,
  hasSession,
  storage = defaultStorage,
  api = defaultApi,
}: PreferencesProviderProps) {
  const value = usePreferencesController({ hasSession, storage, api });
  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

interface PreferencesControllerOptions {
  hasSession: boolean;
  storage: PreferencesStorage;
  api: PreferencesApi;
}

interface PreferencesBootstrapDeps {
  storage: PreferencesStorage;
  api: PreferencesApi;
  hasSession: boolean;
  writeQueue: PreferencesWriteQueue;
  writeEpochRef: MutableRefObject<number>;
  setPreferences: Dispatch<SetStateAction<UserPreferencesV1>>;
  setSystemPrefersDark: Dispatch<SetStateAction<boolean>>;
}

/**
 * Mount-time bootstrap: load the local cache, apply its theme, then hydrate
 * from the account when a session exists. Returns the effect cleanup.
 */
function bootstrapPreferences(deps: PreferencesBootstrapDeps): () => void {
  const {
    storage,
    api,
    hasSession,
    writeQueue,
    writeEpochRef,
    setPreferences,
    setSystemPrefersDark,
  } = deps;
  const loaded = storage.load();
  const prefersDark = getSystemPrefersDark();
  setPreferences(loaded);
  setSystemPrefersDark(prefersDark);
  applyResolvedTheme(resolveTheme(loaded.theme, prefersDark));

  if (!hasSession) {
    return () => undefined;
  }

  let cancelled = false;
  const epoch = writeEpochRef.current;
  const isHydrationCurrent = (): boolean =>
    !cancelled && writeEpochRef.current === epoch;
  void hydrateAccountPreferences({
    storage,
    api,
    writeQueue,
    shouldApply: isHydrationCurrent,
    apply: (remote) => {
      // epoch tuż przed setState — ten sam warunek co przed storage.save
      if (!isHydrationCurrent()) {
        return;
      }
      setPreferences(remote);
      applyResolvedTheme(resolveTheme(remote.theme, getSystemPrefersDark()));
    },
  });
  return () => {
    cancelled = true;
  };
}

function usePreferencesController(
  options: PreferencesControllerOptions,
): PreferencesContextValue {
  const { hasSession, storage, api } = options;
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [systemPrefersDark, setSystemPrefersDark] = useState(true);
  const writeEpochRef = useRef(0);
  const writeQueueRef = useRef(createPreferencesWriteQueue());
  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;

  useEffect(() => {
    const cleanup = bootstrapPreferences({
      storage,
      api,
      hasSession,
      writeQueue: writeQueueRef.current,
      writeEpochRef,
      setPreferences,
      setSystemPrefersDark,
    });
    return cleanup;
  }, [api, hasSession, storage]);

  useEffect(() => {
    const hasMatchMedia =
      typeof window !== "undefined" && typeof window.matchMedia === "function";
    if (!hasMatchMedia) {
      return;
    }
    let media: MediaQueryList;
    try {
      media = window.matchMedia(COLOR_SCHEME_DARK_QUERY);
    } catch {
      return;
    }
    function handleChange(event: MediaQueryListEvent) {
      setSystemPrefersDark(event.matches);
      if (preferencesRef.current.theme === "system") {
        applyResolvedTheme(resolveTheme("system", event.matches));
      }
    }
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  const resolvedTheme = resolveTheme(preferences.theme, systemPrefersDark);

  const commitPatch = useCallback(
    (update: UserPreferencesPatch): void => {
      writeEpochRef.current += 1;
      const next = persistPreferencesPatch(
        preferencesRef.current,
        update,
        {
          storage,
          api,
          hasSession,
          systemPrefersDark,
          writeQueue: writeQueueRef.current,
        },
      );
      // ref synchronicznie, zanim setState — drugi setter w tej samej klatce
      // musi widzieć już scalony dokument, nie stary storage
      preferencesRef.current = next;
      setPreferences(next);
    },
    [api, hasSession, storage, systemPrefersDark],
  );

  const setTheme = useCallback(
    (theme: ThemePreference) => commitPatch({ theme }),
    [commitPatch],
  );

  const setTeamNameDisplay = useCallback(
    (preference: TeamNameDisplayPreference) =>
      commitPatch({ teamNameDisplay: preference }),
    [commitPatch],
  );

  const toggleTheme = useCallback(() => {
    setTheme(nextExplicitTheme(resolvedTheme));
  }, [resolvedTheme, setTheme]);

  return useMemo(
    () => ({
      preferences,
      resolvedTheme,
      setTheme,
      setTeamNameDisplay,
      toggleTheme,
    }),
    [preferences, resolvedTheme, setTheme, setTeamNameDisplay, toggleTheme],
  );
}
