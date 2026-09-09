"use client";

import type { ReactNode } from "react";

import {
  EXPANDABLE_SECTION_BODY_CLASS_NAME,
  EXPANDABLE_SECTION_CHEVRON_CLASS_NAME,
  EXPANDABLE_SECTION_CLASS_NAME,
  EXPANDABLE_SECTION_SUMMARY_CLASS_NAME,
} from "@/components/expandableSectionStyles";

interface ExpandableSectionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  id?: string;
  onToggle?: (open: boolean) => void;
}

export function ExpandableSection({
  title,
  children,
  defaultOpen = false,
  id,
  onToggle,
}: ExpandableSectionProps) {
  return (
    <details
      id={id}
      className={EXPANDABLE_SECTION_CLASS_NAME}
      {...expandableSectionOpenProps(defaultOpen, onToggle)}
      onToggle={
        onToggle
          ? (event) => {
              onToggle(event.currentTarget.open);
            }
          : undefined
      }
    >
      <summary className={EXPANDABLE_SECTION_SUMMARY_CLASS_NAME}>
        <span className="min-w-0 break-words">{title}</span>
        <span
          className={EXPANDABLE_SECTION_CHEVRON_CLASS_NAME}
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>
      <div className={EXPANDABLE_SECTION_BODY_CLASS_NAME}>{children}</div>
    </details>
  );
}

function expandableSectionOpenProps(
  defaultOpen: boolean,
  onToggle: ((open: boolean) => void) | undefined,
): { open?: boolean } {
  // onToggle re-renderuje rodzica; `open={defaultOpen}` wtedy zamyka expander
  if (onToggle) {
    return {};
  }
  return { open: defaultOpen };
}
