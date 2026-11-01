"use client";

import { useRef, useState } from "react";

import { downloadMatchCardPng } from "@/components/matches/downloadMatchCardPng";
import { MatchCardGraphic } from "@/components/matches/MatchCardGraphic";
import type { FootballMatchCard } from "@/components/matches/matchCardModel";

const DOWNLOAD_BUTTON_CLASS =
  "rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
  "transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60";

interface MatchCardPanelProps {
  card: FootballMatchCard;
}

export function MatchCardPanel({ card }: MatchCardPanelProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function onDownload() {
    const svg = svgRef.current;
    if (!svg) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await downloadMatchCardPng(svg, card.fileName);
    } catch {
      setError("Nie udało się zapisać obrazu.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm text-muted">
            Kompaktowa grafika meczu do łatwego eksportu najważniejszych informacji.
          </p>
        </div>
        <button
          type="button"
          className={DOWNLOAD_BUTTON_CLASS}
          onClick={() => {
            void onDownload();
          }}
          disabled={isSaving}
        >
          {isSaving ? "Zapisywanie…" : "Pobierz PNG"}
        </button>
      </div>
      {error ? <p className="text-sm text-danger-text">{error}</p> : null}
      <div className="mx-auto w-full max-w-md overflow-hidden rounded-xl border border-border">
        <MatchCardGraphic card={card} svgRef={svgRef} />
      </div>
    </section>
  );
}
