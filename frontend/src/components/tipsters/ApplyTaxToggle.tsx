"use client";

import { useRouter } from "next/navigation";

import {
  APPLY_TAX_HINT,
  APPLY_TAX_LABEL,
  tipsterApplyTaxPath,
} from "@/components/tipsters/tipsterModel";
import { navigateSearch } from "@/lib/clientNavigation";

interface ApplyTaxToggleProps {
  checked: boolean;
  pathname: string;
  searchParams: Record<string, string | undefined>;
  resetPage?: boolean;
}

export function ApplyTaxToggle({
  checked,
  pathname,
  searchParams,
  resetPage = false,
}: ApplyTaxToggleProps) {
  const router = useRouter();

  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => {
            navigateSearch(
              tipsterApplyTaxPath(
                pathname,
                searchParams,
                event.target.checked,
                resetPage,
              ),
              router,
            );
          }}
          className="rounded border-border bg-surface-raised accent-accent"
        />
        {APPLY_TAX_LABEL}
      </label>
      <p className="text-xs text-muted">{APPLY_TAX_HINT}</p>
    </div>
  );
}
