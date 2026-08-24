interface LoadingSpinnerProps {
  label?: string;
}

export function LoadingSpinner({
  label = "Ładowanie danych...",
}: LoadingSpinnerProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16"
      role="status"
      aria-live="polite"
    >
      <div
        className="h-10 w-10 animate-spin rounded-full border-4 border-accent/30 border-t-accent"
        aria-hidden="true"
      />
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}
