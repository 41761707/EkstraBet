import type { TeamFormResult } from "@/types/api";
import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_OVERTIME_LOSS,
  CHART_COLOR_OVERTIME_WIN,
  CHART_COLOR_POSITIVE,
  CHART_LABEL_ON_FILL,
} from "@/lib/chartColors";

interface TeamFormStripProps {
  form: TeamFormResult[];
}

const formColors: Record<TeamFormResult, string> = {
  W: CHART_COLOR_POSITIVE,
  WPD: CHART_COLOR_OVERTIME_WIN,
  PPD: CHART_COLOR_OVERTIME_LOSS,
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
      <p className="text-sm text-muted">Brak danych o ostatnich meczach.</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {form.map((result, index) => (
        <span
          key={`${result}-${index}`}
          className="inline-flex h-7 w-7 items-center justify-center rounded text-xs font-semibold"
          style={{
            backgroundColor: formColors[result],
            color: CHART_LABEL_ON_FILL,
          }}
          title={formTitles[result]}
        >
          {result}
        </span>
      ))}
    </div>
  );
}
