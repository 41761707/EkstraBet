import { formatPercent } from "@/lib/format";
import type { LeagueCharacteristics } from "@/types/api";

interface LeagueCharacteristicsPanelProps {
  characteristics: LeagueCharacteristics;
  title?: string;
  labels?: "en" | "pl";
}

const OU_LABELS_PL: Record<string, string> = {
  under_1_5: "Poniżej 1.5",
  over_1_5: "Powyżej 1.5",
  under_2_5: "Poniżej 2.5",
  over_2_5: "Powyżej 2.5",
  under_3_5: "Poniżej 3.5",
  over_3_5: "Powyżej 3.5",
};

const OU_LABELS_EN: Record<string, string> = {
  under_1_5: "Under 1.5",
  over_1_5: "Over 1.5",
  under_2_5: "Under 2.5",
  over_2_5: "Over 2.5",
  under_3_5: "Under 3.5",
  over_3_5: "Over 3.5",
};

const BTTS_LABELS_PL: Record<string, string> = {
  no: "BTTS nie",
  yes: "BTTS tak",
};

const BTTS_LABELS_EN: Record<string, string> = {
  no: "BTTS no",
  yes: "BTTS yes",
};

const RESULT_LABELS_PL: Record<string, string> = {
  home: "Gospodarz",
  draw: "Remis",
  away: "Gość",
};

const RESULT_LABELS_EN: Record<string, string> = {
  home: "Home",
  draw: "Draw",
  away: "Away",
};

function formatBucketLabel(
  group: "ou" | "btts" | "result",
  key: string,
  labels: "en" | "pl",
): string {
  if (group === "ou") {
    return (labels === "pl" ? OU_LABELS_PL : OU_LABELS_EN)[key] ?? key;
  }
  if (group === "btts") {
    return (labels === "pl" ? BTTS_LABELS_PL : BTTS_LABELS_EN)[key] ?? key;
  }
  return (labels === "pl" ? RESULT_LABELS_PL : RESULT_LABELS_EN)[key] ?? key;
}

function BucketList({
  title,
  buckets,
  group,
  labels,
}: {
  title: string;
  buckets: Record<string, { count: number; percentage: number }>;
  group: "ou" | "btts" | "result";
  labels: "en" | "pl";
}) {
  const entries = Object.entries(buckets).sort(([left], [right]) => {
    if (group !== "ou") {
      return 0;
    }
    const order = [
      "under_1_5",
      "over_1_5",
      "under_2_5",
      "over_2_5",
      "under_3_5",
      "over_3_5",
    ];
    return order.indexOf(left) - order.indexOf(right);
  });
  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <h4 className="mb-3 text-sm font-semibold text-white">{title}</h4>
      <ul className="space-y-2 text-sm text-slate-300">
        {entries.map(([key, bucket]) => (
          <li key={key} className="flex items-center justify-between">
            <span>{formatBucketLabel(group, key, labels)}</span>
            <span>
              {bucket.count} ({formatPercent(bucket.percentage)})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function LeagueCharacteristicsPanel({
  characteristics,
  title,
  labels = "pl",
}: LeagueCharacteristicsPanelProps) {
  const isPolish = labels === "pl";

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold text-white">
        {title ?? (isPolish ? "Statystyki ligowe" : "League characteristics")}
      </h2>
      <p className="text-sm text-slate-400">
        {isPolish
          ? `Do tej pory rozegrano ${characteristics.played_matches} meczów.`
          : `${characteristics.played_matches} matches played.`}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">
            {isPolish ? "Rozegrane mecze" : "Played matches"}
          </p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {characteristics.played_matches}
          </p>
        </div>
        <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">
            {isPolish ? "Średnia bramek / mecz" : "Avg goals / match"}
          </p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {characteristics.avg_goals_per_match.toFixed(2)}
          </p>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <BucketList
          title="Over/Under"
          buckets={characteristics.ou}
          group="ou"
          labels={labels}
        />
        <BucketList
          title="BTTS"
          buckets={characteristics.btts}
          group="btts"
          labels={labels}
        />
        <BucketList
          title={isPolish ? "Rezultat 1X2" : "1X2"}
          buckets={characteristics.result}
          group="result"
          labels={labels}
        />
      </div>
    </section>
  );
}
