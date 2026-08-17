"use client";

import { useSearchParams } from "next/navigation";

/**
 * Force a fresh subtree when only query params change (season, round, phase…).
 * Without this, client-side navigation can fetch RSC but keep stale UI in prod.
 */
export default function LeagueTemplate({
  children,
}: {
  children: React.ReactNode;
}) {
  const searchParams = useSearchParams();
  return <div key={searchParams.toString()}>{children}</div>;
}
