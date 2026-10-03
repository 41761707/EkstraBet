import { ExpandableSection } from "@/components/ExpandableSection";
import { StatusMessage } from "@/components/StatusMessage";
import { HockeyRosterBoard } from "@/components/teams/HockeyRosterBoard";
import type { HockeyTeamRoster } from "@/types/api";

interface HockeyTeamRosterSectionProps {
  roster: HockeyTeamRoster | null;
  errorMessage?: string | null;
}

export function HockeyTeamRosterSection({
  roster,
  errorMessage = null,
}: HockeyTeamRosterSectionProps) {
  return (
    <ExpandableSection title="Skład" defaultOpen>
      <RosterBody roster={roster} errorMessage={errorMessage} />
    </ExpandableSection>
  );
}

function RosterBody({
  roster,
  errorMessage,
}: HockeyTeamRosterSectionProps) {
  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować składu"
        message={errorMessage}
      />
    );
  }

  if (!roster || roster.groups.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak składu"
        message="Ta drużyna nie ma jeszcze wpisanego składu."
      />
    );
  }

  return <HockeyRosterBoard roster={roster} />;
}
