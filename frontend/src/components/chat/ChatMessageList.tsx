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
    <section className="min-h-[24rem] space-y-4 rounded-2xl border border-border bg-page/50 p-4">
      {messages.length === 0 ? (
        <div className="flex min-h-64 items-center justify-center rounded-xl border border-dashed border-border text-center text-sm text-muted">
          {emptyLabel}
        </div>
      ) : (
        messages.map((message) => (
          <article
            key={message.id}
            className={`rounded-2xl border px-4 py-3 ${
              message.role === "user"
                ? "ml-auto max-w-3xl border-accent/30 bg-accent-soft text-text"
                : "mr-auto max-w-4xl border-border bg-surface text-text"
            }`}
          >
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
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
        <div className="mr-auto max-w-3xl rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-muted">
          Krzychu analizuje pytanie i przygotowuje odpowiedź...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-danger-border bg-danger-bg px-4 py-3 text-sm text-danger-text">
          {error}
        </div>
      ) : null}
    </section>
  );
}
