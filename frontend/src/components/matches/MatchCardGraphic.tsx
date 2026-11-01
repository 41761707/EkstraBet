import type { Ref } from "react";

import {
  layoutMatchCard,
  MATCH_CARD_INNER_LEFT,
  MATCH_CARD_INNER_WIDTH,
  MATCH_CARD_METRICS,
  matchCardNameFontSize,
} from "@/components/matches/matchCardLayout";
import {
  matchCardHasProbabilities,
  type FootballMatchCard,
  type MatchCardForm,
  type MatchCardFormRow,
  type MatchCardHeadToHeadRate,
  type MatchCardMeetingRow,
  type MatchCardSegment,
  type MatchCardShare,
} from "@/components/matches/matchCardModel";
import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_NEUTRAL,
  CHART_COLOR_POSITIVE,
  CHART_LABEL_ON_FILL,
} from "@/lib/chartColors";
import type { TeamFormResult } from "@/types/api";

/**
 * Paleta jest wpisana na sztywno: PNG wychodzi poza motyw aplikacji
 * i ma zostać ciemny po zapisaniu.
 */
const CARD_BG = "#0b1120";
// 10% ciemniej niż #1a2744, nadal jaśniej niż plansza.
const PANEL_BG = "#17233d";
const PANEL_BORDER = "#2d3f5c";
const ROW_DIVIDER = "#2d3f5c";
const ROW_DIVIDER_WIDTH = 2;
const TEXT = "#e2e8f0";
const MUTED = "#94a3b8";
const SUBTLE = "#7b8ea6";
const ACCENT = "#7dd3fc";
const STAT_BG = "#243656";
const STRIPE = "#0284c7";
const FORM_BADGE_X = 200;
const FORM_HOME_X = 230;
const FORM_SCORE_X = 536;
const FORM_AWAY_X = 584;
const FORM_BTTS_X = 886;
const FORM_OVER_X = 958;
const H2H_HOME_X = FORM_HOME_X;
const FONT = "Segoe UI, Arial, sans-serif";

const TONE_FILL: Record<MatchCardSegment["tone"], string> = {
  home: CHART_COLOR_POSITIVE,
  draw: CHART_COLOR_DRAW,
  away: CHART_COLOR_NEGATIVE,
};

interface MatchCardGraphicProps {
  card: FootballMatchCard;
  svgRef?: Ref<SVGSVGElement>;
}

export function MatchCardGraphic({ card, svgRef }: MatchCardGraphicProps) {
  const frame = layoutMatchCard(card);
  const title = `${card.homeTeamName} — ${card.awayTeamName}`;
  return (
    <svg
      ref={svgRef}
      xmlns="http://www.w3.org/2000/svg"
      width={frame.width}
      height={frame.height}
      viewBox={`0 0 ${frame.width} ${frame.height}`}
      className="block h-auto w-full"
      role="img"
      aria-label={title}
      fontFamily={FONT}
    >
      <title>{title}</title>
      <rect width={frame.width} height={frame.height} fill={CARD_BG} />
      <rect width={frame.width} height={8} fill={STRIPE} />
      <CardHeader card={card} />
      <ProbabilitySection
        card={card}
        y={frame.probabilitiesY}
        height={frame.probabilitiesHeight}
      />
      <HeadToHeadSection
        card={card}
        y={frame.headToHeadY}
        height={frame.headToHeadHeight}
      />
      <FormSection
        form={card.homeForm}
        y={frame.homeFormY}
        height={frame.homeFormHeight}
      />
      <FormSection
        form={card.awayForm}
        y={frame.awayFormY}
        height={frame.awayFormHeight}
      />
      <CardText
        x={frame.width / 2}
        y={frame.height - 36}
        size={26}
        fill={SUBTLE}
        anchor="middle"
      >
        EkstraBet
      </CardText>
    </svg>
  );
}

function CardHeader({ card }: { card: FootballMatchCard }) {
  const center = MATCH_CARD_METRICS.width / 2;
  return (
    <g>
      <CardText x={center} y={78} size={32} fill={ACCENT} weight={700} anchor="middle">
        {card.leagueName}
      </CardText>
      <CardText x={center} y={122} size={28} fill={MUTED} anchor="middle">
        {card.metaLabel}
      </CardText>
      <CardText
        x={center}
        y={206}
        size={matchCardNameFontSize(card.homeTeamName)}
        fill={TEXT}
        weight={700}
        anchor="middle"
      >
        {card.homeTeamName}
      </CardText>
      <CardText x={center} y={268} size={26} fill={SUBTLE} anchor="middle">
        vs
      </CardText>
      <CardText
        x={center}
        y={340}
        size={matchCardNameFontSize(card.awayTeamName)}
        fill={TEXT}
        weight={700}
        anchor="middle"
      >
        {card.awayTeamName}
      </CardText>
    </g>
  );
}

function ProbabilitySection({
  card,
  y,
  height,
}: {
  card: FootballMatchCard;
  y: number;
  height: number;
}) {
  return (
    <g>
      <Panel y={y} height={height} />
      {matchCardHasProbabilities(card) ? (
        <ProbabilityBody card={card} y={y} />
      ) : (
        <CardText
          x={MATCH_CARD_METRICS.width / 2}
          y={y + height / 2}
          size={32}
          fill={MUTED}
          anchor="middle"
        >
          Brak zapisanych predykcji
        </CardText>
      )}
    </g>
  );
}

function ProbabilityBody({ card, y }: { card: FootballMatchCard; y: number }) {
  let cursor = y + MATCH_CARD_METRICS.probPad;
  const titleY = cursor + 22;
  cursor += MATCH_CARD_METRICS.probTitle;
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={titleY} size={36} fill={TEXT} weight={700}>
        Prawdopodobieństwa
      </CardText>
      {card.result ? (
        <ResultBlock y={cursor} segments={card.result} />
      ) : null}
      {card.btts ? (
        <ShareBlock
          y={cursor + (card.result ? MATCH_CARD_METRICS.probBlock : 0)}
          title="Obie strzelą"
          share={card.btts}
          clipId="match-card-btts"
        />
      ) : null}
      {card.overUnder ? (
        <ShareBlock
          y={overUnderY(card, cursor)}
          title="Powyżej 2.5"
          share={card.overUnder}
          clipId="match-card-over"
        />
      ) : null}
      {card.topScores.length > 0 ? (
        <ScoreChips y={scoresY(card, cursor)} scores={card.topScores} />
      ) : null}
    </g>
  );
}

function overUnderY(card: FootballMatchCard, cursor: number): number {
  const earlier = (card.result ? 1 : 0) + (card.btts ? 1 : 0);
  return cursor + earlier * MATCH_CARD_METRICS.probBlock;
}

function scoresY(card: FootballMatchCard, cursor: number): number {
  const blocks = [card.result, card.btts, card.overUnder].filter(Boolean).length;
  return cursor + blocks * MATCH_CARD_METRICS.probBlock;
}

function ResultBlock({
  y,
  segments,
}: {
  y: number;
  segments: MatchCardSegment[];
}) {
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 18} size={28} fill={MUTED}>
        Wynik
      </CardText>
      <TripleBar y={y + 44} segments={segments} />
      {segments.map((segment, index) => (
        <CardText
          key={segment.tone}
          x={columnCenter(index, segments.length)}
          y={y + 112}
          size={30}
          fill={TONE_FILL[segment.tone]}
          weight={700}
          anchor="middle"
        >
          {`${segment.label} ${segment.percentLabel}`}
        </CardText>
      ))}
    </g>
  );
}

function ShareBlock({
  y,
  title,
  share,
  clipId,
}: {
  y: number;
  title: string;
  share: MatchCardShare;
  clipId: string;
}) {
  const right = MATCH_CARD_INNER_LEFT + MATCH_CARD_INNER_WIDTH;
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 18} size={28} fill={MUTED}>
        {title}
      </CardText>
      <ShareBar y={y + 44} share={share} clipId={clipId} />
      <CardText
        x={MATCH_CARD_INNER_LEFT}
        y={y + 112}
        size={30}
        fill={CHART_COLOR_POSITIVE}
        weight={700}
      >
        {`${share.leftLabel} ${share.leftPercentLabel}`}
      </CardText>
      <CardText
        x={right}
        y={y + 112}
        size={30}
        fill={CHART_COLOR_NEGATIVE}
        weight={700}
        anchor="end"
      >
        {`${share.rightLabel} ${share.rightPercentLabel}`}
      </CardText>
    </g>
  );
}

function ScoreChips({
  y,
  scores,
}: {
  y: number;
  scores: FootballMatchCard["topScores"];
}) {
  const gap = 16;
  const chipWidth = (MATCH_CARD_INNER_WIDTH - gap * (scores.length - 1)) / scores.length;
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 20} size={28} fill={MUTED}>
        Najczęstsze wyniki
      </CardText>
      {scores.map((chip, index) => {
        const x = MATCH_CARD_INNER_LEFT + index * (chipWidth + gap);
        return (
          <g key={chip.score}>
            <rect
              x={x}
              y={y + 44}
              width={chipWidth}
              height={108}
              rx={18}
              fill={PANEL_BORDER}
            />
            <CardText
              x={x + chipWidth / 2}
              y={y + 80}
              size={36}
              fill={TEXT}
              weight={700}
              anchor="middle"
            >
              {chip.score}
            </CardText>
            <CardText
              x={x + chipWidth / 2}
              y={y + 126}
              size={26}
              fill={ACCENT}
              weight={700}
              anchor="middle"
            >
              {chip.percentLabel}
            </CardText>
          </g>
        );
      })}
    </g>
  );
}

interface FilledHeadToHead {
  statsLabel: string;
  btts: MatchCardHeadToHeadRate;
  over: MatchCardHeadToHeadRate;
  rows: MatchCardMeetingRow[];
}

function filledHeadToHead(
  headToHead: FootballMatchCard["headToHead"],
): FilledHeadToHead | null {
  const { statsLabel, btts, over, rows } = headToHead;
  if (rows.length === 0 || statsLabel === null || btts === null || over === null) {
    return null;
  }
  return { statsLabel, btts, over, rows };
}

function HeadToHeadSection({
  card,
  y,
  height,
}: {
  card: FootballMatchCard;
  y: number;
  height: number;
}) {
  const filled = filledHeadToHead(card.headToHead);
  return (
    <g>
      <Panel y={y} height={height} />
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 48} size={36} fill={TEXT} weight={700}>
        Bezpośrednie spotkania
      </CardText>
      {filled === null ? (
        <CardText
          x={MATCH_CARD_INNER_LEFT}
          y={y + 108}
          size={30}
          fill={MUTED}
        >
          Brak bezpośrednich spotkań
        </CardText>
      ) : (
        <HeadToHeadRows headToHead={filled} y={y} />
      )}
    </g>
  );
}

function HeadToHeadRows({
  headToHead,
  y,
}: {
  headToHead: FilledHeadToHead;
  y: number;
}) {
  const statsY = (
    y
    + MATCH_CARD_METRICS.h2hHead
    + headToHead.rows.length * MATCH_CARD_METRICS.row
  );
  return (
    <g>
      <HeadToHeadColumns y={y + 112} />
      <RowDivider y={y + MATCH_CARD_METRICS.h2hHead} />
      {headToHead.rows.map((row, index) => (
        <g key={`${row.dateLabel}-${row.score}-${index}`}>
          {index > 0 ? (
            <RowDivider
              y={y + MATCH_CARD_METRICS.h2hHead + index * MATCH_CARD_METRICS.row}
            />
          ) : null}
          <MeetingRow
            row={row}
            y={rowCenter(y, MATCH_CARD_METRICS.h2hHead, index)}
          />
        </g>
      ))}
      <HeadToHeadStats headToHead={headToHead} y={statsY} />
    </g>
  );
}

function HeadToHeadColumns({ y }: { y: number }) {
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y} size={22} fill={SUBTLE}>
        Data
      </CardText>
      <CardText x={H2H_HOME_X} y={y} size={22} fill={SUBTLE}>
        Gospodarze
      </CardText>
      <CardText x={FORM_SCORE_X} y={y} size={22} fill={SUBTLE} anchor="middle">
        Wynik
      </CardText>
      <CardText x={FORM_AWAY_X} y={y} size={22} fill={SUBTLE}>
        Goście
      </CardText>
      <CardText x={FORM_BTTS_X} y={y} size={22} fill={SUBTLE} anchor="middle">
        BTTS
      </CardText>
      <CardText x={FORM_OVER_X} y={y} size={22} fill={SUBTLE} anchor="middle">
        O2.5
      </CardText>
    </g>
  );
}

function MeetingRow({ row, y }: { row: MatchCardMeetingRow; y: number }) {
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y} size={26} fill={SUBTLE}>
        {row.dateLabel}
      </CardText>
      <CardText x={H2H_HOME_X} y={y} size={28} fill={TEXT} weight={600}>
        {row.homeName}
      </CardText>
      <CardText x={FORM_SCORE_X} y={y} size={30} fill={TEXT} weight={700} anchor="middle">
        {row.score}
      </CardText>
      <CardText x={FORM_AWAY_X} y={y} size={28} fill={TEXT} weight={600}>
        {row.awayName}
      </CardText>
      <CardText
        x={FORM_BTTS_X}
        y={y}
        size={24}
        fill={flagFill(row.bothTeamsScored)}
        weight={700}
        anchor="middle"
      >
        {flagLabel(row.bothTeamsScored)}
      </CardText>
      <CardText
        x={FORM_OVER_X}
        y={y}
        size={24}
        fill={flagFill(row.overTwoAndHalf)}
        weight={700}
        anchor="middle"
      >
        {flagLabel(row.overTwoAndHalf)}
      </CardText>
    </g>
  );
}

function HeadToHeadStats({
  headToHead,
  y,
}: {
  headToHead: FilledHeadToHead;
  y: number;
}) {
  return (
    <g>
      <RowDivider y={y} />
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 40} size={22} fill={MUTED}>
        {headToHead.statsLabel}
      </CardText>
      <RateCard
        x={MATCH_CARD_INNER_LEFT}
        y={y + 72}
        rate={headToHead.btts}
      />
      <RateCard
        x={MATCH_CARD_INNER_LEFT + rateCardWidth() + 16}
        y={y + 72}
        rate={headToHead.over}
      />
    </g>
  );
}

function RateCard({
  x,
  y,
  rate,
}: {
  x: number;
  y: number;
  rate: MatchCardHeadToHeadRate;
}) {
  const width = rateCardWidth();
  return (
    <g>
      <rect x={x} y={y} width={width} height={168} rx={18} fill={STAT_BG} />
      <CardText x={x + width / 2} y={y + 46} size={32} fill={MUTED} anchor="middle">
        {rate.label}
      </CardText>
      <CardText
        x={x + width / 2}
        y={y + 116}
        size={52}
        fill={ACCENT}
        weight={700}
        anchor="middle"
      >
        {rate.percentLabel}
      </CardText>
    </g>
  );
}

function rateCardWidth(): number {
  return (MATCH_CARD_INNER_WIDTH - 16) / 2;
}

function FormSection({
  form,
  y,
  height,
}: {
  form: MatchCardForm;
  y: number;
  height: number;
}) {
  return (
    <g>
      <Panel y={y} height={height} />
      <CardText x={MATCH_CARD_INNER_LEFT} y={y + 48} size={36} fill={TEXT} weight={700}>
        {form.teamName}
      </CardText>
      {form.rows.length === 0 ? (
        <CardText x={MATCH_CARD_INNER_LEFT} y={y + 108} size={30} fill={MUTED}>
          Brak rozegranych meczów
        </CardText>
      ) : (
        <FormRows form={form} y={y} />
      )}
    </g>
  );
}

function FormRows({ form, y }: { form: MatchCardForm; y: number }) {
  return (
    <g>
      <FormColumns y={y + 114} fill={SUBTLE} size={22} />
      <RowDivider y={y + MATCH_CARD_METRICS.formHead} />
      {form.rows.map((row, index) => (
        <g key={`${row.dateLabel}-${row.homeName}-${row.score}-${index}`}>
          {index > 0 ? (
            <RowDivider
              y={y + MATCH_CARD_METRICS.formHead + index * MATCH_CARD_METRICS.row}
            />
          ) : null}
          <FormRow
            row={row}
            y={rowCenter(y, MATCH_CARD_METRICS.formHead, index)}
          />
        </g>
      ))}
    </g>
  );
}

function FormRow({ row, y }: { row: MatchCardFormRow; y: number }) {
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y} size={24} fill={SUBTLE}>
        {row.dateLabel}
      </CardText>
      <ResultBadge x={FORM_BADGE_X} y={y} result={row.result} />
      <CardText x={FORM_HOME_X} y={y} size={26} fill={TEXT} weight={600}>
        {row.homeName}
      </CardText>
      <CardText x={FORM_SCORE_X} y={y} size={28} fill={ACCENT} weight={700} anchor="middle">
        {row.score}
      </CardText>
      <CardText x={FORM_AWAY_X} y={y} size={26} fill={TEXT} weight={600}>
        {row.awayName}
      </CardText>
      <CardText
        x={FORM_BTTS_X}
        y={y}
        size={24}
        fill={flagFill(row.bothTeamsScored)}
        weight={700}
        anchor="middle"
      >
        {flagLabel(row.bothTeamsScored)}
      </CardText>
      <CardText
        x={FORM_OVER_X}
        y={y}
        size={24}
        fill={flagFill(row.overTwoAndHalf)}
        weight={700}
        anchor="middle"
      >
        {flagLabel(row.overTwoAndHalf)}
      </CardText>
    </g>
  );
}

function FormColumns({ y, fill, size }: { y: number; fill: string; size: number }) {
  return (
    <g>
      <CardText x={MATCH_CARD_INNER_LEFT} y={y} size={size} fill={fill}>
        Data
      </CardText>
      <CardText x={FORM_HOME_X} y={y} size={size} fill={fill}>
        Gospodarze
      </CardText>
      <CardText x={FORM_SCORE_X} y={y} size={size} fill={fill} anchor="middle">
        Wynik
      </CardText>
      <CardText x={FORM_AWAY_X} y={y} size={size} fill={fill}>
        Goście
      </CardText>
      <CardText x={FORM_BTTS_X} y={y} size={size} fill={fill} anchor="middle">
        BTTS
      </CardText>
      <CardText x={FORM_OVER_X} y={y} size={size} fill={fill} anchor="middle">
        Over 2.5
      </CardText>
    </g>
  );
}

function ResultBadge({
  x,
  y,
  result,
}: {
  x: number;
  y: number;
  result: TeamFormResult;
}) {
  return (
    <g>
      <rect x={x - 18} y={y - 18} width={36} height={36} rx={8} fill={resultFill(result)} />
      <CardText x={x} y={y} size={20} fill={CHART_LABEL_ON_FILL} weight={700} anchor="middle">
        {result}
      </CardText>
    </g>
  );
}

function RowDivider({ y }: { y: number }) {
  const right = MATCH_CARD_INNER_LEFT + MATCH_CARD_INNER_WIDTH;
  return (
    <line
      x1={MATCH_CARD_INNER_LEFT}
      x2={right}
      y1={y}
      y2={y}
      stroke={ROW_DIVIDER}
      strokeWidth={ROW_DIVIDER_WIDTH}
    />
  );
}

function Panel({ y, height }: { y: number; height: number }) {
  return (
    <rect
      x={MATCH_CARD_METRICS.margin}
      y={y}
      width={MATCH_CARD_METRICS.width - MATCH_CARD_METRICS.margin * 2}
      height={height}
      rx={28}
      fill={PANEL_BG}
    />
  );
}

function TripleBar({ y, segments }: { y: number; segments: MatchCardSegment[] }) {
  const height = 36;
  let offset = MATCH_CARD_INNER_LEFT;
  return (
    <g>
      <clipPath id="match-card-result">
        <rect
          x={MATCH_CARD_INNER_LEFT}
          y={y}
          width={MATCH_CARD_INNER_WIDTH}
          height={height}
          rx={height / 2}
        />
      </clipPath>
      <g clipPath="url(#match-card-result)">
        {segments.map((segment) => {
          const width = MATCH_CARD_INNER_WIDTH * segment.share;
          const rect = (
            <rect
              key={segment.tone}
              x={offset}
              y={y}
              width={width}
              height={height}
              fill={TONE_FILL[segment.tone]}
            />
          );
          offset += width;
          return rect;
        })}
      </g>
    </g>
  );
}

function ShareBar({
  y,
  share,
  clipId,
}: {
  y: number;
  share: MatchCardShare;
  clipId: string;
}) {
  const height = 36;
  const leftWidth = MATCH_CARD_INNER_WIDTH * share.leftShare;
  return (
    <g>
      <clipPath id={clipId}>
        <rect
          x={MATCH_CARD_INNER_LEFT}
          y={y}
          width={MATCH_CARD_INNER_WIDTH}
          height={height}
          rx={height / 2}
        />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        <rect
          x={MATCH_CARD_INNER_LEFT}
          y={y}
          width={leftWidth}
          height={height}
          fill={CHART_COLOR_POSITIVE}
        />
        <rect
          x={MATCH_CARD_INNER_LEFT + leftWidth}
          y={y}
          width={MATCH_CARD_INNER_WIDTH - leftWidth}
          height={height}
          fill={CHART_COLOR_NEGATIVE}
        />
      </g>
    </g>
  );
}

function CardText({
  x,
  y,
  size,
  fill,
  children,
  weight = 400,
  anchor = "start",
}: {
  x: number;
  y: number;
  size: number;
  fill: string;
  children: string;
  weight?: number;
  anchor?: "start" | "middle" | "end";
}) {
  return (
    <text
      x={x}
      y={y}
      fill={fill}
      fontSize={size}
      fontWeight={weight}
      textAnchor={anchor}
      dominantBaseline="middle"
    >
      {children}
    </text>
  );
}

function columnCenter(index: number, count: number): number {
  const slot = MATCH_CARD_INNER_WIDTH / count;
  return MATCH_CARD_INNER_LEFT + slot * index + slot / 2;
}

function rowCenter(sectionY: number, head: number, index: number): number {
  return sectionY + head + index * MATCH_CARD_METRICS.row + MATCH_CARD_METRICS.row / 2;
}

function resultFill(result: TeamFormResult): string {
  if (result === "W" || result === "WPD") {
    return CHART_COLOR_POSITIVE;
  }
  if (result === "D") {
    return CHART_COLOR_DRAW;
  }
  if (result === "L" || result === "PPD") {
    return CHART_COLOR_NEGATIVE;
  }
  return CHART_COLOR_NEUTRAL;
}

function flagFill(value: boolean): string {
  return value ? CHART_COLOR_POSITIVE : CHART_COLOR_NEGATIVE;
}

function flagLabel(value: boolean): string {
  return value ? "TAK" : "NIE";
}
