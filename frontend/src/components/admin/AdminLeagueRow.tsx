import {
  ADMIN_DANGER_BUTTON_CLASS,
  ADMIN_SECONDARY_BUTTON_CLASS,
  StatusBadge,
} from "@/components/admin/adminChrome";
import {
  ADMIN_LEAGUES_BUSY_HINT,
  leagueCountryLabel,
  leagueSeasonLabel,
} from "@/components/admin/adminLeaguesModel";
import { formatMatchDate } from "@/lib/format";
import type { AdminLeague, AdminSeason } from "@/types/api";

interface AdminLeagueRowProps {
  league: AdminLeague;
  seasons: AdminSeason[];
  isSaving: boolean;
  areActionsLocked: boolean;
  onToggleActive: (league: AdminLeague) => void;
}

export function AdminLeagueRow({
  league,
  seasons,
  isSaving,
  areActionsLocked,
  onToggleActive,
}: AdminLeagueRowProps) {
  const displayName = league.name?.trim() ? league.name : "—";
  const updatedLabel = league.last_update
    ? formatMatchDate(league.last_update)
    : "—";
  const seasonLabel = leagueSeasonLabel(seasons, league.current_season_id);
  const tierLabel = league.tier === null ? "—" : String(league.tier);

  return (
    <li className="rounded-lg border border-border bg-surface-muted px-3 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1 space-y-2">
          <p className="flex min-w-0 items-baseline gap-2">
            <span className="truncate font-medium text-text">{displayName}</span>
            <span className="shrink-0 text-sm font-normal text-muted">
              ID {league.id}
            </span>
          </p>
          <p className="truncate text-sm text-muted">
            {leagueCountryLabel(league)}
            {league.sport_name ? ` · ${league.sport_name}` : ""}
          </p>
          <LeagueStatusBadges league={league} />
          <p className="text-xs text-muted">
            Sezon: {seasonLabel} · Poziom: {tierLabel} · Aktualizacja: {updatedLabel}
          </p>
        </div>
        <button
          type="button"
          disabled={areActionsLocked}
          title={areActionsLocked ? ADMIN_LEAGUES_BUSY_HINT : undefined}
          onClick={() => onToggleActive(league)}
          className={league.active ? ADMIN_DANGER_BUTTON_CLASS : ADMIN_SECONDARY_BUTTON_CLASS}
        >
          {isSaving ? "Zapisywanie…" : league.active ? "Dezaktywuj" : "Aktywuj"}
        </button>
      </div>
    </li>
  );
}

function LeagueStatusBadges({ league }: { league: AdminLeague }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <StatusBadge
        label={league.active ? "Aktywna" : "Nieaktywna"}
        tone={league.active ? "success" : "danger"}
      />
      {league.has_player_stats ? (
        <StatusBadge label="Statystyki zawodników" tone="accent" />
      ) : null}
    </div>
  );
}
