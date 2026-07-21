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
      className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-3"
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
        className="min-h-24 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-sky-500"
      />
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">{hint}</p>
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {isLoading ? "Analizuję..." : "Wyślij"}
        </button>
      </div>
    </form>
  );
}
