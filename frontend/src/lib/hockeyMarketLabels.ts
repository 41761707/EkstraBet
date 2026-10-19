/** Polish labels for NHL event families from the catalog. */

export const HOCKEY_FAMILY_LABELS: Record<string, string> = {
  HOCKEY_ML: "Zwycięzca (OT/SO)",
  HOCKEY_OU_55: "Powyżej/poniżej 5.5",
  HOCKEY_OU_65: "Powyżej/poniżej 6.5",
  HOCKEY_PL_HOME: "Handicap gospodarza",
  HOCKEY_PL_AWAY: "Handicap gościa",
  HOCKEY_HOME_TT_25: "Gole gospodarza 2.5",
  HOCKEY_HOME_TT_35: "Gole gospodarza 3.5",
  HOCKEY_AWAY_TT_25: "Gole gościa 2.5",
  HOCKEY_AWAY_TT_35: "Gole gościa 3.5",
};

export const HOCKEY_FAMILY_ORDER = Object.keys(HOCKEY_FAMILY_LABELS);

/** Label for a family code. Unknown names stay as stored in the catalog. */
export function hockeyFamilyLabel(familyName: string): string {
  return HOCKEY_FAMILY_LABELS[familyName] ?? familyName;
}
