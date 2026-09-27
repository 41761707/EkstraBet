"use client";

import {
  catalogEventGroupLabel,
  catalogEventName,
  catalogMatchTitle,
  COMBINED_SELECTION_LABEL,
  isCombinedLeg,
  slipKickoffParts,
  type DraftCouponLeg,
  type SlipKickoffParts,
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

const ODDS_INPUT_CLASS_NAME =
  "w-20 rounded-lg border border-border px-2 py-1.5 text-right text-base " +
  "font-semibold tabular-nums text-text focus:border-accent " +
  "disabled:cursor-not-allowed disabled:opacity-60";

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
      <p className="rounded-lg border border-dashed border-border px-3 py-4 text-sm text-muted">
        Na kuponie nie ma jeszcze zdarzeń.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {legs.map((leg) => (
        <DraftLegCard
          key={leg.matchId}
          leg={leg}
          matches={matches}
          events={events}
          isSubmitting={isSubmitting}
          onOddsChange={onOddsChange}
          onRemove={onRemove}
        />
      ))}
    </ul>
  );
}

interface DraftLegCardProps {
  leg: DraftCouponLeg;
  matches: CatalogMatch[];
  events: CatalogEvent[];
  isSubmitting: boolean;
  onOddsChange: (matchId: number, odds: string) => void;
  onRemove: (matchId: number, eventId: number) => void;
}

function DraftLegCard({
  leg,
  matches,
  events,
  isSubmitting,
  onOddsChange,
  onRemove,
}: DraftLegCardProps) {
  const match = matches.find((item) => item.id === leg.matchId) ?? null;
  const combined = isCombinedLeg(leg.eventIds);
  const kickoff = slipKickoffParts(match?.game_date ?? null);

  return (
    <li className="flex overflow-hidden rounded-xl border border-border bg-surface">
      <div className="w-1 shrink-0 bg-accent" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <DraftLegHeader
          title={catalogMatchTitle(matches, leg.matchId)}
          leagueName={match?.league_name ?? null}
          kickoff={kickoff}
          isCombined={combined}
        />
        <ul className="divide-y divide-border">
          {leg.eventIds.map((eventId) => (
            <DraftSelectionRow
              key={eventId}
              eventId={eventId}
              events={events}
              isSubmitting={isSubmitting}
              showOdds={!combined}
              odds={leg.odds}
              onOddsChange={(odds) => onOddsChange(leg.matchId, odds)}
              onRemove={() => onRemove(leg.matchId, eventId)}
            />
          ))}
        </ul>
        {combined ? (
          <CombinedOddsRow
            value={leg.odds}
            disabled={isSubmitting}
            onChange={(odds) => onOddsChange(leg.matchId, odds)}
          />
        ) : null}
      </div>
    </li>
  );
}

interface DraftLegHeaderProps {
  title: string;
  leagueName: string | null;
  kickoff: SlipKickoffParts | null;
  isCombined: boolean;
}

function DraftLegHeader({
  title,
  leagueName,
  kickoff,
  isCombined,
}: DraftLegHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border bg-surface-muted px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-text">{title}</p>
        <DraftLegMeta leagueName={leagueName} isCombined={isCombined} />
      </div>
      {kickoff ? (
        <div className="shrink-0 text-right">
          <p className="text-sm font-semibold tabular-nums text-text">
            {kickoff.timeLabel}
          </p>
          <p className="text-xs text-muted">{kickoff.dayLabel}</p>
        </div>
      ) : null}
    </div>
  );
}

function DraftLegMeta({
  leagueName,
  isCombined,
}: {
  leagueName: string | null;
  isCombined: boolean;
}) {
  if (!leagueName && !isCombined) {
    return null;
  }
  return (
    <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
      {leagueName ? <span className="truncate">{leagueName}</span> : null}
      {isCombined ? <SelectionBadge /> : null}
    </p>
  );
}

interface DraftSelectionRowProps {
  eventId: number;
  events: CatalogEvent[];
  isSubmitting: boolean;
  showOdds: boolean;
  odds: string;
  onOddsChange: (odds: string) => void;
  onRemove: () => void;
}

function DraftSelectionRow({
  eventId,
  events,
  isSubmitting,
  showOdds,
  odds,
  onOddsChange,
  onRemove,
}: DraftSelectionRowProps) {
  const event = events.find((item) => item.id === eventId) ?? null;
  const name = event?.name ?? catalogEventName(events, eventId);
  const market = event ? catalogEventGroupLabel(event) : null;

  return (
    <li className="flex flex-wrap items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text">{name}</p>
        {market ? <p className="text-xs text-muted">{market}</p> : null}
      </div>
      {showOdds ? (
        <DraftOddsField
          label="Kurs"
          value={odds}
          tone="muted"
          disabled={isSubmitting}
          onChange={onOddsChange}
        />
      ) : null}
      <RemoveSelectionButton
        label={name}
        disabled={isSubmitting}
        onRemove={onRemove}
      />
    </li>
  );
}

interface DraftOddsFieldProps {
  label: string;
  value: string;
  tone: "muted" | "surface";
  disabled: boolean;
  onChange: (odds: string) => void;
}

function DraftOddsField({
  label,
  value,
  tone,
  disabled,
  onChange,
}: DraftOddsFieldProps) {
  const background = tone === "muted" ? "bg-surface-muted" : "bg-surface";
  return (
    <input
      type="text"
      inputMode="decimal"
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={`${ODDS_INPUT_CLASS_NAME} ${background}`}
    />
  );
}

function CombinedOddsRow({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (odds: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-t border-border bg-surface-muted px-4 py-3">
      <span className="text-sm text-muted" aria-hidden="true">
        Kurs łączony
      </span>
      <DraftOddsField
        label="Kurs łączony"
        value={value}
        tone="surface"
        disabled={disabled}
        onChange={onChange}
      />
    </div>
  );
}

function RemoveSelectionButton({
  label,
  disabled,
  onRemove,
}: {
  label: string;
  disabled: boolean;
  onRemove: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onRemove}
      aria-label={`Usuń ${label} z kuponu`}
      className={
        "rounded-lg p-2 text-muted transition hover:bg-danger-bg " +
        "hover:text-danger-text disabled:cursor-not-allowed disabled:opacity-60"
      }
    >
      <RemoveIcon />
    </button>
  );
}

function RemoveIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 7h16M9 7V5h6v2M7 7l1 13h8l1-13M10 11v6M14 11v6"
      />
    </svg>
  );
}

function SelectionBadge() {
  return (
    <span className="rounded-md bg-accent-soft px-1.5 py-0.5 font-medium text-accent-text">
      {COMBINED_SELECTION_LABEL}
    </span>
  );
}
