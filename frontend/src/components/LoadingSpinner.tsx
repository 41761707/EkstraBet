interface LoadingSpinnerProps {
  label?: string;
}

export function LoadingSpinner({
  label = "Loading data...",
}: LoadingSpinnerProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16"
      role="status"
      aria-live="polite"
    >
      <div
        className="h-10 w-10 animate-spin rounded-full border-4 border-sky-400/30 border-t-sky-400"
        aria-hidden="true"
      />
      <p className="text-sm text-slate-300">{label}</p>
    </div>
  );
}
