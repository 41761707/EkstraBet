/** Shared calendar-date helpers for Europe/Warsaw. */

const WARSAW_TIME_ZONE = "Europe/Warsaw";

const NAIVE_DATE_TIME_PATTERN =
  /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/;

function readFormatPart(
  parts: Intl.DateTimeFormatPart[],
  type: Intl.DateTimeFormatPartTypes,
): string | undefined {
  return parts.find((part) => part.type === type)?.value;
}

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

  const year = readFormatPart(parts, "year");
  const month = readFormatPart(parts, "month");
  const day = readFormatPart(parts, "day");

  if (!year || !month || !day) {
    throw new Error("Failed to format Warsaw calendar date");
  }

  return `${year}-${month}-${day}`;
}

/**
 * Return wall-clock YYYY-MM-DDTHH:mm:ss in Europe/Warsaw for an instant.
 */
export function getWarsawDateTimeIso(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: WARSAW_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(now);

  const year = readFormatPart(parts, "year");
  const month = readFormatPart(parts, "month");
  const day = readFormatPart(parts, "day");
  const hour = readFormatPart(parts, "hour");
  const minute = readFormatPart(parts, "minute");
  const second = readFormatPart(parts, "second");

  if (!year || !month || !day || !hour || !minute || !second) {
    throw new Error("Failed to format Warsaw date-time");
  }

  return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
}

/**
 * Normalize a naive API datetime to YYYY-MM-DDTHH:mm:ss for lexical compare.
 * Values are treated as Europe/Warsaw wall clock, never as UTC/host local.
 */
export function normalizeWarsawNaiveDateTime(
  value: string,
): string | null {
  const match = NAIVE_DATE_TIME_PATTERN.exec(value.trim());
  if (!match) {
    return null;
  }

  const [, year, month, day, hour = "00", minute = "00", second = "00"] =
    match;
  return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
}

/**
 * Whether a naive kick-off (Warsaw local) is at or before `now` in Warsaw.
 */
export function hasWarsawNaiveDateTimePassed(
  naiveDateTime: string,
  now: Date = new Date(),
): boolean {
  const kickoff = normalizeWarsawNaiveDateTime(naiveDateTime);
  if (!kickoff) {
    return false;
  }
  return kickoff <= getWarsawDateTimeIso(now);
}

/** Add calendar days to an ISO date string without timezone drift. */
export function addIsoCalendarDays(isoDate: string, days: number): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const utc = new Date(Date.UTC(year!, month! - 1, day!));
  utc.setUTCDate(utc.getUTCDate() + days);
  return utc.toISOString().slice(0, 10);
}
