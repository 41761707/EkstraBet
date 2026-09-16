import type { HockeyMatchEvent } from "@/types/api";

export const HOCKEY_EVENT_PERIODS = [
  { period: 1, label: "Tercja 1" },
  { period: 2, label: "Tercja 2" },
  { period: 3, label: "Tercja 3" },
  { period: 4, label: "Dogrywka" },
  { period: 5, label: "Rzuty karne" },
] as const;

export interface HockeyEventPeriodGroup {
  period: number;
  label: string;
  events: HockeyMatchEvent[];
}

export function groupHockeyEventsByPeriod(
  events: HockeyMatchEvent[],
): HockeyEventPeriodGroup[] {
  return HOCKEY_EVENT_PERIODS.flatMap(({ period, label }) => {
    const periodEvents = events.filter((event) => event.period === period);
    if (periodEvents.length === 0) {
      return [];
    }
    return [{ period, label, events: periodEvents }];
  });
}

export function hockeyEventSecondaryText(event: HockeyMatchEvent): string {
  if (event.description) {
    return `${event.player_name} (${event.description})`;
  }
  return event.player_name;
}
