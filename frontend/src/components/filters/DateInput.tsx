"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";

import { DateInputCalendar } from "@/components/filters/DateInputCalendar";
import {
  formatIsoDatePl,
  parseIsoDate,
} from "@/components/filters/dateInputModel";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { getWarsawDateIso } from "@/lib/date";

const DEFAULT_TRIGGER_CLASS_NAME =
  "flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg " +
  `text-left text-sm ${INPUT_CLASS_NAME}`;

/** ISO YYYY-MM-DD date field with a calendar popover instead of native typing. */
interface DateInputProps {
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
  className?: string;
  allowEmpty?: boolean;
  min?: string;
  max?: string;
}

export function DateInput({
  value,
  onChange,
  ariaLabel,
  className = DEFAULT_TRIGGER_CLASS_NAME,
  allowEmpty = true,
  min,
  max,
}: DateInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const calendarId = useId();
  const todayIso = getWarsawDateIso();
  const viewDate = parseIsoDate(value) ?? parseIsoDate(todayIso);

  useDatePickerDismiss(isOpen, rootRef, setIsOpen);

  const displayValue = value ? formatIsoDatePl(value) : "dd.mm.rrrr";

  return (
    <div ref={rootRef} className={isOpen ? "relative z-50" : "relative"}>
      <button
        type="button"
        className={className}
        aria-label={`${ariaLabel}: ${displayValue}`}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls={calendarId}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className={value ? "text-text" : "text-subtle"}>
          {displayValue}
        </span>
        <CalendarIcon />
      </button>
      {isOpen && viewDate ? (
        <DateInputCalendar
          id={calendarId}
          selectedIso={value}
          todayIso={todayIso}
          initialView={viewDate}
          min={min}
          max={max}
          allowEmpty={allowEmpty}
          onSelect={(isoDate) => {
            onChange(isoDate);
            setIsOpen(false);
          }}
          onClear={() => {
            onChange("");
            setIsOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}

function useDatePickerDismiss(
  isOpen: boolean,
  rootRef: RefObject<HTMLDivElement | null>,
  setIsOpen: (open: boolean) => void,
) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (rootRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, rootRef, setIsOpen]);
}

function CalendarIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 shrink-0 text-muted"
      aria-hidden="true"
    >
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 11h18" />
    </svg>
  );
}
