import type { BasketballCourtMarker } from "@/components/matches/basketballLineupModel";

interface BasketballCourtProps {
  markers: BasketballCourtMarker[];
}

const COURT_WIDTH = 50;
const COURT_HEIGHT = 47;
const MARKER_RADIUS = 2.2;
const NAME_OFFSET = 5;
const HALF_LINE_Y = 0.5;
const LANE_LEFT = 17;
const LANE_RIGHT = 33;
const FREE_THROW_LINE_Y = 28;
const FREE_THROW_CIRCLE_RADIUS = 6;
const BASKET_X = 25;
const BASKET_Y = 42;
const BACKBOARD_Y = 43.2;
const BACKBOARD_HALF_WIDTH = 3;
const RIM_RADIUS = 0.75;
const THREE_POINT_RADIUS = 23.75;
const CORNER_THREE_INSET = 3;

const COURT_FILL = "#c9a36b";
const PAINT_FILL = "#b8956a";
const LINE_STROKE = "#f8fafc";
const RIM_STROKE = "#ea580c";
const MARKER_FILL = "#0f172a";
const MARKER_TEXT = "#f8fafc";
const NAME_FILL = "#0f172a";

const CORNER_THREE_Y =
  BASKET_Y -
  Math.sqrt(
    THREE_POINT_RADIUS * THREE_POINT_RADIUS -
      (BASKET_X - CORNER_THREE_INSET) * (BASKET_X - CORNER_THREE_INSET),
  );

function threePointPath(): string {
  const rightX = COURT_WIDTH - CORNER_THREE_INSET;
  return [
    `M ${CORNER_THREE_INSET} ${COURT_HEIGHT}`,
    `L ${CORNER_THREE_INSET} ${CORNER_THREE_Y}`,
    `A ${THREE_POINT_RADIUS} ${THREE_POINT_RADIUS} 0 0 1 ${rightX} ${CORNER_THREE_Y}`,
    `L ${rightX} ${COURT_HEIGHT}`,
  ].join(" ");
}

function BasketballCourtMarkings() {
  const laneWidth = LANE_RIGHT - LANE_LEFT;
  const laneHeight = COURT_HEIGHT - FREE_THROW_LINE_Y;

  return (
    <g>
      <rect
        x={0}
        y={0}
        width={COURT_WIDTH}
        height={COURT_HEIGHT}
        fill={COURT_FILL}
        stroke={LINE_STROKE}
        strokeWidth={0.4}
      />
      <line
        x1={0}
        y1={HALF_LINE_Y}
        x2={COURT_WIDTH}
        y2={HALF_LINE_Y}
        stroke={LINE_STROKE}
        strokeWidth={0.3}
      />
      <path
        d={threePointPath()}
        fill="none"
        stroke={LINE_STROKE}
        strokeWidth={0.25}
      />
      <rect
        x={LANE_LEFT}
        y={FREE_THROW_LINE_Y}
        width={laneWidth}
        height={laneHeight}
        fill={PAINT_FILL}
        stroke={LINE_STROKE}
        strokeWidth={0.25}
      />
      <circle
        cx={BASKET_X}
        cy={FREE_THROW_LINE_Y}
        r={FREE_THROW_CIRCLE_RADIUS}
        fill="none"
        stroke={LINE_STROKE}
        strokeWidth={0.25}
      />
      <line
        x1={BASKET_X - BACKBOARD_HALF_WIDTH}
        y1={BACKBOARD_Y}
        x2={BASKET_X + BACKBOARD_HALF_WIDTH}
        y2={BACKBOARD_Y}
        stroke={LINE_STROKE}
        strokeWidth={0.45}
      />
      <circle
        cx={BASKET_X}
        cy={BASKET_Y}
        r={RIM_RADIUS}
        fill="none"
        stroke={RIM_STROKE}
        strokeWidth={0.3}
      />
    </g>
  );
}

function BasketballCourtPlayerMarker({
  marker,
}: {
  marker: BasketballCourtMarker;
}) {
  const numberLabel = marker.number === null ? "" : String(marker.number);

  return (
    <g>
      <circle
        cx={marker.x}
        cy={marker.y}
        r={MARKER_RADIUS}
        fill={MARKER_FILL}
      />
      <text
        x={marker.x}
        y={marker.y}
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
        y={marker.y + NAME_OFFSET}
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

export function BasketballCourt({ markers }: BasketballCourtProps) {
  return (
    <div className="mx-auto w-full max-w-80 overflow-visible rounded-xl border border-border bg-surface p-2">
      <svg
        viewBox={`0 0 ${COURT_WIDTH} ${COURT_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label="Ustawienie starterów na boisku"
      >
        <BasketballCourtMarkings />
        {markers.map((marker) => (
          <BasketballCourtPlayerMarker key={marker.playerId} marker={marker} />
        ))}
      </svg>
    </div>
  );
}
