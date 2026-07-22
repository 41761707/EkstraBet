export interface PieSegmentInput {
  id: string;
  percent: number;
}

export interface GenericPieSlice {
  id: string;
  percent: number;
  /** SVG path `d` for a donut/pie wedge; null when percent is 0. */
  path: string | null;
  /** Full-circle fill when one side is 100%. */
  isFullCircle: boolean;
}

function polarPoint(
  cx: number,
  cy: number,
  radius: number,
  angleDeg: number,
): { x: number; y: number } {
  const radians = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function describeWedge(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polarPoint(cx, cy, radius, endAngle);
  const end = polarPoint(cx, cy, radius, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return [
    `M ${cx} ${cy}`,
    `L ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
}

/**
 * Build SVG pie slices from integer percents (typically summing to 100).
 * Segment order in the input array defines clockwise drawing order.
 */
export function buildPieSlicesFromSegments(
  segments: PieSegmentInput[],
  radius = 42,
  cx = 50,
  cy = 50,
): GenericPieSlice[] {
  let angle = 0;
  const slices: GenericPieSlice[] = [];

  for (const segment of segments) {
    const percent = segment.percent;
    if (percent <= 0) {
      slices.push({
        id: segment.id,
        percent: 0,
        path: null,
        isFullCircle: false,
      });
      continue;
    }
    if (percent >= 100) {
      slices.push({
        id: segment.id,
        percent: 100,
        path: null,
        isFullCircle: true,
      });
      angle = 360;
      continue;
    }
    const sweep = (percent / 100) * 360;
    const startAngle = angle;
    const endAngle = angle + sweep;
    slices.push({
      id: segment.id,
      percent,
      path: describeWedge(cx, cy, radius, startAngle, endAngle),
      isFullCircle: false,
    });
    angle = endAngle;
  }

  return slices;
}

/**
 * Convert probabilities in [0, 1] to integer percents that sum to 100
 * (largest remainder method).
 */
export function normalizeProbabilitiesToPercents(
  probabilities: number[],
): number[] {
  if (probabilities.length === 0) {
    return [];
  }

  const clamped = probabilities.map((value) =>
    Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0,
  );
  const sum = clamped.reduce((total, value) => total + value, 0);
  if (sum <= 0) {
    return clamped.map(() => 0);
  }

  const raw = clamped.map((value) => (value / sum) * 100);
  const floors = raw.map((value) => Math.floor(value));
  const remainder = 100 - floors.reduce((total, value) => total + value, 0);
  const byFraction = raw
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((left, right) => right.fraction - left.fraction);

  const result = [...floors];
  for (let step = 0; step < remainder; step += 1) {
    const target = byFraction[step % byFraction.length];
    if (!target) {
      break;
    }
    result[target.index] += 1;
  }
  return result;
}
