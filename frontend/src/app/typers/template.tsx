"use client";

import { useSearchParams } from "next/navigation";

export default function SearchParamsTemplate({
  children,
}: {
  children: React.ReactNode;
}) {
  const searchParams = useSearchParams();
  return <div key={searchParams.toString()}>{children}</div>;
}
