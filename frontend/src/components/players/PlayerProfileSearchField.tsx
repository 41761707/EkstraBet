"use client";

import { useEffect, useId, useState } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { ApiError, searchProfilePlayers } from "@/lib/apiClient";
import { canSelectTeammate } from "@/lib/playerProfileParams";
import type { PlayerSearchHit } from "@/types/api";

const SEARCH_MIN_LENGTH = 2;
const SEARCH_DELAY_MS = 250;
const SEARCH_ERROR = "Nie udało się wyszukać zawodnika.";
const SAME_PLAYER_MESSAGE = "Partner musi być innym zawodnikiem.";

interface PlayerProfileSearchFieldProps {
  playerId: number;
  sportId: number | null;
  teammateId: number | null;
  teammateLabel: string | null;
  onChange: (selection: {
    teammateId: number | null;
    teammateLabel: string | null;
  }) => void;
}

interface SearchResult {
  hits: PlayerSearchHit[];
  error: string | null;
}

export function PlayerProfileSearchField({
  playerId,
  sportId,
  teammateId,
  teammateLabel,
  onChange,
}: PlayerProfileSearchFieldProps) {
  const listId = useId();
  const [term, setTerm] = useState(teammateLabel ?? "");
  const [isOpen, setIsOpen] = useState(false);
  const [samePlayerMessage, setSamePlayerMessage] = useState<string | null>(
    null,
  );
  const isCommitted =
    teammateId != null && term.trim() === (teammateLabel ?? "");
  const searchEnabled = sportId != null;
  const search = useProfilePlayerSearch(sportId, term, isCommitted);
  const showList = searchEnabled && isOpen && !isCommitted && search.hits.length > 0;

  function updateTerm(next: string) {
    setTerm(next);
    setSamePlayerMessage(null);
    setIsOpen(true);
    if (teammateId != null && next.trim() !== (teammateLabel ?? "")) {
      onChange({ teammateId: null, teammateLabel: null });
    }
  }

  function selectHit(hit: PlayerSearchHit) {
    if (!canSelectTeammate(playerId, hit.player_id)) {
      setSamePlayerMessage(SAME_PLAYER_MESSAGE);
      return;
    }
    onChange({ teammateId: hit.player_id, teammateLabel: hit.player_name });
    setTerm(hit.player_name);
    setSamePlayerMessage(null);
    setIsOpen(false);
  }

  function clearSelection() {
    onChange({ teammateId: null, teammateLabel: null });
    setTerm("");
    setSamePlayerMessage(null);
    setIsOpen(false);
  }

  const message = samePlayerMessage ?? search.error;

  return (
    <div className="space-y-2 text-sm text-muted">
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={`${listId}-input`} className="font-medium text-text">
          Partner
        </label>
        {teammateId != null ? (
          <button
            type="button"
            className="text-accent-text transition hover:text-accent-text-hover"
            onClick={clearSelection}
          >
            Wyczyść
          </button>
        ) : null}
      </div>
      <div className="relative">
        <input
          id={`${listId}-input`}
          type="search"
          className={
            `w-full rounded-lg text-sm disabled:cursor-not-allowed ` +
            `disabled:opacity-60 ${INPUT_CLASS_NAME}`
          }
          value={term}
          placeholder={
            searchEnabled
              ? "Wpisz co najmniej 2 znaki"
              : "Wyszukiwarka niedostępna"
          }
          disabled={!searchEnabled}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          onChange={(event) => updateTerm(event.target.value)}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setIsOpen(false)}
        />
        {showList ? (
          <ProfileSearchHits
            listId={listId}
            hits={search.hits}
            onSelect={selectHit}
          />
        ) : null}
      </div>
      {message ? <p className="text-danger-text">{message}</p> : null}
    </div>
  );
}

function ProfileSearchHits({
  listId,
  hits,
  onSelect,
}: {
  listId: string;
  hits: PlayerSearchHit[];
  onSelect: (hit: PlayerSearchHit) => void;
}) {
  return (
    <ul
      id={listId}
      role="listbox"
      className={
        "absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-xl " +
        "border border-border bg-surface p-1"
      }
    >
      {hits.map((hit) => (
        <li key={hit.player_id}>
          <button
            type="button"
            role="option"
            className={
              "w-full rounded-lg px-3 py-2 text-left text-sm text-text " +
              "hover:bg-surface-muted"
            }
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onSelect(hit)}
          >
            {hit.player_name}
            {hit.current_team_name ? (
              <span className="text-muted">{` · ${hit.current_team_name}`}</span>
            ) : null}
          </button>
        </li>
      ))}
    </ul>
  );
}

function useProfilePlayerSearch(
  sportId: number | null,
  term: string,
  isCommitted: boolean,
): SearchResult {
  const [result, setResult] = useState<SearchResult>({ hits: [], error: null });

  useEffect(() => {
    const query = term.trim();
    if (sportId == null || query.length < SEARCH_MIN_LENGTH || isCommitted) {
      setResult({ hits: [], error: null });
      return;
    }

    let cancelled = false;
    const timer = setTimeout(() => {
      void loadHits(sportId, query).then((next) => {
        if (!cancelled) {
          setResult(next);
        }
      });
    }, SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [sportId, term, isCommitted]);

  return result;
}

async function loadHits(sportId: number, term: string): Promise<SearchResult> {
  try {
    const response = await searchProfilePlayers(sportId, term);
    return { hits: response.players, error: null };
  } catch (error) {
    const message = error instanceof ApiError ? error.message : SEARCH_ERROR;
    return { hits: [], error: message };
  }
}
