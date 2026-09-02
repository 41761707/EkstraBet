import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { AdminPageView } from "@/app/admin/AdminPageView";
import { loadAdminPage } from "@/app/admin/loadAdminPage";
import { StatusMessage } from "@/components/StatusMessage";
import { isAuthEnabled } from "@/lib/authCookie";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Panel administratora | EkstraBet",
  description: "Zarządzanie kontami użytkowników i ligami.",
};

export default async function AdminPage() {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const page = await loadAdminPage();
  if (page.kind === "unauthenticated") {
    redirect("/login");
  }
  if (page.kind === "forbidden") {
    notFound();
  }
  if (page.kind === "error") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować panelu administratora"
        message={page.message}
      />
    );
  }

  return <AdminPageView />;
}
