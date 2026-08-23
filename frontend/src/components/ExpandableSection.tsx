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
}

export function ExpandableSection({
  title,
  children,
  defaultOpen = false,
  id,
}: ExpandableSectionProps) {
  return (
    <details
      id={id}
      open={defaultOpen}
      className={EXPANDABLE_SECTION_CLASS_NAME}
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
