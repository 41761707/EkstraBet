import { HockeyPlayerEventSplitTiles } from "@/components/players/HockeyPlayerEventSplitTiles";
import { HockeyPlayerSliceTable } from "@/components/players/HockeyPlayerSliceTable";
import { PlayerSummaryTiles } from "@/components/players/PlayerSummaryTiles";
import {
  HOCKEY_SPORT_ID,
  type HockeyPlayerEventSplit,
  type HockeyPlayerProfileBody as HockeyPlayerProfileData,
} from "@/types/api";

interface HockeyPlayerProfileBodyProps {
  body: HockeyPlayerProfileData;
}

export function HockeyPlayerProfileBody({
  body,
}: HockeyPlayerProfileBodyProps) {
  if (body.matches.length === 0) {
    return null;
  }

  const eventSplit: HockeyPlayerEventSplit | null = body.event_split;

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-text">Protokół meczowy</h2>
        <PlayerSummaryTiles
          sportId={HOCKEY_SPORT_ID}
          playerRole={body.player_role}
          summary={body.summary}
        />
      </section>
      {eventSplit === null ? null : (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-text">Zdarzenia</h2>
          <HockeyPlayerEventSplitTiles split={eventSplit} />
        </section>
      )}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-text">Log meczowy</h2>
        <HockeyPlayerSliceTable
          playerRole={body.player_role}
          matches={body.matches}
        />
      </section>
    </div>
  );
}
