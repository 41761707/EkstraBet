import type { TeamFormResult } from "@/types/api";
import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";

interface TeamFormStripProps {
  form: TeamFormResult[];
}

const formColors: Record<TeamFormResult, string> = {
  W: CHART_COLOR_POSITIVE,
  WPD: "#22c55e",
  PPD: "#f97316",
  D: CHART_COLOR_DRAW,
  L: CHART_COLOR_NEGATIVE,
};

const formTitles: Record<TeamFormResult, string> = {
  W: "Wygrana",
  WPD: "Wygrana po dogrywce",
  PPD: "Przegrana po dogrywce",
  D: "Remis",
  L: "Porażka",
};

export function TeamFormStrip({ form }: TeamFormStripProps) {
  if (form.length === 0) {
    return (
      <p className="text-sm text-slate-400">Brak danych o ostatniej formie.</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {form.map((result, index) => (
        <span
          key={`${result}-${index}`}
          className="inline-flex h-7 w-7 items-center justify-center rounded text-xs font-semibold text-slate-950"
          style={{ backgroundColor: formColors[result] }}
          title={formTitles[result]}
        >
          {result}
        </span>
      ))}
    </div>
  );
}
