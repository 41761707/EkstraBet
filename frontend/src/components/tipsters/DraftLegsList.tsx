"use client";

import { FIELD_CLASS_NAME } from "@/components/inputStyles";
import {
  catalogEventName,
  catalogMatchTitle,
  isCombinedLeg,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import type { CatalogEvent, CatalogMatch } from "@/types/api";

interface DraftLegsListProps {
  legs: DraftCouponLeg[];
  matches: CatalogMatch[];
  events: CatalogEvent[];
  isSubmitting: boolean;
  onOddsChange: (matchId: number, odds: string) => void;
  onRemove: (matchId: number, eventId: number) => void;
}

export function DraftLegsList({
  legs,
  matches,
  events,
  isSubmitting,
  onOddsChange,
  onRemove,
}: DraftLegsListProps) {
  if (legs.length === 0) {
    return (
      <p className="text-sm text-muted">
        Wybierz mecz i event, potem wpisz kurs nogi. Combined wymaga kursu
        łączonego.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {legs.map((leg) => (
        <li
          key={leg.matchId}
          className="space-y-2 rounded-lg border border-border bg-surface-muted px-3 py-3"
        >
          <p className="text-sm font-medium text-text">
            {catalogMatchTitle(matches, leg.matchId)}
            {isCombinedLeg(leg.eventIds) ? " · Combined" : null}
          </p>
          <ul className="flex flex-wrap gap-2">
            {leg.eventIds.map((id) => (
              <li key={id}>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => onRemove(leg.matchId, id)}
                  className={
                    "rounded-md border border-border px-2 py-1 text-xs " +
                    "text-text transition hover:bg-surface-raised"
                  }
                >
                  {catalogEventName(events, id)} ×
                </button>
              </li>
            ))}
          </ul>
          <label className="flex max-w-40 flex-col gap-1.5 text-sm text-muted">
            {isCombinedLeg(leg.eventIds) ? "Kurs łączony bukmachera" : "Kurs nogi"}
            <input
              type="text"
              inputMode="decimal"
              value={leg.odds}
              disabled={isSubmitting}
              onChange={(event) => onOddsChange(leg.matchId, event.target.value)}
              className={FIELD_CLASS_NAME}
            />
          </label>
        </li>
      ))}
    </ul>
  );
}
