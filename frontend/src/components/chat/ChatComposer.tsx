"use client";

import { FormEvent } from "react";

interface ChatComposerProps {
  draft: string;
  hint: string;
  canSend: boolean;
  isLoading: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function ChatComposer({
  draft,
  hint,
  canSend,
  isLoading,
  onDraftChange,
  onSubmit,
}: ChatComposerProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-border bg-surface p-3"
    >
      <label className="sr-only" htmlFor="chat-message">
        Wiadomość do asystenta
      </label>
      <textarea
        id="chat-message"
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        rows={3}
        placeholder="Np. który zawodnik w zespole Maroko ma najwięcej strzałów celnych w ostatnich 5 meczach?"
        className="min-h-24 w-full resize-y rounded-xl border border-border bg-page px-3 py-2 text-sm text-text outline-none transition placeholder:text-subtle focus:border-accent"
      />
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-subtle">{hint}</p>
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-muted"
        >
          {isLoading ? "Analizuję..." : "Wyślij"}
        </button>
      </div>
    </form>
  );
}
