import { BasketballCourt } from "@/components/matches/BasketballCourt";
import {
  courtMarkersForStarters,
  starterPlayers,
} from "@/components/matches/basketballLineupModel";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  BasketballLineupPlayer,
  BasketballMatchLineups,
  BasketballTeamLineup,
} from "@/types/api";

interface BasketballMatchLineupsPanelProps {
  lineups: BasketballMatchLineups;
  homeTeamName: string;
  awayTeamName: string;
}

function formatJerseyNumber(value: number | null): string {
  return value === null ? "—" : String(value);
}

function formatStarter(isStarter: boolean): string {
  return isStarter ? "⭐" : "—";
}

function BasketballLineupTable({
  players,
}: {
  players: BasketballLineupPlayer[];
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Zawodnik</th>
            <th className="px-3 py-2 text-center font-medium">Numer</th>
            <th className="px-3 py-2 text-center font-medium">Starter</th>
          </tr>
        </thead>
        <tbody>
          {players.map((player) => (
            <tr
              key={player.player_id}
              className="border-t border-border hover:bg-surface-muted/50"
            >
              <td className="px-3 py-2 font-medium text-text">
                {player.player_name}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatJerseyNumber(player.number)}
              </td>
              <td className="px-3 py-2 text-center text-text">
                {formatStarter(player.starter)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BasketballTeamLineupColumn({
  team,
  teamName,
}: {
  team: BasketballTeamLineup;
  teamName: string;
}) {
  if (team.players.length === 0) {
    return (
      <section className="min-w-0 space-y-3">
        <h3 className="text-xl font-semibold text-center text-text">
          {teamName}
        </h3>
        <StatusMessage
          variant="empty"
          title="Brak zawodników"
          message="Skład tej drużyny nie jest dostępny."
        />
      </section>
    );
  }

  const markers = courtMarkersForStarters(starterPlayers(team));

  return (
    <section className="min-w-0 space-y-3">
      <h3 className="text-xl font-semibold text-center text-text">
        {teamName}
      </h3>
      <BasketballCourt markers={markers} />
      <BasketballLineupTable players={team.players} />
    </section>
  );
}

export function BasketballMatchLineupsPanel({
  lineups,
  homeTeamName,
  awayTeamName,
}: BasketballMatchLineupsPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <BasketballTeamLineupColumn team={lineups.home} teamName={homeTeamName} />
      <BasketballTeamLineupColumn team={lineups.away} teamName={awayTeamName} />
    </div>
  );
}
