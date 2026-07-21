"use client";

import { FormEvent, useMemo, useState } from "react";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { ChatIntro } from "@/components/chat/ChatIntro";
import { ChatMessageList } from "@/components/chat/ChatMessageList";
import type {
  ChatMessage,
  ChatProvider,
  ChatResponse,
  ChatSportContext,
} from "@/types/api";

const CHAT_SPORTS: ChatSportContext[] = [
  { sport_id: 1, label: "Piłka nożna" },
  { sport_id: 2, label: "Hokej" },
];

const CHAT_PROVIDERS: Array<{
  id: ChatProvider;
  label: string;
  hint: string;
}> = [
  {
    id: "openrouter",
    label: "Produkcja (OpenRouter)",
    hint: "Wymaga OPENROUTER_API_KEY po stronie serwera.",
  },
  {
    id: "cursor",
    label: "Lokalnie (Cursor SDK)",
    hint: "Wymaga CURSOR_API_KEY po stronie serwera. Prototyp wewnętrzny.",
  },
];

function isCursorProviderEnabled(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_ENABLE_CURSOR === "true";
}

function availableProviders() {
  if (isCursorProviderEnabled()) {
    return CHAT_PROVIDERS;
  }
  return CHAT_PROVIDERS.filter((provider) => provider.id !== "cursor");
}

function resolveDefaultProvider(): ChatProvider {
  const providers = availableProviders();
  const fromEnv = process.env.NEXT_PUBLIC_CHAT_DEFAULT_PROVIDER?.trim();
  if (
    (fromEnv === "cursor" || fromEnv === "openrouter") &&
    providers.some((provider) => provider.id === fromEnv)
  ) {
    return fromEnv;
  }
  return "openrouter";
}

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
  provider: ChatProvider,
): Promise<ChatResponse> {
  // OpenRouter i Cursor mają osobne endpointy — wybór GUI nie może odpalić drugiego
  const endpoint = provider === "cursor" ? "/api/chat/cursor" : "/api/chat";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      // /api/chat i tak wymusza openrouter; cursor route ignoruje provider z body
      ...(provider === "openrouter" ? { provider: "openrouter" } : {}),
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
  const [selectedProvider, setSelectedProvider] = useState<ChatProvider>(
    resolveDefaultProvider,
  );

  const providers = availableProviders();
  const selectedSport =
    CHAT_SPORTS.find((sport) => sport.sport_id === selectedSportId) ??
    CHAT_SPORTS[0];
  const providerMeta =
    providers.find((item) => item.id === selectedProvider) ?? providers[0];
  const canSend = useMemo(
    () => draft.trim().length > 0 && !isLoading,
    [draft, isLoading],
  );

  function resetConversation() {
    setMessages([]);
    setError(null);
  }

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
      const response = await postChat(
        nextMessages,
        selectedSport,
        selectedProvider,
      );
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
      <ChatIntro
        providerLabel={providerMeta.label}
        providers={providers}
        selectedProvider={selectedProvider}
        providerHint={providerMeta.hint}
        sports={CHAT_SPORTS}
        selectedSportId={selectedSportId}
        examplePrompts={EXAMPLE_PROMPTS}
        disabled={isLoading}
        onProviderChange={(provider) => {
          setSelectedProvider(provider);
          resetConversation();
        }}
        onSportChange={(sportId) => {
          setSelectedSportId(sportId);
          resetConversation();
        }}
        onExampleClick={setDraft}
      />
      <ChatMessageList
        messages={messages}
        emptyLabel={`Rozmowa jest pusta. Wybrany sport: ${selectedSport.label}. Zacznij od pytania o drużynę, ligę lub statystyki.`}
        isLoading={isLoading}
        error={error}
      />
      <ChatComposer
        draft={draft}
        hint={providerMeta.hint}
        canSend={canSend}
        isLoading={isLoading}
        onDraftChange={setDraft}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
