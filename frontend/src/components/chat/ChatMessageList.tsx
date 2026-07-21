"use client";

import { ChatAnswerView } from "@/components/chat/ChatAnswerView";
import type { ChatMessage } from "@/types/api";

interface ChatMessageListProps {
  messages: ChatMessage[];
  emptyLabel: string;
  isLoading: boolean;
  error: string | null;
}

export function ChatMessageList({
  messages,
  emptyLabel,
  isLoading,
  error,
}: ChatMessageListProps) {
  return (
    <section className="min-h-[24rem] space-y-4 rounded-2xl border border-slate-700/80 bg-slate-950/50 p-4">
      {messages.length === 0 ? (
        <div className="flex min-h-64 items-center justify-center rounded-xl border border-dashed border-slate-700 text-center text-sm text-slate-400">
          {emptyLabel}
        </div>
      ) : (
        messages.map((message) => (
          <article
            key={message.id}
            className={`rounded-2xl border px-4 py-3 ${
              message.role === "user"
                ? "ml-auto max-w-3xl border-sky-500/30 bg-sky-950/30 text-sky-50"
                : "mr-auto max-w-4xl border-slate-700/80 bg-slate-900/80 text-slate-100"
            }`}
          >
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {message.role === "user" ? "Ty" : "Asystent"}
            </div>
            {message.answer ? (
              <ChatAnswerView answer={message.answer} />
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-6">
                {message.content}
              </p>
            )}
          </article>
        ))
      )}

      {isLoading ? (
        <div className="mr-auto max-w-3xl rounded-2xl border border-slate-700/80 bg-slate-900/80 px-4 py-3 text-sm text-slate-300">
          Krzychu analizuje pytanie i przygotowuje odpowiedź...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}
    </section>
  );
}
