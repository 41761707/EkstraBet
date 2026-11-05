/** Grid, period shift and intensity for the settled-result calendar. */

import {
  formatIsoDate,
  formatMonthTitle,
  parseIsoDate,
  type CalendarDate,
} from "@/components/filters/dateInputModel";
import type { ResultCalendarBucket, ResultCalendarGrain } from "@/types/api";

/** Grain of the result calendar. Same union as the API. */
export type ResultGrain = ResultCalendarGrain;

/** One cell. `start` is null only for the blank cells that align a month. */
export interface CalendarSlot {
  start: string | null;
  bucket: ResultCalendarBucket | null;
}

const DAYS_IN_WEEK = 7;
const MONTHS_IN_YEAR = 12;
const MS_PER_DAY = 86_400_000;

interface IsoWeek {
  year: number;
  week: number;
  weekday: number;
}

/**
 * Monday-first month of `anchor`. Leading and trailing cells that fall
 * outside the month have `start: null`. Length is a multiple of 7.
 */
export function dayGrid(
  anchor: string,
  buckets: ResultCalendarBucket[],
): CalendarSlot[] {
  const { year, month } = requireCalendarDate(anchor);
  const firstDay: CalendarDate = { year, month, day: 1 };
  const leading = mondayIndex(firstDay);
  const slots: CalendarSlot[] = [];

  for (let index = 0; index < leading; index += 1) {
    slots.push(blankSlot());
  }
  for (let day = 1; day <= daysInMonth(year, month); day += 1) {
    slots.push(slotAt(formatIsoDate(year, month, day), buckets));
  }
  const trailing = (DAYS_IN_WEEK - (slots.length % DAYS_IN_WEEK)) % DAYS_IN_WEEK;
  for (let index = 0; index < trailing; index += 1) {
    slots.push(blankSlot());
  }
  return slots;
}

/**
 * Every ISO week of the ISO year of `anchor`, week 1 through the week
 * of 28 December. An empty week keeps the Monday in `start`.
 */
export function weekSlots(
  anchor: string,
  buckets: ResultCalendarBucket[],
): CalendarSlot[] {
  const isoYear = isoWeekOf(requireCalendarDate(anchor)).year;
  const lastWeek = weeksInIsoYear(isoYear);
  const slots: CalendarSlot[] = [];
  for (let week = 1; week <= lastWeek; week += 1) {
    const monday = mondayOfIsoWeek(isoYear, week);
    slots.push(slotAt(formatParts(monday), buckets));
  }
  return slots;
}

/** Twelve calendar months of the year of `anchor`. Empty months stay in place. */
export function monthSlots(
  anchor: string,
  buckets: ResultCalendarBucket[],
): CalendarSlot[] {
  const { year } = requireCalendarDate(anchor);
  const slots: CalendarSlot[] = [];
  for (let month = 1; month <= MONTHS_IN_YEAR; month += 1) {
    slots.push(slotAt(formatIsoDate(year, month, 1), buckets));
  }
  return slots;
}

/**
 * Years from the earlier of the earliest bucket and `today` through the
 * later of the latest bucket and `today`. A gap in the middle stays empty.
 */
export function yearSlots(
  buckets: ResultCalendarBucket[],
  today: string,
): CalendarSlot[] {
  const todayYear = requireCalendarDate(today).year;
  const years = buckets.map((bucket) => requireCalendarDate(bucket.start).year);
  const earliest = years.length === 0 ? todayYear : Math.min(...years);
  const latest = years.length === 0 ? todayYear : Math.max(...years);
  const startYear = Math.min(earliest, todayYear);
  const endYear = Math.max(latest, todayYear);
  const slots: CalendarSlot[] = [];
  for (let year = startYear; year <= endYear; year += 1) {
    slots.push(slotAt(formatIsoDate(year, 1, 1), buckets));
  }
  return slots;
}

/**
 * Move the viewed period. Day steps one month, week one ISO year,
 * month one calendar year. Year stays put. The day of month is kept
 * and clamped, so 31 January does not spill into March.
 */
export function shiftAnchor(
  grain: ResultGrain,
  anchor: string,
  direction: -1 | 1,
): string {
  if (grain === "year") {
    return anchor;
  }
  const parts = requireCalendarDate(anchor);
  if (grain === "day") {
    return shiftMonths(parts, direction);
  }
  if (grain === "month") {
    return shiftMonths(parts, direction * MONTHS_IN_YEAR);
  }
  return shiftIsoYear(parts, direction);
}

/**
 * Whether the next period is still allowed.
 * Day compares calendar months, week compares ISO years, month compares
 * calendar years. Year has no next period.
 */
export function canShiftForward(
  grain: ResultGrain,
  anchor: string,
  today: string,
): boolean {
  if (grain === "year") {
    return false;
  }
  const anchorDate = requireCalendarDate(anchor);
  const todayDate = requireCalendarDate(today);
  if (grain === "day") {
    return monthIndex(anchorDate) < monthIndex(todayDate);
  }
  if (grain === "month") {
    return anchorDate.year < todayDate.year;
  }
  return isoWeekOf(anchorDate).year < isoWeekOf(todayDate).year;
}

/** 0 at a zero profit or a non-positive scale, otherwise a third of `maxAbs`. */
export function intensityStep(profit: number, maxAbs: number): 0 | 1 | 2 | 3 {
  if (profit === 0 || maxAbs <= 0) {
    return 0;
  }
  const magnitude = Math.abs(profit);
  if (magnitude < maxAbs / 3) {
    return 1;
  }
  if (magnitude < (2 * maxAbs) / 3) {
    return 2;
  }
  return 3;
}

/**
 * Heading of the viewed period. Week uses the ISO year, because
 * 1 January can still belong to the previous week-year.
 */
export function periodTitle(grain: ResultGrain, anchor: string): string {
  if (grain === "year") {
    return "Wszystkie lata";
  }
  const parts = requireCalendarDate(anchor);
  if (grain === "day") {
    return formatMonthTitle(parts.year, parts.month);
  }
  if (grain === "week") {
    return String(isoWeekOf(parts).year);
  }
  return String(parts.year);
}

function requireCalendarDate(isoDate: string): CalendarDate {
  const parsed = parseIsoDate(isoDate);
  if (!parsed) {
    throw new Error(`Invalid calendar date: ${isoDate}`);
  }
  return parsed;
}

function formatParts(parts: CalendarDate): string {
  return formatIsoDate(parts.year, parts.month, parts.day);
}

function blankSlot(): CalendarSlot {
  return { start: null, bucket: null };
}

function slotAt(start: string, buckets: ResultCalendarBucket[]): CalendarSlot {
  const bucket = buckets.find((item) => item.start === start) ?? null;
  return { start, bucket };
}

function monthIndex(parts: CalendarDate): number {
  return parts.year * MONTHS_IN_YEAR + parts.month;
}

function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

function shiftMonths(parts: CalendarDate, monthDelta: number): string {
  const index = parts.year * MONTHS_IN_YEAR + (parts.month - 1) + monthDelta;
  const year = Math.floor(index / MONTHS_IN_YEAR);
  const month = index - year * MONTHS_IN_YEAR + 1;
  const day = Math.min(parts.day, daysInMonth(year, month));
  return formatIsoDate(year, month, day);
}

function shiftIsoYear(parts: CalendarDate, direction: -1 | 1): string {
  const current = isoWeekOf(parts);
  const isoYear = current.year + direction;
  const week = Math.min(current.week, weeksInIsoYear(isoYear));
  const monday = mondayOfIsoWeek(isoYear, week);
  return formatParts(addDays(monday, current.weekday - 1));
}

// Czwartek wyznacza rok ISO, tak jak date.isocalendar w Pythonie.
// 4 stycznia i 28 grudnia zawsze leżą w skrajnych tygodniach tego roku.
function isoWeekOf(parts: CalendarDate): IsoWeek {
  const weekdayIndex = mondayIndex(parts);
  const thursday = addDays(parts, 3 - weekdayIndex);
  const weekOneMonday = mondayOfIsoWeek(thursday.year, 1);
  const thisMonday = addDays(parts, -weekdayIndex);
  const week = (dayStamp(thisMonday) - dayStamp(weekOneMonday)) / DAYS_IN_WEEK + 1;
  return {
    year: thursday.year,
    week,
    weekday: weekdayIndex + 1,
  };
}

function weeksInIsoYear(isoYear: number): number {
  return isoWeekOf({ year: isoYear, month: 12, day: 28 }).week;
}

function mondayOfIsoWeek(isoYear: number, week: number): CalendarDate {
  const januaryFourth: CalendarDate = { year: isoYear, month: 1, day: 4 };
  const weekOneMonday = addDays(januaryFourth, -mondayIndex(januaryFourth));
  return addDays(weekOneMonday, (week - 1) * DAYS_IN_WEEK);
}

function mondayIndex(parts: CalendarDate): number {
  const utc = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  return (utc.getUTCDay() + 6) % DAYS_IN_WEEK;
}

function addDays(parts: CalendarDate, days: number): CalendarDate {
  const utc = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  utc.setUTCDate(utc.getUTCDate() + days);
  return {
    year: utc.getUTCFullYear(),
    month: utc.getUTCMonth() + 1,
    day: utc.getUTCDate(),
  };
}

function dayStamp(parts: CalendarDate): number {
  return Date.UTC(parts.year, parts.month - 1, parts.day) / MS_PER_DAY;
}
