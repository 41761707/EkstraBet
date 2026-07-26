/** Shared calendar-date helpers for Europe/Warsaw. */

const WARSAW_TIME_ZONE = "Europe/Warsaw";

/**
 * Return the calendar date YYYY-MM-DD in Europe/Warsaw.
 * Uses formatToParts so UTC midnight rollover does not shift the day.
 */
export function getWarsawDateIso(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: WARSAW_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);

  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const day = parts.find((part) => part.type === "day")?.value;

  if (!year || !month || !day) {
    throw new Error("Failed to format Warsaw calendar date");
  }

  return `${year}-${month}-${day}`;
}

/** Add calendar days to an ISO date string without timezone drift. */
export function addIsoCalendarDays(isoDate: string, days: number): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const utc = new Date(Date.UTC(year!, month! - 1, day!));
  utc.setUTCDate(utc.getUTCDate() + days);
  return utc.toISOString().slice(0, 10);
}
