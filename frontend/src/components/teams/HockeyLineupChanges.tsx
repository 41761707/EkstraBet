import {
  lineShiftLabel,
  type LineShiftMarker,
} from "@/components/teams/lineupChangeLabels";

interface LineShiftMarkProps {
  marker: LineShiftMarker;
}

export function LineShiftMark({ marker }: LineShiftMarkProps) {
  const promoted = marker.direction === "up";
  const label = lineShiftLabel(marker);
  const color = promoted ? "text-success" : "text-danger";

  return (
    <div className={`mt-1 text-sm font-semibold leading-none ${color}`} title={label}>
      <span aria-hidden="true" className="inline-flex items-center gap-0.5">
        <span>{promoted ? "↑" : "↓"}</span>
        <span>{marker.previousLine}</span>
      </span>
      <span className="sr-only">{label}</span>
    </div>
  );
}
