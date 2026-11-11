export interface PlayerPropEventOption {
  id: number;
  label: string;
}

/** Over lines that have both a bookmaker price and a player model. */
export const PLAYER_PROP_EVENT_OPTIONS: PlayerPropEventOption[] = [
  { id: 190, label: "Strzały na bramkę" },
  { id: 192, label: "Punkty kanadyjskie" },
  { id: 194, label: "Asysty" },
  { id: 196, label: "Gole" },
];
