import type {
  BasketballLineupPlayer,
  BasketballTeamLineup,
} from "@/types/api";

/** Fixed 2-1-2 slots on viewBox 0 0 50 47 (basket at the bottom). */
export const BASKETBALL_STARTER_SLOTS = [
  { x: 12, y: 14 },
  { x: 38, y: 14 },
  { x: 25, y: 24 },
  { x: 14, y: 36 },
  { x: 36, y: 36 },
] as const;

export const BASKETBALL_STARTER_SLOT_COUNT = BASKETBALL_STARTER_SLOTS.length;

export interface BasketballCourtMarker {
  playerId: number;
  name: string;
  number: number | null;
  x: number;
  y: number;
}

/** Starters in the same order as the API payload. */
export function starterPlayers(
  team: BasketballTeamLineup,
): BasketballLineupPlayer[] {
  return team.players.filter((player) => player.starter);
}

function compareStartersByNumber(
  left: BasketballLineupPlayer,
  right: BasketballLineupPlayer,
): number {
  if (left.number === right.number) {
    return left.player_id - right.player_id;
  }
  if (left.number === null) {
    return 1;
  }
  if (right.number === null) {
    return -1;
  }
  return left.number - right.number;
}

/** Place at most five starters on the 2-1-2 slots; extra starters are omitted. */
export function courtMarkersForStarters(
  players: BasketballLineupPlayer[],
): BasketballCourtMarker[] {
  // kopiujemy, bo sort mutuje tablicę, a kolejność payloadu zostaje w tabeli
  const starters = [...players]
    .filter((player) => player.starter)
    .sort(compareStartersByNumber)
    .slice(0, BASKETBALL_STARTER_SLOT_COUNT);

  return starters.map((player, index) => {
    const slot = BASKETBALL_STARTER_SLOTS[index];
    return {
      playerId: player.player_id,
      name: player.player_name,
      number: player.number,
      x: slot.x,
      y: slot.y,
    };
  });
}
