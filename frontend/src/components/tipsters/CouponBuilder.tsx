"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { SUBMIT_BUTTON_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import { CouponPicker } from "@/components/tipsters/CouponPicker";
import { CouponStakeFields } from "@/components/tipsters/CouponStakeFields";
import {
  clearCouponDraft,
  matchesForDraftLegs,
  readCouponDraft,
  writeCouponDraft,
  type PersistedCouponDraft,
} from "@/components/tipsters/couponDraftStorage";
import { DraftLegsList } from "@/components/tipsters/DraftLegsList";
import {
  addEventToDraftLegs,
  buildCouponCreateRequest,
  mergeCatalogMatches,
  removeEventFromDraftLegs,
  tipsterMutationMessage,
  updateDraftLegOdds,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import { usePickerCatalog } from "@/components/tipsters/usePickerCatalog";
import { createMyCoupon } from "@/lib/apiClient";
import type {
  CatalogMatch,
  CatalogMatchesResponse,
  CurrencyCode,
  StakeInputMode,
} from "@/types/api";

export const COUPON_BUILDER_TITLE = "Nowy kupon";
export const COUPON_BUILDER_HINT =
  "Drugi event tego samego meczu trafia do jednej nogi combined. " +
  "Wpisz kurs łączony bukmachera — nie iloczyn i nie cenę pierwszego eventu.";
export {
  ADD_CATALOG_EVENT_LABEL,
  ALL_LEAGUES_LABEL,
  CATALOG_DATE_LABEL,
  CATALOG_UPCOMING_HINT,
  EVENT_SEARCH_LABEL,
  FAVORITES_UNAVAILABLE_HINT,
  MATCH_SEARCH_LABEL,
} from "@/components/tipsters/CouponPicker";

interface CouponBuilderProps {
  catalog: CatalogMatchesResponse;
  favoriteLeagueIds: number[];
  favoritesUnavailable?: boolean;
  draftStorageKey: string;
  unitSize: number;
  currency: CurrencyCode;
}

export function CouponBuilder({
  catalog,
  favoriteLeagueIds,
  favoritesUnavailable = false,
  draftStorageKey,
  unitSize,
  currency,
}: CouponBuilderProps) {
  const draft = useCouponDraft(catalog, favoriteLeagueIds, draftStorageKey);
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-text">{COUPON_BUILDER_TITLE}</h3>
        <p className="text-sm text-muted">{COUPON_BUILDER_HINT}</p>
      </div>
      <CouponPicker
        events={catalog.events}
        pickerMatches={draft.picker.pickerMatches}
        catalogDate={draft.picker.catalogDate}
        matchQuery={draft.picker.matchQuery}
        includeAllLeagues={draft.picker.includeAllLeagues}
        hasFavoriteLeagues={favoriteLeagueIds.length > 0}
        favoritesUnavailable={favoritesUnavailable}
        isLoadingMatches={draft.picker.isLoading}
        catalogError={draft.picker.error}
        matchId={draft.matchId}
        eventId={draft.eventId}
        disabled={draft.isSubmitting}
        onDateChange={draft.handleDateChange}
        onAllLeaguesChange={draft.handleAllLeaguesChange}
        onQueryChange={draft.picker.setMatchQuery}
        onMatchChange={draft.setMatchId}
        onEventChange={draft.setEventId}
        onAdd={draft.handleAddEvent}
      />
      <CouponSlipForm
        catalog={catalog}
        knownMatches={draft.knownMatches}
        legs={draft.legs}
        mode={draft.mode}
        stakeRaw={draft.stakeRaw}
        unitSize={unitSize}
        currency={currency}
        error={draft.error}
        isSubmitting={draft.isSubmitting}
        onOddsChange={draft.handleOddsChange}
        onRemove={draft.handleRemove}
        onModeChange={draft.setMode}
        onStakeChange={draft.setStakeRaw}
        onSave={draft.handleSave}
      />
    </div>
  );
}

function useCouponDraft(
  catalog: CatalogMatchesResponse,
  favoriteLeagueIds: number[],
  storageKey: string,
) {
  const router = useRouter();
  const picker = usePickerCatalog(catalog.matches, favoriteLeagueIds);
  const submittingRef = useRef(false);
  const [matchId, setMatchId] = useState(catalog.matches[0]?.id ?? 0);
  const [eventId, setEventId] = useState(catalog.events[0]?.id ?? 0);
  const [legs, setLegs] = useState<DraftCouponLeg[]>([]);
  const [mode, setMode] = useState<StakeInputMode>("money");
  const [stakeRaw, setStakeRaw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [restoredMatches, setRestoredMatches] = useState<CatalogMatch[]>([]);
  const knownMatches = mergeCatalogMatches(picker.knownMatches, restoredMatches);

  useCouponSlipStorage(storageKey, {
    legs,
    mode,
    stakeRaw,
    knownMatches,
    applyDraft: (draft) => {
      setLegs(draft.legs);
      setMode(draft.mode);
      setStakeRaw(draft.stakeRaw);
      setRestoredMatches(draft.matches);
    },
  });

  function handleAddEvent() {
    const result = addEventToDraftLegs(legs, matchId, eventId);
    if ("error" in result) {
      setError(draftLegErrorMessage(result.error));
      return;
    }
    setError(null);
    setLegs(result.legs);
  }

  async function handleSave() {
    if (submittingRef.current) {
      return;
    }
    submittingRef.current = true;
    setIsSubmitting(true);
    const request = buildCouponCreateRequest(legs, mode, stakeRaw);
    if ("error" in request) {
      submittingRef.current = false;
      setIsSubmitting(false);
      setError(request.error);
      return;
    }
    setError(null);
    try {
      await createMyCoupon(request);
      setLegs([]);
      setStakeRaw("");
      clearCouponDraft(storageKey);
      router.refresh();
    } catch (cause) {
      setError(tipsterMutationMessage(cause));
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  }

  return {
    picker,
    knownMatches,
    matchId,
    eventId,
    legs,
    mode,
    stakeRaw,
    error,
    isSubmitting,
    setMatchId,
    setEventId,
    setMode,
    setStakeRaw,
    handleAddEvent,
    handleSave,
    handleDateChange: (nextDate: string) =>
      applyPickerMatches(picker.changeDate(nextDate), matchId, setMatchId),
    handleAllLeaguesChange: (nextValue: boolean) =>
      applyPickerMatches(
        picker.changeIncludeAllLeagues(nextValue),
        matchId,
        setMatchId,
      ),
    handleOddsChange: (id: number, odds: string) =>
      setLegs(updateDraftLegOdds(legs, id, odds)),
    handleRemove: (id: number, eventIdToRemove: number) =>
      setLegs(removeEventFromDraftLegs(legs, id, eventIdToRemove)),
  };
}

function useCouponSlipStorage(
  storageKey: string,
  state: {
    legs: DraftCouponLeg[];
    mode: StakeInputMode;
    stakeRaw: string;
    knownMatches: CatalogMatch[];
    applyDraft: (draft: PersistedCouponDraft) => void;
  },
) {
  const [isHydrated, setIsHydrated] = useState(false);
  const applyRef = useRef(state.applyDraft);
  applyRef.current = state.applyDraft;

  useEffect(() => {
    const draft = readCouponDraft(storageKey);
    if (draft) {
      applyRef.current(draft);
    }
    setIsHydrated(true);
  }, [storageKey]);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }
    if (state.legs.length === 0 && !state.stakeRaw) {
      clearCouponDraft(storageKey);
      return;
    }
    writeCouponDraft(storageKey, {
      legs: state.legs,
      mode: state.mode,
      stakeRaw: state.stakeRaw,
      matches: matchesForDraftLegs(state.knownMatches, state.legs),
    });
  }, [
    isHydrated,
    storageKey,
    state.legs,
    state.mode,
    state.stakeRaw,
    state.knownMatches,
  ]);
}

async function applyPickerMatches(
  pending: Promise<CatalogMatch[] | null>,
  matchId: number,
  setMatchId: (id: number) => void,
) {
  const nextMatches = await pending;
  if (nextMatches && !nextMatches.some((match) => match.id === matchId)) {
    setMatchId(nextMatches[0]?.id ?? 0);
  }
}

interface CouponSlipFormProps {
  catalog: CatalogMatchesResponse;
  knownMatches: CatalogMatch[];
  legs: DraftCouponLeg[];
  mode: StakeInputMode;
  stakeRaw: string;
  unitSize: number;
  currency: CurrencyCode;
  error: string | null;
  isSubmitting: boolean;
  onOddsChange: (matchId: number, odds: string) => void;
  onRemove: (matchId: number, eventId: number) => void;
  onModeChange: (mode: StakeInputMode) => void;
  onStakeChange: (value: string) => void;
  onSave: () => Promise<void>;
}

function CouponSlipForm({
  catalog,
  knownMatches,
  legs,
  mode,
  stakeRaw,
  unitSize,
  currency,
  error,
  isSubmitting,
  onOddsChange,
  onRemove,
  onModeChange,
  onStakeChange,
  onSave,
}: CouponSlipFormProps) {
  return (
    <form onSubmit={(event) => event.preventDefault()} className="space-y-4">
      <DraftLegsList
        legs={legs}
        matches={knownMatches}
        events={catalog.events}
        isSubmitting={isSubmitting}
        onOddsChange={onOddsChange}
        onRemove={onRemove}
      />
      <CouponStakeFields
        legs={legs}
        mode={mode}
        stakeRaw={stakeRaw}
        unitSize={unitSize}
        currency={currency}
        isSubmitting={isSubmitting}
        onModeChange={onModeChange}
        onStakeChange={onStakeChange}
      />
      {error ? (
        <StatusMessage
          variant="error"
          title="Nie udało się dodać kuponu"
          message={error}
        />
      ) : null}
      <button
        type="button"
        disabled={isSubmitting || legs.length === 0}
        onClick={() => void onSave()}
        className={SUBMIT_BUTTON_CLASS_NAME}
      >
        {isSubmitting ? "Zapisywanie…" : "Dodaj kupon"}
      </button>
    </form>
  );
}

function draftLegErrorMessage(error: "duplicate_event" | "max_legs"): string {
  if (error === "max_legs") {
    return "Kupon może mieć maksymalnie 8 nóg.";
  }
  return "Ten event jest już na nodze tego meczu.";
}
