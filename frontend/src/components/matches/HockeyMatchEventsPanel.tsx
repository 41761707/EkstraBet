"use client";

import {
  groupHockeyEventsByPeriod,
  hockeyEventSecondaryText,
  type HockeyEventPeriodGroup,
} from "@/components/matches/hockeyEventsModel";
import { StatusMessage } from "@/components/StatusMessage";
import type { HockeyMatchEvent } from "@/types/api";

interface HockeyMatchEventsPanelProps {
  events: HockeyMatchEvent[];
  homeTeamName: string;
  awayTeamName: string;
}

function EventBadges({ event }: { event: HockeyMatchEvent }) {
  if (!event.is_power_play && !event.is_empty_net) {
    return null;
  }

  return (
    <span className="ml-2 inline-flex gap-1 align-middle">
      {event.is_power_play ? (
        <span className="rounded border border-accent/40 bg-accent-soft px-1.5 py-0.5 text-xs font-medium text-accent-text">
          PP
        </span>
      ) : null}
      {event.is_empty_net ? (
        <span className="rounded border border-success-border bg-success-bg px-1.5 py-0.5 text-xs font-medium text-success-text">
          EN
        </span>
      ) : null}
    </span>
  );
}

function EventCard({ event }: { event: HockeyMatchEvent }) {
  const timeLabel = event.event_time || "—";

  return (
    <article className="rounded-xl border border-border bg-surface-raised p-3 text-center shadow-sm">
      <h4 className="text-sm font-semibold text-text">
        {timeLabel} ({event.event_name})
        <EventBadges event={event} />
      </h4>
      <p className="mt-1 text-sm text-muted">
        {hockeyEventSecondaryText(event)}
      </p>
    </article>
  );
}

function PeriodEvents({
  group,
  homeTeamName,
  awayTeamName,
}: {
  group: HockeyEventPeriodGroup;
  homeTeamName: string;
  awayTeamName: string;
}) {
  return (
    <section className="space-y-3">
      <h3 className="text-center text-lg font-semibold text-text">
        {group.label}
      </h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <p className="text-center font-medium text-text">{homeTeamName}</p>
        <p className="text-center font-medium text-text">{awayTeamName}</p>
      </div>
      <div className="grid grid-cols-2 items-stretch gap-3">
        {group.events.map((event) => (
          <EventRow key={event.id} event={event} />
        ))}
      </div>
    </section>
  );
}

function EventRow({ event }: { event: HockeyMatchEvent }) {
  const card = <EventCard event={event} />;
  return (
    <div className="contents">
      {event.side === "home" ? card : <div aria-hidden="true" />}
      {event.side === "away" ? card : <div aria-hidden="true" />}
    </div>
  );
}

export function HockeyMatchEventsPanel({
  events,
  homeTeamName,
  awayTeamName,
}: HockeyMatchEventsPanelProps) {
  const groups = groupHockeyEventsByPeriod(events);
  if (groups.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak zdarzeń meczowych"
        message="Przebieg tego meczu nie jest jeszcze dostępny."
      />
    );
  }

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <PeriodEvents
          key={group.period}
          group={group}
          homeTeamName={homeTeamName}
          awayTeamName={awayTeamName}
        />
      ))}
    </div>
  );
}
