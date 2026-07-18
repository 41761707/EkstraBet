"use client";

import { FormEvent, useMemo, useState } from "react";
import { ChatAnswerView } from "@/components/chat/ChatAnswerView";
import type { ChatMessage, ChatResponse, ChatSportContext } from "@/types/api";

const CHAT_SPORTS: ChatSportContext[] = [
  { sport_id: 1, label: "Piłka nożna" },
  { sport_id: 2, label: "Hokej" },
];

const EXAMPLE_PROMPTS = [
  "Który zawodnik w zespole Maroko ma najwięcej strzałów celnych na bramkę w ostatnich 5 meczach?",
  "Przedstaw w formie wykresu ostatnie 5 meczów Argentyny pod kątem strzałów celnych.",
  "Pokaż tabelę ligi Ekstraklasa za sezon 2024/2025.",
  "Znajdź drużynę Legia Warszawa i pokaż jej profil dla najnowszego sezonu.",
];

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function postChat(
  messages: ChatMessage[],
  sport: ChatSportContext,
): Promise<ChatResponse> {
  const response = await fetch("/api/chat/cursor", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      sport,
      messages: messages.map((message) => ({
        role: message.role,
        content: message.content,
      })),
    }),
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(body?.detail ?? "Nie udało się uzyskać odpowiedzi czatu.");
  }

  return response.json() as Promise<ChatResponse>;
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSportId, setSelectedSportId] = useState(
    CHAT_SPORTS[0].sport_id,
  );

  const selectedSport =
    CHAT_SPORTS.find((sport) => sport.sport_id === selectedSportId) ??
    CHAT_SPORTS[0];

  const canSend = useMemo(
    () => draft.trim().length > 0 && !isLoading,
    [draft, isLoading],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSend) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: draft.trim(),
    };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setDraft("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await postChat(nextMessages, selectedSport);
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: response.answer.answerText,
          answer: response.answer,
        },
      ]);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Nieznany błąd czatu.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-700/80 bg-slate-900/50 p-5 shadow-xl shadow-slate-950/30">
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wide text-sky-300">
            Lokalny Cursor SDK
          </p>
          <h1 className="text-3xl font-bold text-white">
            Krzychu - Asystent analityczny EkstraBet
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-300">
            Zadawaj pytania po polsku o ligi, drużyny, zawodników, mecze i statystyki. Asystent na podstawie zbioru danych odpowiada na pytania dotyczące lig, statystyk i predykcji dostępnych w aplikacji.
          </p>
        </div>

        <fieldset className="mt-5 space-y-3">
          <legend className="text-sm font-semibold text-white">
            Wybierz sport dla tej rozmowy
          </legend>
          <div className="flex flex-wrap gap-3">
            {CHAT_SPORTS.map((sport) => (
              <label
                key={sport.sport_id}
                className={`cursor-pointer rounded-xl border px-4 py-2 text-sm font-medium transition ${
                  selectedSportId === sport.sport_id
                    ? "border-sky-400 bg-sky-950/60 text-sky-100"
                    : "border-slate-700 bg-slate-950/60 text-slate-300 hover:border-sky-500/50"
                }`}
              >
                <input
                  type="radio"
                  name="chat-sport"
                  value={sport.sport_id}
                  checked={selectedSportId === sport.sport_id}
                  onChange={() => {
                    setSelectedSportId(sport.sport_id);
                    setMessages([]);
                    setError(null);
                  }}
                  disabled={isLoading}
                  className="sr-only"
                />
                {sport.label}
              </label>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            Sport jest przekazywany do planera narzędzi, aby zapytania nie mieszały danych między dyscyplinami.
          </p>
        </fieldset>

        <div className="mt-4 flex flex-wrap gap-2">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setDraft(prompt)}
              className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1.5 text-xs text-slate-300 transition hover:border-sky-500/60 hover:text-sky-200"
            >
              {prompt}
            </button>
          ))}
        </div>
      </section>

      <section className="min-h-[24rem] space-y-4 rounded-2xl border border-slate-700/80 bg-slate-950/50 p-4">
        {messages.length === 0 ? (
          <div className="flex min-h-64 items-center justify-center rounded-xl border border-dashed border-slate-700 text-center text-sm text-slate-400">
            Rozmowa jest pusta. Wybrany sport: {selectedSport.label}. Zacznij od pytania o drużynę, ligę lub statystyki.
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

      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-3"
      >
        <label className="sr-only" htmlFor="chat-message">
          Wiadomość do asystenta
        </label>
        <textarea
          id="chat-message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={3}
          placeholder="Np. który zawodnik w zespole Maroko ma najwięcej strzałów celnych w ostatnich 5 meczach?"
          className="min-h-24 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-sky-500"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            Wymaga `CURSOR_API_KEY` w środowisku serwera Next.js.
          </p>
          <button
            type="submit"
            disabled={!canSend}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isLoading ? "Analizuję..." : "Wyślij"}
          </button>
        </div>
      </form>
    </div>
  );
}
