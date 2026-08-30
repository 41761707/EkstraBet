"use client";

import { useState } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import { formatTyperRoundLabel } from "@/lib/typerLm";
import {
  GROUP_STAGE_ROUNDS,
  KNOCKOUT_MIN_ROUND,
  parseKnockoutRoundNumber,
} from "@/lib/typerLmAdmin";
import type { LeagueRound } from "@/types/api";

interface TyperLmAdminRoundControlsProps {
  selectedRound: number;
  knockoutRounds: readonly LeagueRound[];
  knockoutRoundsError?: string;
  isSaving?: boolean;
  onSelectRound: (roundNumber: number) => void;
}

export function TyperLmAdminRoundControls({
  selectedRound,
  knockoutRounds,
  knockoutRoundsError,
  isSaving = false,
  onSelectRound,
}: TyperLmAdminRoundControlsProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-text">Runda do publikacji</h3>
      <RoundButtonRow
        selectedRound={selectedRound}
        rounds={GROUP_STAGE_ROUNDS.map((roundNumber) => ({
          round_number: roundNumber,
          round_label: formatTyperRoundLabel(roundNumber),
        }))}
        isSaving={isSaving}
        onSelectRound={onSelectRound}
      />
      <h3 className="text-sm font-medium text-text">Faza pucharowa</h3>
      <KnockoutRoundsSection
        selectedRound={selectedRound}
        knockoutRounds={knockoutRounds}
        knockoutRoundsError={knockoutRoundsError}
        isSaving={isSaving}
        onSelectRound={onSelectRound}
      />
    </div>
  );
}

interface KnockoutRoundsSectionProps {
  selectedRound: number;
  knockoutRounds: readonly LeagueRound[];
  knockoutRoundsError?: string;
  isSaving: boolean;
  onSelectRound: (roundNumber: number) => void;
}

function KnockoutRoundsSection({
  selectedRound,
  knockoutRounds,
  knockoutRoundsError,
  isSaving,
  onSelectRound,
}: KnockoutRoundsSectionProps) {
  return (
    <div className="space-y-3">
      {knockoutRoundsError ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać rund pucharowych"
          message={knockoutRoundsError}
        />
      ) : null}
      {knockoutRounds.length === 0 && knockoutRoundsError === undefined ? (
        <p className="text-sm text-muted">
          Brak zaimportowanych rund pucharowych w tym sezonie.
        </p>
      ) : null}
      {knockoutRounds.length > 0 ? (
        <RoundButtonRow
          selectedRound={selectedRound}
          rounds={knockoutRounds.map((round) => ({
            round_number: round.round_number,
            round_label: formatTyperRoundLabel(
              round.round_number,
              round.round_label,
            ),
          }))}
          isSaving={isSaving}
          onSelectRound={onSelectRound}
        />
      ) : null}
      <KnockoutRoundNumberField
        isSaving={isSaving}
        onSelectRound={onSelectRound}
      />
    </div>
  );
}

function KnockoutRoundNumberField({
  isSaving,
  onSelectRound,
}: {
  isSaving: boolean;
  onSelectRound: (roundNumber: number) => void;
}) {
  const [draft, setDraft] = useState("");

  function handleLoad() {
    if (isSaving) {
      return;
    }
    const roundNumber = parseKnockoutRoundNumber(draft);
    if (roundNumber === undefined) {
      return;
    }
    onSelectRound(roundNumber);
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex min-w-40 flex-col gap-1 text-sm text-muted">
        Numer rundy pucharowej
        <input
          type="number"
          min={KNOCKOUT_MIN_ROUND}
          value={draft}
          disabled={isSaving}
          onChange={(event) => setDraft(event.target.value)}
          className={`w-40 rounded-md ${INPUT_CLASS_NAME}`}
        />
      </label>
      <button
        type="button"
        disabled={isSaving}
        onClick={handleLoad}
        className={
          "rounded-lg border border-border bg-surface px-3 py-2 " +
          "text-sm text-text hover:bg-surface-muted disabled:opacity-50"
        }
      >
        Wczytaj rundę
      </button>
    </div>
  );
}

interface RoundButtonRowProps {
  selectedRound: number;
  rounds: readonly { round_number: number; round_label: string }[];
  isSaving: boolean;
  onSelectRound: (roundNumber: number) => void;
}

function RoundButtonRow({
  selectedRound,
  rounds,
  isSaving,
  onSelectRound,
}: RoundButtonRowProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {rounds.map((round) => {
        const isActive = round.round_number === selectedRound;
        return (
          <button
            key={round.round_number}
            type="button"
            disabled={isSaving}
            onClick={() => onSelectRound(round.round_number)}
            className={`rounded-full px-3 py-1.5 text-sm transition ${
              isActive
                ? "bg-accent text-on-accent"
                : "bg-surface-muted text-muted hover:bg-surface hover:text-text"
            } disabled:opacity-50`}
          >
            {round.round_label}
          </button>
        );
      })}
    </div>
  );
}
