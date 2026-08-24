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
    <section className="min-w-0 overflow-hidden rounded-xl border border-border bg-surface">
      <header className="space-y-1 px-5 py-4">
        <h2 className="text-base font-semibold text-accent-text">{title}</h2>
        {description ? (
          <p className="text-sm text-muted">{description}</p>
        ) : null}
      </header>
      <div className="min-w-0 border-t border-border px-5 py-4 text-muted">
        {children}
      </div>
    </section>
  );
}
