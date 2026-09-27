/**
 * Shared field chrome for text inputs, selects and date triggers.
 * Compose with layout extras (`w-full`, `pr-10`, rounding) at the call site.
 */

// Różnice layoutu (w-full, pr-10, rounded-*) zostają w konsumentach.
export const INPUT_CLASS_NAME =
  "border border-border bg-surface-muted px-3 py-2 text-text " +
  "focus:border-accent focus-visible:outline-2 " +
  "focus-visible:outline-offset-2 focus-visible:outline-focus-ring";

export const FIELD_CLASS_NAME = `w-full rounded-md ${INPUT_CLASS_NAME}`;

export const SUBMIT_BUTTON_CLASS_NAME =
  "rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
  "transition hover:bg-accent-hover disabled:cursor-not-allowed " +
  "disabled:opacity-60";
