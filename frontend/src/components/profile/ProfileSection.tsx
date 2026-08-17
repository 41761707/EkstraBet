import type { ReactNode } from "react";

interface ProfileSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export function ProfileSection({
  title,
  description,
  children,
}: ProfileSectionProps) {
  return (
    <section className="min-w-0 overflow-hidden rounded-xl border border-slate-700/80 bg-slate-900/50">
      <header className="space-y-1 px-5 py-4">
        <h2 className="text-base font-semibold text-sky-300">{title}</h2>
        {description ? (
          <p className="text-sm text-slate-400">{description}</p>
        ) : null}
      </header>
      <div className="min-w-0 border-t border-slate-700/80 px-5 py-4 text-slate-300">
        {children}
      </div>
    </section>
  );
}
