type ChartSize = "compact" | "expanded";

export interface ChartBarDensityClasses {
  containerClass: string;
  columnClass: string;
  barWidthClass: string;
  barHeightClass: string;
  valueClass: string;
  labelClass: string;
  barLabelClass: string;
}

export function getChartBarDensityClasses(
  pointCount: number,
  size: ChartSize,
): ChartBarDensityClasses {
  if (size === "compact") {
    return {
      containerClass: "flex items-end gap-2",
      columnClass: "flex min-w-[3.5rem] flex-col items-center gap-2",
      barWidthClass: "w-10",
      barHeightClass: "h-40",
      valueClass: "font-semibold text-white text-xs",
      labelClass:
        "max-w-[4.5rem] text-center leading-tight text-slate-400 text-[10px]",
      barLabelClass: "font-bold text-white text-[10px]",
    };
  }

  const gapClass =
    pointCount > 28
      ? "gap-0.5"
      : pointCount > 20
        ? "gap-1"
        : pointCount > 14
          ? "gap-1.5"
          : "gap-2";
  const valueSize =
    pointCount > 28
      ? "text-[9px]"
      : pointCount > 20
        ? "text-[10px]"
        : pointCount > 14
          ? "text-xs"
          : "text-sm";
  const labelSize =
    pointCount > 28
      ? "text-[8px]"
      : pointCount > 20
        ? "text-[9px]"
        : pointCount > 14
          ? "text-[10px]"
          : "text-xs";
  const barLabelSize =
    pointCount > 20 ? "text-[8px]" : pointCount > 14 ? "text-[9px]" : "text-xs";

  return {
    containerClass: `flex w-full items-end ${gapClass}`,
    columnClass: "flex min-w-0 flex-1 flex-col items-center gap-1",
    barWidthClass: "w-full max-w-14",
    barHeightClass: pointCount > 20 ? "h-32" : "h-40",
    valueClass: `font-semibold text-white ${valueSize}`,
    labelClass: `w-full truncate text-center leading-tight text-slate-400 ${labelSize}`,
    barLabelClass: `font-bold text-white ${barLabelSize}`,
  };
}

export function getBttsBarLabel(btts: boolean, pointCount: number): string {
  if (pointCount > 24) {
    return btts ? "T" : "N";
  }
  return btts ? "TAK" : "NIE";
}
