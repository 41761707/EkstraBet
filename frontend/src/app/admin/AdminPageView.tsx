import { AdminLeaguesPanel } from "@/components/admin/AdminLeaguesPanel";
import { AdminUsersPanel } from "@/components/admin/AdminUsersPanel";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  AdminUser,
} from "@/types/api";

interface AdminPageViewProps {
  currentUserUuid: string;
  users: AdminUser[];
  usersError?: string | null;
  leagues: AdminLeague[];
  leaguesError?: string | null;
  countries: AdminCountry[];
  sports: AdminSport[];
  seasons: AdminSeason[];
  dictionariesError?: string | null;
  seasonsError?: string | null;
}

export function AdminPageView({
  currentUserUuid,
  users,
  usersError = null,
  leagues,
  leaguesError = null,
  countries,
  sports,
  seasons,
  dictionariesError = null,
  seasonsError = null,
}: AdminPageViewProps) {
  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold text-text">Panel administratora</h1>
        <p className="text-muted">Zarządzaj kontami użytkowników i ligami.</p>
      </section>
      <AdminUsersPanel
        currentUserUuid={currentUserUuid}
        initialUsers={users}
        usersError={usersError}
      />
      <AdminLeaguesPanel
        initialLeagues={leagues}
        countries={countries}
        sports={sports}
        seasons={seasons}
        leaguesError={leaguesError}
        dictionariesError={dictionariesError}
        seasonsError={seasonsError}
      />
    </div>
  );
}
