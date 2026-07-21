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
    <section className="rounded-2xl border border-slate-700/80 bg-slate-900/50 p-5 shadow-xl shadow-slate-950/30">
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-sky-300">
          {providerLabel}
        </p>
        <h1 className="text-3xl font-bold text-white">
          Krzychu - Asystent analityczny EkstraBet
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-300">
          Zadawaj pytania po polsku o ligi, drużyny, zawodników, mecze i
          statystyki. Asystent na podstawie zbioru danych odpowiada na pytania
          dotyczące lig, statystyk i predykcji dostępnych w aplikacji.
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
            className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1.5 text-xs text-slate-300 transition hover:border-sky-500/60 hover:text-sky-200"
          >
            {prompt}
          </button>
        ))}
      </div>
    </section>
  );
}
