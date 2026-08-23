"use client";

import {
  ChatEngineSelector,
  ChatSportSelector,
} from "@/components/chat/ChatSelectors";
import type { ChatProvider, ChatSportContext } from "@/types/api";

interface ChatProviderOption {
  id: ChatProvider;
  label: string;
  hint: string;
}

interface ChatIntroProps {
  providerLabel: string;
  providers: ChatProviderOption[];
  selectedProvider: ChatProvider;
  providerHint: string;
  sports: ChatSportContext[];
  selectedSportId: number;
  examplePrompts: string[];
  disabled?: boolean;
  onProviderChange: (provider: ChatProvider) => void;
  onSportChange: (sportId: number) => void;
  onExampleClick: (prompt: string) => void;
}

export function ChatIntro({
  providerLabel,
  providers,
  selectedProvider,
  providerHint,
  sports,
  selectedSportId,
  examplePrompts,
  disabled = false,
  onProviderChange,
  onSportChange,
  onExampleClick,
}: ChatIntroProps) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-xl ">
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent-text">
          {providerLabel}
        </p>
        <h1 className="text-3xl font-bold text-text">
          Krzychu - Asystent analityczny EkstraBet
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-muted">
          Zadawaj pytania po polsku o ligi, drużyny, zawodników, mecze,
          statystyki, kursy i prawdopodobieństwa modeli.
        </p>
      </div>

      {providers.length > 1 ? (
        <ChatEngineSelector
          providers={providers}
          selectedProvider={selectedProvider}
          hint={providerHint}
          disabled={disabled}
          onChange={onProviderChange}
        />
      ) : null}
      <ChatSportSelector
        sports={sports}
        selectedSportId={selectedSportId}
        disabled={disabled}
        onChange={onSportChange}
      />

      <div className="mt-4 flex flex-wrap gap-2">
        {examplePrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onExampleClick(prompt)}
            className="rounded-full border border-border bg-surface-muted px-3 py-1.5 text-xs text-muted transition hover:border-accent/60 hover:text-accent-text-hover"
          >
            {prompt}
          </button>
        ))}
      </div>
    </section>
  );
}
