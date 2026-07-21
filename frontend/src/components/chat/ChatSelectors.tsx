"use client";

import type { ChatProvider, ChatSportContext } from "@/types/api";

interface ChatProviderOption {
  id: ChatProvider;
  label: string;
}

interface ChatEngineSelectorProps {
  providers: ChatProviderOption[];
  selectedProvider: ChatProvider;
  hint: string;
  disabled?: boolean;
  onChange: (provider: ChatProvider) => void;
}

export function ChatEngineSelector({
  providers,
  selectedProvider,
  hint,
  disabled = false,
  onChange,
}: ChatEngineSelectorProps) {
  return (
    <fieldset className="mt-5 space-y-3">
      <legend className="text-sm font-semibold text-white">
        Tryb silnika LLM
      </legend>
      <div className="flex flex-wrap gap-3">
        {providers.map((provider) => (
          <label
            key={provider.id}
            className={`cursor-pointer rounded-xl border px-4 py-2 text-sm font-medium transition ${
              selectedProvider === provider.id
                ? "border-sky-400 bg-sky-950/60 text-sky-100"
                : "border-slate-700 bg-slate-950/60 text-slate-300 hover:border-sky-500/50"
            }`}
          >
            <input
              type="radio"
              name="chat-provider"
              value={provider.id}
              checked={selectedProvider === provider.id}
              onChange={() => onChange(provider.id)}
              disabled={disabled}
              className="sr-only"
            />
            {provider.label}
          </label>
        ))}
      </div>
      <p className="text-xs text-slate-500">{hint}</p>
    </fieldset>
  );
}

interface ChatSportSelectorProps {
  sports: ChatSportContext[];
  selectedSportId: number;
  disabled?: boolean;
  onChange: (sportId: number) => void;
}

export function ChatSportSelector({
  sports,
  selectedSportId,
  disabled = false,
  onChange,
}: ChatSportSelectorProps) {
  return (
    <fieldset className="mt-5 space-y-3">
      <legend className="text-sm font-semibold text-white">
        Wybierz sport dla tej rozmowy
      </legend>
      <div className="flex flex-wrap gap-3">
        {sports.map((sport) => (
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
              onChange={() => onChange(sport.sport_id)}
              disabled={disabled}
              className="sr-only"
            />
            {sport.label}
          </label>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        Sport jest przekazywany do planera narzędzi, aby zapytania nie mieszały
        danych między dyscyplinami.
      </p>
    </fieldset>
  );
}
