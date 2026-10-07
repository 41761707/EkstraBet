import type { HockeyRosterPlayer, HockeyTeamRoster } from "@/types/api";

const WING_SLOTS = ["LW", "C", "RW"] as const;
const DEFENSE_POSITION = "D";

export type PowerPlayUnit = 1 | 2;

export interface PowerPlaySheet {
  wings: (HockeyRosterPlayer | null)[];
  back: (HockeyRosterPlayer | null)[];
  overflow: HockeyRosterPlayer[];
}

/** Skaters assigned to one power-play unit, in roster order. */
export function playersOnPowerPlay(
  roster: HockeyTeamRoster,
  unit: PowerPlayUnit,
): HockeyRosterPlayer[] {
  return roster.groups.flatMap((group) =>
    group.players.filter((player) => player.pp_unit === unit),
  );
}

/**
 * Lay a power-play unit on the five-man sheet.
 *
 * Defensemen take the two back slots before anyone else, including when
 * they appear last in the list. Forwards take a matching wing first, so a
 * second center does not push the only left wing onto C. Everyone left
 * fills the first open slot, wings before the back row.
 */
export function placePowerPlayUnit(players: HockeyRosterPlayer[]): PowerPlaySheet {
  const wings: (HockeyRosterPlayer | null)[] = [null, null, null];
  const back: (HockeyRosterPlayer | null)[] = [null, null];
  const unmatched: HockeyRosterPlayer[] = [];

  for (const player of players) {
    if (isDefenseman(player)) {
      if (!takeOpen(back, player)) {
        unmatched.push(player);
      }
      continue;
    }
    const index = wingIndex(player.position);
    if (index >= 0 && wings[index] === null) {
      wings[index] = player;
      continue;
    }
    unmatched.push(player);
  }

  const overflow: HockeyRosterPlayer[] = [];
  for (const player of unmatched) {
    if (takeOpen(wings, player) || takeOpen(back, player)) {
      continue;
    }
    overflow.push(player);
  }

  return { wings, back, overflow };
}

function takeOpen(
  slots: (HockeyRosterPlayer | null)[],
  player: HockeyRosterPlayer,
): boolean {
  const index = slots.findIndex((slot) => slot === null);
  if (index < 0) {
    return false;
  }
  slots[index] = player;
  return true;
}

function isDefenseman(player: HockeyRosterPlayer): boolean {
  return player.position.trim().toUpperCase() === DEFENSE_POSITION;
}

function wingIndex(position: string): number {
  const code = position.trim().toUpperCase();
  return WING_SLOTS.findIndex((slot) => slot === code);
}
