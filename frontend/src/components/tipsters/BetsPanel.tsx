import type { ReactNode } from "react";

interface BetsPanelProps {
  title: string;
  description?: string;
  children: ReactNode;
}

/** Karta głównej sekcji na stronie zakładów. */
export function BetsPanel({ title, description, children }: BetsPanelProps) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface">
      <header className="border-b border-border bg-surface-muted px-5 py-4">
        <h2 className="text-lg font-semibold text-text">{title}</h2>
        {description ? (
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">
            {description}
          </p>
        ) : null}
      </header>
      <div className="space-y-4 px-5 py-5">{children}</div>
    </section>
  );
}

interface BetsSubsectionProps {
  title: string;
  description?: string;
  divided?: boolean;
  children: ReactNode;
}

/** Blok wewnątrz karty, oddzielony kreską od poprzedniego. */
export function BetsSubsection({
  title,
  description,
  divided = false,
  children,
}: BetsSubsectionProps) {
  const className = divided
    ? "space-y-3 border-t border-border pt-5"
    : "space-y-3";
  return (
    <div className={className}>
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-text">{title}</h3>
        {description ? (
          <p className="max-w-3xl text-sm leading-relaxed text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {children}
    </div>
  );
}
