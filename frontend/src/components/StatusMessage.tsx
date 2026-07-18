interface StatusMessageProps {
  title: string;
  message?: string;
  variant?: "error" | "empty" | "info";
}

const variantStyles = {
  error: "border-red-500/40 bg-red-950/30 text-red-100",
  empty: "border-slate-600 bg-slate-900/60 text-slate-200",
  info: "border-sky-500/40 bg-sky-950/20 text-sky-100",
};

export function StatusMessage({
  title,
  message,
  variant = "info",
}: StatusMessageProps) {
  return (
    <div
      className={`rounded-lg border px-4 py-6 text-center ${variantStyles[variant]}`}
      role="status"
    >
      <p className="text-lg font-medium">{title}</p>
      {message ? (
        <p className="mt-2 text-sm opacity-80">{message}</p>
      ) : null}
    </div>
  );
}
