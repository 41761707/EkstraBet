/** Polish display labels for analytics type keys (OU / BTTS / 1X2). */

const ANALYTICS_TYPE_LABELS: Record<string, string> = {
  under_2_5: "Poniżej 2.5",
  over_2_5: "Powyżej 2.5",
  no: "BTTS nie",
  yes: "BTTS tak",
  home: "Gospodarz",
  draw: "Remis",
  away: "Gość",
};

/** Map backend type key (or English chart label) to Polish UI label. */
export function formatAnalyticsTypeLabel(raw: string): string {
  const direct = ANALYTICS_TYPE_LABELS[raw];
  if (direct) {
    return direct;
  }

  const normalized = raw.trim().toLowerCase();
  const englishFallback: Record<string, string> = {
    "under 2.5": "Poniżej 2.5",
    "over 2.5": "Powyżej 2.5",
    "no btts": "BTTS nie",
    btts: "BTTS tak",
    "btts yes": "BTTS tak",
    "btts no": "BTTS nie",
    home: "Gospodarz",
    draw: "Remis",
    away: "Gość",
  };
  return englishFallback[normalized] ?? raw;
}
