"use client";

import { useEffect, useState } from "react";

import { FIELD_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import {
  catalogMatchOptionLabel,
  filterCatalogEvents,
  filterCatalogMatches,
  groupCatalogEvents,
  groupCatalogMatches,
  resolveCatalogEventId,
} from "@/components/tipsters/tipsterModel";
import { getWarsawDateIso } from "@/lib/date";
import type { CatalogMatch, CatalogMatchesResponse } from "@/types/api";

export const ADD_CATALOG_EVENT_LABEL = "Dodaj zdarzenie";
export const MATCH_SEARCH_LABEL = "Szukaj meczu";
export const EVENT_SEARCH_LABEL = "Szukaj zdarzenia";
export const CATALOG_DATE_LABEL = "Data";
export const ALL_LEAGUES_LABEL = "Wszystkie ligi";
export const CATALOG_UPCOMING_HINT =
  "Katalog pokazuje tylko mecze, które jeszcze się nie rozpoczęły.";
export const FAVORITES_UNAVAILABLE_HINT =
  "Nie udało się wczytać ulubionych lig — mecze ze wszystkich lig z wybranej daty.";
const CATALOG_CHECKBOX_CLASS_NAME =
  "rounded border-border bg-surface-raised accent-accent";

export interface CouponPickerProps {
  events: CatalogMatchesResponse["events"];
  pickerMatches: CatalogMatch[];
  catalogDate: string;
  matchQuery: string;
  includeAllLeagues: boolean;
  hasFavoriteLeagues: boolean;
  favoritesUnavailable: boolean;
  isLoadingMatches: boolean;
  catalogError: string | null;
  matchId: number;
  eventId: number;
  disabled: boolean;
  onDateChange: (date: string) => void;
  onAllLeaguesChange: (includeAllLeagues: boolean) => void;
  onQueryChange: (query: string) => void;
  onMatchChange: (matchId: number) => void;
  onEventChange: (eventId: number) => void;
  onAdd: (eventId: number) => void;
}

export function CouponPicker({
  events,
  pickerMatches,
  catalogDate,
  matchQuery,
  includeAllLeagues,
  hasFavoriteLeagues,
  favoritesUnavailable,
  isLoadingMatches,
  catalogError,
  matchId,
  eventId,
  disabled,
  onDateChange,
  onAllLeaguesChange,
  onQueryChange,
  onMatchChange,
  onEventChange,
  onAdd,
}: CouponPickerProps) {
  const [eventQuery, setEventQuery] = useState("");
  const selectedEventId = useVisibleEventId(
    events, eventQuery, eventId, onEventChange,
  );
  if (events.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak zdarzeń do kuponu"
        message="Katalog pokazuje tylko rozliczalne zdarzenia."
      />
    );
  }

  const visibleMatches = filterCatalogMatches(pickerMatches, matchQuery);
  const controlsDisabled = disabled || isLoadingMatches;
  const visibleEvents = filterCatalogEvents(events, eventQuery);
  const canAdd = visibleMatches.length > 0 && visibleEvents.length > 0;

  return (
    <div className="space-y-3">
      <CatalogScopeNote
        hasFavoriteLeagues={hasFavoriteLeagues}
        includeAllLeagues={includeAllLeagues}
        favoritesUnavailable={favoritesUnavailable}
      />
      {catalogError ? (
        <StatusMessage
          variant="error"
          title="Nie udało się odświeżyć katalogu"
          message={catalogError}
        />
      ) : null}
      <CatalogFilters
        catalogDate={catalogDate}
        matchQuery={matchQuery}
        eventQuery={eventQuery}
        includeAllLeagues={includeAllLeagues}
        hasFavoriteLeagues={hasFavoriteLeagues && !favoritesUnavailable}
        disabled={controlsDisabled}
        onDateChange={onDateChange}
        onAllLeaguesChange={onAllLeaguesChange}
        onQueryChange={onQueryChange}
        onEventQueryChange={setEventQuery}
      />
      <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <MatchSelect
          matches={visibleMatches}
          matchId={matchId}
          emptyLabel={emptyMatchesLabel(matchQuery)}
          disabled={controlsDisabled}
          onMatchChange={onMatchChange}
        />
        <EventSelect
          events={visibleEvents}
          eventId={selectedEventId}
          emptyLabel={emptyEventsLabel(eventQuery)}
          disabled={controlsDisabled}
          onEventChange={onEventChange}
        />
        <button
          type="button"
          disabled={controlsDisabled || !canAdd}
          onClick={() => {
            onAdd(selectedEventId);
            onQueryChange("");
            setEventQuery("");
          }}
          className={
            "rounded-md border border-border px-4 py-2 text-sm font-medium " +
            "text-text transition hover:bg-surface-raised disabled:opacity-60"
          }
        >
          {ADD_CATALOG_EVENT_LABEL}
        </button>
      </div>
    </div>
  );
}

function CatalogScopeNote({
  hasFavoriteLeagues,
  includeAllLeagues,
  favoritesUnavailable,
}: {
  hasFavoriteLeagues: boolean;
  includeAllLeagues: boolean;
  favoritesUnavailable: boolean;
}) {
  return (
    <div
      className={
        "space-y-1 rounded-lg border border-border bg-surface-muted " +
        "px-3 py-2 text-sm leading-relaxed text-muted"
      }
    >
      <p>
        {catalogScopeHint(
          hasFavoriteLeagues,
          includeAllLeagues,
          favoritesUnavailable,
        )}
      </p>
      <p>{CATALOG_UPCOMING_HINT}</p>
    </div>
  );
}

function catalogScopeHint(
  hasFavoriteLeagues: boolean,
  includeAllLeagues: boolean,
  favoritesUnavailable: boolean,
): string {
  if (favoritesUnavailable) {
    return FAVORITES_UNAVAILABLE_HINT;
  }
  if (!hasFavoriteLeagues) {
    return "Brak ulubionych lig: mecze z wybranej daty, wszystkie ligi.";
  }
  if (includeAllLeagues) {
    return "Wszystkie ligi z wybranej daty.";
  }
  return "Domyślnie ulubione ligi z wybranej daty.";
}

function emptyMatchesLabel(query: string): string {
  if (query.trim()) {
    return "Brak meczów dla daty i wyszukiwania";
  }
  return "Brak nadchodzących meczów na tę datę";
}

function emptyEventsLabel(query: string): string {
  if (query.trim()) {
    return "Brak zdarzeń dla wyszukiwania";
  }
  return "Brak zdarzeń";
}

function CatalogFilters({
  catalogDate,
  matchQuery,
  eventQuery,
  includeAllLeagues,
  hasFavoriteLeagues,
  disabled,
  onDateChange,
  onAllLeaguesChange,
  onQueryChange,
  onEventQueryChange,
}: {
  catalogDate: string;
  matchQuery: string;
  eventQuery: string;
  includeAllLeagues: boolean;
  hasFavoriteLeagues: boolean;
  disabled: boolean;
  onDateChange: (date: string) => void;
  onAllLeaguesChange: (includeAllLeagues: boolean) => void;
  onQueryChange: (query: string) => void;
  onEventQueryChange: (query: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
        <label className="flex flex-col gap-1.5 text-sm text-muted">
          {CATALOG_DATE_LABEL}
          <input
            type="date"
            value={catalogDate}
            min={getWarsawDateIso()}
            disabled={disabled}
            onChange={(event) => onDateChange(event.target.value)}
            className={FIELD_CLASS_NAME}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm text-muted">
          {MATCH_SEARCH_LABEL}
          <input
            type="search"
            value={matchQuery}
            disabled={disabled}
            onChange={(event) => onQueryChange(event.target.value)}
            autoComplete="off"
            className={FIELD_CLASS_NAME}
          />
        </label>
      </div>
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        {EVENT_SEARCH_LABEL}
        <input
          type="search"
          value={eventQuery}
          disabled={disabled}
          onChange={(event) => onEventQueryChange(event.target.value)}
          autoComplete="off"
          className={FIELD_CLASS_NAME}
        />
      </label>
      {hasFavoriteLeagues ? (
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={includeAllLeagues}
            disabled={disabled}
            onChange={(event) => onAllLeaguesChange(event.target.checked)}
            className={CATALOG_CHECKBOX_CLASS_NAME}
          />
          {ALL_LEAGUES_LABEL}
        </label>
      ) : null}
    </div>
  );
}

function MatchSelect({
  matches,
  matchId,
  emptyLabel,
  disabled,
  onMatchChange,
}: {
  matches: CatalogMatch[];
  matchId: number;
  emptyLabel: string;
  disabled: boolean;
  onMatchChange: (matchId: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-muted">
      Mecz
      <select
        value={matchId}
        disabled={disabled || matches.length === 0}
        onChange={(event) => onMatchChange(Number(event.target.value))}
        className={FIELD_CLASS_NAME}
      >
        {matches.length === 0 ? (
          <option value={0}>{emptyLabel}</option>
        ) : (
          groupCatalogMatches(matches).map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.matches.map((match) => (
                <option key={match.id} value={match.id}>
                  {catalogMatchOptionLabel(match)}
                </option>
              ))}
            </optgroup>
          ))
        )}
      </select>
    </label>
  );
}

function useVisibleEventId(
  events: CatalogMatchesResponse["events"],
  query: string,
  eventId: number,
  onEventChange: (eventId: number) => void,
): number {
  const selectedEventId = resolveCatalogEventId(events, query, eventId);
  useEffect(() => {
    if (selectedEventId !== eventId) {
      onEventChange(selectedEventId);
    }
  }, [selectedEventId, eventId, onEventChange]);
  return selectedEventId;
}

function EventSelect({
  events,
  eventId,
  emptyLabel,
  disabled,
  onEventChange,
}: {
  events: CatalogMatchesResponse["events"];
  eventId: number;
  emptyLabel: string;
  disabled: boolean;
  onEventChange: (eventId: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-muted">
      Zdarzenie
      <select
        value={eventId}
        disabled={disabled || events.length === 0}
        onChange={(event) => onEventChange(Number(event.target.value))}
        className={FIELD_CLASS_NAME}
      >
        {events.length === 0 ? (
          <option value={0}>{emptyLabel}</option>
        ) : (
          groupCatalogEvents(events).map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.events.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </optgroup>
          ))
        )}
      </select>
    </label>
  );
}
