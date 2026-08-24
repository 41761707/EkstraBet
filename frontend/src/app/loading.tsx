function HomeExpanderSkeleton({
  title,
  showContent,
}: {
  title: string;
  showContent?: boolean;
}) {
  return (
    <div
      className="rounded-xl border border-border bg-surface"
      aria-hidden="true"
    >
      <div className="flex items-center justify-between gap-3 px-5 py-4">
        <span className="text-base font-semibold text-accent-text">{title}</span>
        <span className="text-subtle">▾</span>
      </div>
      {showContent ? (
        <div className="space-y-3 border-t border-border px-5 py-4">
          <div className="flex items-end justify-between gap-3">
            <div className="h-4 w-44 animate-pulse rounded bg-skeleton" />
            <div className="h-4 w-16 animate-pulse rounded bg-skeleton" />
          </div>
          <div className="h-20 animate-pulse rounded-lg bg-skeleton" />
          <div className="h-20 animate-pulse rounded-lg bg-skeleton" />
          <div className="h-20 animate-pulse rounded-lg bg-skeleton" />
        </div>
      ) : null}
    </div>
  );
}

export default function HomeLoading() {
  return (
    <div
      className="space-y-8"
      role="status"
      aria-live="polite"
      aria-label="Ładowanie strony głównej"
    >
      <section className="space-y-3 text-center sm:text-left">
        <div className="mx-auto h-9 w-full max-w-xl animate-pulse rounded bg-skeleton sm:mx-0" />
        <div className="mx-auto h-4 w-full max-w-lg animate-pulse rounded bg-skeleton sm:mx-0" />
      </section>

      <div className="space-y-4">
        <HomeExpanderSkeleton title="Lista obsługiwanych lig" />
        <HomeExpanderSkeleton title="Dzisiejsze mecze" showContent />
      </div>
    </div>
  );
}
