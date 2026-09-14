import type { HockeyRinkMarker } from "@/components/matches/hockeyLineupModel";

interface HockeyRinkProps {
  markers: HockeyRinkMarker[];
}

const RINK_WIDTH = 40;
const RINK_HEIGHT = 60;
const MARKER_RADIUS = 2.2;
// Streamlit dawało offset 7 pod koszulką JPG; tu małe kółko, plan każe y-5.
const NAME_OFFSET = 5;
const CENTER_X = 20;
const CENTER_Y = 30;
const GOAL_CREASE_RADIUS = 2.5;
const ZONE_CIRCLE_RADIUS = 4;
const ZONE_DOT_RADIUS = 0.25;
const CENTER_CIRCLE_RADIUS = 5;
const CENTER_DOT_RADIUS = 0.5;

const RINK_FILL = "#f8fafc";
const RINK_BOARD = "#1e3a5f";
const LINE_RED = "#dc2626";
const LINE_BLUE = "#2563eb";
const CREASE_FILL = "#bfdbfe";
const MARKER_FILL = "#0f172a";
const MARKER_TEXT = "#f8fafc";
const NAME_FILL = "#0f172a";

const ZONE_FACEOFF_CENTERS: readonly [number, number][] = [
  [7, 10],
  [33, 10],
  [7, 50],
  [33, 50],
];

// Plotly y rośnie w górę; SVG ma y w dół — odwracamy, żeby G został na dole.
function toSvgY(plotlyY: number): number {
  return RINK_HEIGHT - plotlyY;
}

function creasePath(plotlyGoalY: number, sweepFlag: 0 | 1): string {
  const svgY = toSvgY(plotlyGoalY);
  const radius = GOAL_CREASE_RADIUS;
  const startX = CENTER_X - radius;
  const endX = CENTER_X + radius;
  return `M ${startX} ${svgY} A ${radius} ${radius} 0 0 ${sweepFlag} ${endX} ${svgY} Z`;
}

function HockeyRinkMarkings() {
  const centerSvgY = toSvgY(CENTER_Y);

  return (
    <g>
      <rect
        x={0}
        y={0}
        width={RINK_WIDTH}
        height={RINK_HEIGHT}
        fill={RINK_FILL}
        stroke={RINK_BOARD}
        strokeWidth={0.4}
      />
      <line
        x1={0}
        y1={centerSvgY}
        x2={RINK_WIDTH}
        y2={centerSvgY}
        stroke={LINE_RED}
        strokeWidth={0.35}
      />
      <line
        x1={0}
        y1={toSvgY(20)}
        x2={RINK_WIDTH}
        y2={toSvgY(20)}
        stroke={LINE_BLUE}
        strokeWidth={0.25}
      />
      <line
        x1={0}
        y1={toSvgY(40)}
        x2={RINK_WIDTH}
        y2={toSvgY(40)}
        stroke={LINE_BLUE}
        strokeWidth={0.25}
      />
      <line
        x1={0}
        y1={toSvgY(5)}
        x2={RINK_WIDTH}
        y2={toSvgY(5)}
        stroke={LINE_RED}
        strokeWidth={0.25}
      />
      <line
        x1={0}
        y1={toSvgY(55)}
        x2={RINK_WIDTH}
        y2={toSvgY(55)}
        stroke={LINE_RED}
        strokeWidth={0.25}
      />
      <circle
        cx={CENTER_X}
        cy={centerSvgY}
        r={CENTER_CIRCLE_RADIUS}
        fill="none"
        stroke={LINE_BLUE}
        strokeWidth={0.25}
      />
      <circle
        cx={CENTER_X}
        cy={centerSvgY}
        r={CENTER_DOT_RADIUS}
        fill={LINE_RED}
      />
      {ZONE_FACEOFF_CENTERS.map(([x, y]) => (
        <g key={`${x}-${y}`}>
          <circle
            cx={x}
            cy={toSvgY(y)}
            r={ZONE_CIRCLE_RADIUS}
            fill="none"
            stroke={LINE_RED}
            strokeWidth={0.2}
          />
          <circle cx={x} cy={toSvgY(y)} r={ZONE_DOT_RADIUS} fill={LINE_RED} />
        </g>
      ))}
      <path
        d={creasePath(5, 0)}
        fill={CREASE_FILL}
        stroke={LINE_BLUE}
        strokeWidth={0.25}
      />
      <path
        d={creasePath(55, 1)}
        fill={CREASE_FILL}
        stroke={LINE_BLUE}
        strokeWidth={0.25}
      />
    </g>
  );
}

function HockeyRinkPlayerMarker({ marker }: { marker: HockeyRinkMarker }) {
  const svgY = toSvgY(marker.y);
  const numberLabel = marker.number === null ? "" : String(marker.number);

  return (
    <g>
      <circle
        cx={marker.x}
        cy={svgY}
        r={MARKER_RADIUS}
        fill={MARKER_FILL}
      />
      <text
        x={marker.x}
        y={svgY}
        textAnchor="middle"
        dominantBaseline="central"
        fill={MARKER_TEXT}
        fontSize={2}
        fontWeight={700}
      >
        {numberLabel}
      </text>
      <text
        x={marker.x}
        y={svgY + NAME_OFFSET}
        textAnchor="middle"
        dominantBaseline="hanging"
        fill={NAME_FILL}
        fontSize={1.8}
      >
        {marker.name}
      </text>
    </g>
  );
}

export function HockeyRink({ markers }: HockeyRinkProps) {
  return (
    <div className="mx-auto w-full max-w-80 overflow-visible rounded-xl border border-border bg-surface p-2">
      <svg
        viewBox={`0 0 ${RINK_WIDTH} ${RINK_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label="Ustawienie zawodników na lodowisku"
      >
        <HockeyRinkMarkings />
        {markers.map((marker) => (
          <HockeyRinkPlayerMarker key={marker.playerId} marker={marker} />
        ))}
      </svg>
    </div>
  );
}
