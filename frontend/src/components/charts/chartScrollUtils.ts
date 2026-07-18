export type CompactScrollAlign = "start" | "end";

export function getChartPointsScrollKey(
  points: readonly { label: string }[],
): string {
  return points.map((point) => point.label).join("\0");
}

export function scrollContainerToEnd(element: HTMLElement | null): void {
  if (element === null) {
    return;
  }
  if (element.scrollWidth <= element.clientWidth) {
    return;
  }
  element.scrollLeft = element.scrollWidth - element.clientWidth;
}

export function applyCompactScrollAlign(
  element: HTMLElement | null,
  align: CompactScrollAlign,
): void {
  if (element === null) {
    return;
  }
  if (align === "end") {
    scrollContainerToEnd(element);
    return;
  }
  element.scrollLeft = 0;
}
