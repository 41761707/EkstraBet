interface StatusMessageProps {
  title: string;
  message?: string;
  variant?: "error" | "empty" | "info";
}

const variantStyles = {
  error: "border-danger-border bg-danger-bg text-danger-text",
  empty: "border-border bg-surface text-text",
  info: "border-info-border bg-info-bg text-info-text",
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
