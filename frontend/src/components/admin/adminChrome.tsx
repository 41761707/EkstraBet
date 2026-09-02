export type AdminStatusTone = "success" | "danger" | "accent" | "muted";

export const ADMIN_SECONDARY_BUTTON_CLASS =
  "rounded-md border border-border bg-surface px-3 py-1.5 text-sm " +
  "text-text hover:bg-surface-muted disabled:cursor-not-allowed " +
  "disabled:opacity-50";

export const ADMIN_DANGER_BUTTON_CLASS =
  "rounded-md border border-danger-border bg-danger-bg px-3 py-1.5 " +
  "text-sm text-danger-text disabled:cursor-not-allowed disabled:opacity-50";

interface StatusBadgeProps {
  label: string;
  tone: AdminStatusTone;
}

const TONE_CLASS: Record<AdminStatusTone, string> = {
  success: "border-success-border bg-success-bg text-success-text",
  danger: "border-danger-border bg-danger-bg text-danger-text",
  accent: "border-border bg-accent-soft text-accent-text",
  muted: "border-border bg-surface text-muted",
};

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${TONE_CLASS[tone]}`}
    >
      {label}
    </span>
  );
}
