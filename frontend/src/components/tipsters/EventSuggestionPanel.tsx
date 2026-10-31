"use client";

import { useRef, useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import {
  buildSuggestEventsRequest,
  draftMatchIds,
  eventAdvisorErrorMessage,
  suggestionTierGroups,
  suggestionTierPhrase,
  suggestionsAreEmpty,
  visibleReasonLabels,
  withoutMatchSuggestions,
  type SuggestableDraftLeg,
} from "@/components/tipsters/eventAdvisorModel";
import { suggestMyEvents } from "@/lib/apiClient";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import type {
  EventSuggestion,
  EventSuggestionTier,
  EventSuggestionTiers,
} from "@/types/api";

export const SUGGEST_EVENTS_BUTTON_LABEL = "Wygeneruj sugestie zdarzeń";
export const SUGGEST_EVENTS_OPTIONAL_HINT =
  "Brak pomysłu? A może szukasz inspiracji? Komputer zawsze Ci coś doradzi";
export const ADD_SUGGESTED_EVENT_LABEL = "Dodaj do kuponu";
export const SUGGESTIONS_SECTION_TITLE = "Sugestie zdarzeń";
export const SUGGESTION_DISCLAIMER =
  "Poniżej znajdują się sugestie systemu dotyczące zdarzeń, które mogą Cię zainteresować. " +
  "Sugestie opierają się na Twojej historii kuponów, Twoich ulubionych ligach oraz predykcjach komputera jak i kursach bukmacherskich.";
export const COLD_START_HINT =
  "Niewystarczająca liczba kuponów - sugestie opierają się tylko " +
  "na werdykcie komputera i ulubionych ligach.";
export const EMPTY_SUGGESTIONS_TITLE =
  "Brak zdarzeń pasujących do Twojego profilu.";
export const EMPTY_TIER_LABEL = "Brak propozycji";
export const SUGGESTIONS_LOADING_LABEL = "Szukam zdarzeń…";
export const SUGGESTIONS_ERROR_TITLE = "Nie udało się zasugerować zdarzeń";

const SUGGEST_BUTTON_CLASS_NAME =
  "rounded-md border border-border px-4 py-2 text-sm font-medium text-text " +
  "transition hover:bg-surface-raised disabled:cursor-not-allowed " +
  "disabled:opacity-60";

const TIER_BADGE_CLASS_NAME =
  "inline-block rounded-md border border-border bg-surface-muted " +
  "px-2 py-0.5 text-xs font-semibold text-text";

export interface EventSuggestionsController {
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  coldStart: boolean;
  tiers: EventSuggestionTiers | null;
  serverSuggestionsEmpty: boolean;
  load: () => Promise<void>;
}

export function useEventSuggestions(
  legs: readonly SuggestableDraftLeg[],
): EventSuggestionsController {
  const legsRef = useRef(legs);
  legsRef.current = legs;
  const requestId = useRef(0);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [coldStart, setColdStart] = useState(false);
  const [payload, setPayload] = useState<EventSuggestionTiers | null>(null);

  async function load() {
    const id = requestId.current + 1;
    requestId.current = id;
    setIsOpen(true);
    setIsLoading(true);
    setError(null);
    try {
      const response = await suggestMyEvents(
        buildSuggestEventsRequest(legsRef.current),
      );
      if (requestId.current !== id) {
        return;
      }
      setColdStart(response.cold_start);
      setPayload(response.tiers);
    } catch (cause: unknown) {
      if (requestId.current !== id) {
        return;
      }
      setColdStart(false);
      setPayload(null);
      setError(eventAdvisorErrorMessage(cause));
    } finally {
      if (requestId.current === id) {
        setIsLoading(false);
      }
    }
  }

  const tiers = payload === null
    ? null
    : withoutMatchSuggestions(payload, draftMatchIds(legs));

  return {
    isOpen,
    isLoading,
    error,
    coldStart,
    tiers,
    serverSuggestionsEmpty:
      payload !== null && suggestionsAreEmpty(payload),
    load,
  };
}

interface SuggestEventsButtonProps {
  disabled: boolean;
  onClick: () => void;
}

export function SuggestEventsButton({
  disabled,
  onClick,
}: SuggestEventsButtonProps) {
  return (
    <aside className="space-y-2 rounded-lg border border-dashed border-border bg-surface-muted px-4 py-3">
      <p className="text-sm leading-relaxed text-muted">
        {SUGGEST_EVENTS_OPTIONAL_HINT}
      </p>
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={SUGGEST_BUTTON_CLASS_NAME}
      >
        {SUGGEST_EVENTS_BUTTON_LABEL}
      </button>
    </aside>
  );
}

interface EventSuggestionPanelProps {
  isLoading: boolean;
  error: string | null;
  coldStart: boolean;
  tiers: EventSuggestionTiers | null;
  serverSuggestionsEmpty: boolean;
  disabled: boolean;
  onAdd: (suggestion: EventSuggestion) => void;
}

export function EventSuggestionPanel({
  isLoading,
  error,
  coldStart,
  tiers,
  serverSuggestionsEmpty,
  disabled,
  onAdd,
}: EventSuggestionPanelProps) {
  const groups = tiers === null ? [] : suggestionTierGroups(tiers);
  // Widok bez meczów ze szkicu nie jest pustą odpowiedzią doradcy.
  const showHistoryGap = serverSuggestionsEmpty && !isLoading && !error;

  return (
    <div className="space-y-3">
      {coldStart ? (
        <p className="rounded-lg border border-info-border bg-info-bg px-3 py-2 text-sm leading-relaxed text-info-text">
          {COLD_START_HINT}
        </p>
      ) : null}
      {isLoading ? (
        <p className="text-sm text-muted">{SUGGESTIONS_LOADING_LABEL}</p>
      ) : null}
      {error ? (
        <StatusMessage
          variant="error"
          title={SUGGESTIONS_ERROR_TITLE}
          message={error}
        />
      ) : null}
      {showHistoryGap ? (
        <StatusMessage variant="empty" title={EMPTY_SUGGESTIONS_TITLE} />
      ) : null}
      {groups.map((group) => (
        <SuggestionTierList
          key={group.tier}
          tier={group.tier}
          phrase={suggestionTierPhrase(group.tier)}
          items={group.items}
          disabled={disabled}
          onAdd={onAdd}
        />
      ))}
    </div>
  );
}

interface SuggestionTierListProps {
  tier: EventSuggestionTier;
  phrase: string;
  items: EventSuggestion[];
  disabled: boolean;
  onAdd: (suggestion: EventSuggestion) => void;
}

function SuggestionTierList({
  tier,
  phrase,
  items,
  disabled,
  onAdd,
}: SuggestionTierListProps) {
  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold text-text">
        <span className={TIER_BADGE_CLASS_NAME}>{tier}</span>
        <span className="ml-2">{` — ${phrase}`}</span>
      </h4>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{EMPTY_TIER_LABEL}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <SuggestionRow
              key={`${item.match_id}-${item.event_id}`}
              item={item}
              disabled={disabled}
              onAdd={onAdd}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

interface SuggestionRowProps {
  item: EventSuggestion;
  disabled: boolean;
  onAdd: (suggestion: EventSuggestion) => void;
}

function SuggestionRow({ item, disabled, onAdd }: SuggestionRowProps) {
  const reasons = visibleReasonLabels(item.reasons);

  return (
    <li className="rounded-lg border border-border bg-surface px-3 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs text-muted">{item.league_name}</p>
          <p className="font-medium text-text">
            {item.home_name} – {item.away_name}
          </p>
          <p className="text-sm text-muted">
            {formatMatchDateTime(item.game_date)}
          </p>
          <p className="text-sm text-text">
            {item.event_name}
            <span className="text-muted">{` · ${formatOdds(item.odds)}`}</span>
          </p>
          {reasons.length > 0 ? (
            <ul className="flex flex-wrap gap-1">
              {reasons.map((label) => (
                <li
                  key={label}
                  className={
                    "rounded-full border border-border bg-surface-muted " +
                    "px-2 py-0.5 text-xs text-text"
                  }
                >
                  {label}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAdd(item)}
          className={SUGGEST_BUTTON_CLASS_NAME}
        >
          {ADD_SUGGESTED_EVENT_LABEL}
        </button>
      </div>
    </li>
  );
}
