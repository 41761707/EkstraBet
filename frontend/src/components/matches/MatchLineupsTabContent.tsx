import { BasketballMatchLineupsPanel } from "@/components/matches/BasketballMatchLineupsPanel";
import { HockeyMatchLineupsPanel } from "@/components/matches/HockeyMatchLineupsPanel";
import { StatusMessage } from "@/components/StatusMessage";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type MatchDetails,
} from "@/types/api";

interface MatchLineupsTabContentProps {
  match: MatchDetails;
}

function LineupsUnavailableMessage() {
  return (
    <StatusMessage
      variant="empty"
      title="Brak składów"
      message="Skład meczowy nie jest dostępny dla tego meczu."
    />
  );
}

export function MatchLineupsTabContent({ match }: MatchLineupsTabContentProps) {
  if (match.sport_id === HOCKEY_SPORT_ID) {
    if (!match.hockey_lineups) {
      return <LineupsUnavailableMessage />;
    }
    return (
      <HockeyMatchLineupsPanel
        lineups={match.hockey_lineups}
        homeTeamName={match.home_team.name}
        awayTeamName={match.away_team.name}
      />
    );
  }

  if (match.sport_id === BASKETBALL_SPORT_ID) {
    if (!match.basketball_lineups) {
      return <LineupsUnavailableMessage />;
    }
    return (
      <BasketballMatchLineupsPanel
        lineups={match.basketball_lineups}
        homeTeamName={match.home_team.name}
        awayTeamName={match.away_team.name}
      />
    );
  }

  return <LineupsUnavailableMessage />;
}
