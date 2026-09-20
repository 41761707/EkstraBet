"use client";

import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useRef, useState } from "react";

import {
  mergeCatalogMatches,
  tipsterMutationMessage,
  toTipsterCatalogQuery,
} from "@/components/tipsters/tipsterModel";
import { getTipsterCatalog } from "@/lib/apiClient";
import { getWarsawDateIso } from "@/lib/date";
import type { CatalogMatch } from "@/types/api";

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export interface PickerCatalogState {
  catalogDate: string;
  matchQuery: string;
  includeAllLeagues: boolean;
  pickerMatches: CatalogMatch[];
  knownMatches: CatalogMatch[];
  isLoading: boolean;
  error: string | null;
  changeDate: (date: string) => Promise<CatalogMatch[] | null>;
  changeIncludeAllLeagues: (
    includeAllLeagues: boolean,
  ) => Promise<CatalogMatch[] | null>;
  setMatchQuery: (query: string) => void;
}

interface CatalogScope {
  date: string;
  includeAllLeagues: boolean;
}

export function usePickerCatalog(
  initialMatches: CatalogMatch[],
  favoriteLeagueIds: number[],
): PickerCatalogState {
  const [catalogDate, setCatalogDate] = useState(() => getWarsawDateIso());
  const [matchQuery, setMatchQuery] = useState("");
  const [includeAllLeagues, setIncludeAllLeagues] = useState(false);
  const [pickerMatches, setPickerMatches] = useState(initialMatches);
  const [knownMatches, setKnownMatches] = useState(initialMatches);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const dateRef = useRef(catalogDate);
  const allLeaguesRef = useRef(false);
  const committedRef = useRef<CatalogScope>({
    date: catalogDate, includeAllLeagues: false,
  });

  async function reloadCatalog(
    nextDate: string,
    allLeagues: boolean,
  ): Promise<CatalogMatch[] | null> {
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    try {
      const next = await getTipsterCatalog(
        toTipsterCatalogQuery(nextDate, favoriteLeagueIds, allLeagues),
      );
      if (requestId !== requestIdRef.current) {
        return null;
      }
      commitCatalogMatches(
        committedRef,
        setPickerMatches,
        setKnownMatches,
        setError,
        nextDate,
        allLeagues,
        next.matches,
      );
      return next.matches;
    } catch (cause) {
      if (requestId !== requestIdRef.current) {
        return null;
      }
      setError(tipsterMutationMessage(cause));
      revertCatalogScope(
        committedRef,
        dateRef,
        allLeaguesRef,
        setCatalogDate,
        setIncludeAllLeagues,
      );
      return null;
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }

  async function changeDate(nextDate: string): Promise<CatalogMatch[] | null> {
    if (!ISO_DATE_PATTERN.test(nextDate)) {
      requestIdRef.current += 1;
      setIsLoading(false);
      revertCatalogScope(
        committedRef,
        dateRef,
        allLeaguesRef,
        setCatalogDate,
        setIncludeAllLeagues,
      );
      return null;
    }
    dateRef.current = nextDate;
    setCatalogDate(nextDate);
    return reloadCatalog(nextDate, allLeaguesRef.current);
  }

  async function changeIncludeAllLeagues(
    nextValue: boolean,
  ): Promise<CatalogMatch[] | null> {
    allLeaguesRef.current = nextValue;
    setIncludeAllLeagues(nextValue);
    return reloadCatalog(dateRef.current, nextValue);
  }

  return {
    catalogDate,
    matchQuery,
    includeAllLeagues,
    pickerMatches,
    knownMatches,
    isLoading,
    error,
    changeDate,
    changeIncludeAllLeagues,
    setMatchQuery,
  };
}

function commitCatalogMatches(
  committedRef: MutableRefObject<CatalogScope>,
  setPickerMatches: (matches: CatalogMatch[]) => void,
  setKnownMatches: Dispatch<SetStateAction<CatalogMatch[]>>,
  setError: (error: string | null) => void,
  nextDate: string,
  allLeagues: boolean,
  matches: CatalogMatch[],
) {
  setPickerMatches(matches);
  setKnownMatches((current) => mergeCatalogMatches(current, matches));
  setError(null);
  committedRef.current = { date: nextDate, includeAllLeagues: allLeagues };
}

function revertCatalogScope(
  committedRef: MutableRefObject<CatalogScope>,
  dateRef: MutableRefObject<string>,
  allLeaguesRef: MutableRefObject<boolean>,
  setCatalogDate: (date: string) => void,
  setIncludeAllLeagues: (value: boolean) => void,
) {
  const committed = committedRef.current;
  dateRef.current = committed.date;
  allLeaguesRef.current = committed.includeAllLeagues;
  setCatalogDate(committed.date);
  setIncludeAllLeagues(committed.includeAllLeagues);
}
