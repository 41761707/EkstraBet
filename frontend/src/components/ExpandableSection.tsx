import type { ReactNode } from "react";

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
      className="group rounded-xl border border-slate-700/80 bg-slate-900/50"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-base font-semibold text-sky-300 transition hover:bg-slate-800/40 [&::-webkit-details-marker]:hidden">
        <span>{title}</span>
        <span
          className="text-slate-500 transition group-open:rotate-180"
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>
      <div className="border-t border-slate-700/80 px-5 py-4 text-slate-300">
        {children}
      </div>
    </details>
  );
}
