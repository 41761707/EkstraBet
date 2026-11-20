import { formatMatchDate } from "@/lib/format";
import type { HockeyPlayerSliceMatch } from "@/types/api";

interface SliceColumn {
  key: string;
  label: string;
  align: "left" | "center";
  cell: (match: HockeyPlayerSliceMatch) => string;
}

const VENUE_LABEL: Record<HockeyPlayerSliceMatch["venue"], string> = {
  home: "Dom",
  away: "Wyjazd",
};

const HEADER_COLUMNS: SliceColumn[] = [
  {
    key: "game_date",
    label: "Data",
    align: "left",
    cell: (match) => formatMatchDate(match.game_date),
  },
  {
    key: "season",
    label: "Sezon",
    align: "left",
    cell: (match) => match.season_years,
  },
  {
    key: "club",
    label: "Klub",
    align: "left",
    cell: (match) => match.own_team_name,
  },
  {
    key: "opponent",
    label: "Rywal",
    align: "left",
    cell: (match) => match.opponent_name,
  },
  {
    key: "venue",
    label: "Dom/wyjazd",
    align: "left",
    cell: (match) => VENUE_LABEL[match.venue],
  },
  {
    key: "result",
    label: "Wynik",
    align: "center",
    cell: formatSliceScore,
  },
];

const SKATER_COLUMNS: SliceColumn[] = [
  countColumn("points", "Punkty", (match) => match.points),
  countColumn("goals", "Bramki", (match) => match.goals),
  countColumn("assists", "Asysty", (match) => match.assists),
  countColumn("plus_minus", "Plus/Minus", (match) => match.plus_minus),
  countColumn("penalty_minutes", "Minuty kar", (match) => match.penalty_minutes),
  countColumn("toi", "Czas na lodzie", (match) => match.toi),
  countColumn("sog", "Strzały na bramkę", (match) => match.sog),
];

const GOALIE_COLUMNS: SliceColumn[] = [
  countColumn("shots_against", "Strzały na bramkę", (match) => match.shots_against),
  countColumn("shots_saved", "Obrony", (match) => match.shots_saved),
  {
    key: "saves_acc",
    label: "Skuteczność obron (%)",
    align: "center",
    cell: (match) => formatSavePercentage(match.saves_acc),
  },
  countColumn("toi", "Czas na lodzie", (match) => match.toi),
];

const SITUATIONAL_COLUMNS: SliceColumn[] = [
  countColumn("power_play_goals", "Gole w przewadze", (match) => match.power_play_goals),
  countColumn("empty_net_goals", "Gole do pustej", (match) => match.empty_net_goals),
];

interface HockeyPlayerSliceTableProps {
  playerRole: "skater" | "goalie";
  matches: HockeyPlayerSliceMatch[];
}

export function HockeyPlayerSliceTable({
  playerRole,
  matches,
}: HockeyPlayerSliceTableProps) {
  const columns = sliceColumns(playerRole);

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={headerClassName(column.align)}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <tr
              key={match.match_id}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cellClassName(column.align)}
                >
                  {column.cell(match)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function sliceColumns(playerRole: "skater" | "goalie"): SliceColumn[] {
  const roleColumns = playerRole === "goalie" ? GOALIE_COLUMNS : SKATER_COLUMNS;
  return [...HEADER_COLUMNS, ...roleColumns, ...SITUATIONAL_COLUMNS];
}

function countColumn(
  key: string,
  label: string,
  read: (match: HockeyPlayerSliceMatch) => string | number | null,
): SliceColumn {
  return {
    key,
    label,
    align: "center",
    cell: (match) => formatCount(read(match)),
  };
}

function headerClassName(align: SliceColumn["align"]): string {
  const placement = align === "center" ? "text-center" : "text-left";
  return `whitespace-nowrap px-3 py-3 font-medium ${placement}`;
}

function cellClassName(align: SliceColumn["align"]): string {
  const placement = align === "center" ? "text-center" : "text-left";
  return `whitespace-nowrap px-3 py-2 text-text ${placement}`;
}

function formatCount(value: string | number | null): string {
  if (value === null || value === "") {
    return "-";
  }
  return String(value);
}

function formatSavePercentage(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return `${value}%`;
}

// Kod wyniku w matches to 1/X/2. W logu widać bramki, tak jak na stronie meczu.
function formatSliceScore(match: HockeyPlayerSliceMatch): string {
  if (match.home_goals === null || match.away_goals === null) {
    return "-";
  }
  return `${match.home_goals}:${match.away_goals}`;
}
