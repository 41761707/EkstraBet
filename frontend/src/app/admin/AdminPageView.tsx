import { AdminUsersPanel } from "@/components/admin/AdminUsersPanel";
import type { AdminUser } from "@/types/api";

interface AdminPageViewProps {
  currentUserUuid: string;
  users: AdminUser[];
  usersError?: string | null;
}

export function AdminPageView({
  currentUserUuid,
  users,
  usersError = null,
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
    </div>
  );
}
