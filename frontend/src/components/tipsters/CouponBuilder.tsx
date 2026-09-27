"use client";

import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import { useRouter } from "next/navigation";

import { SUBMIT_BUTTON_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import { BetsPanel, BetsSubsection } from "@/components/tipsters/BetsPanel";
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
  applySuggestedLegOdds,
  buildCouponCreateRequest,
  isCombinedLeg,
  mergeCatalogMatches,
  removeEventFromDraftLegs,
  resolveCatalogMatchId,
  tipsterMutationMessage,
  updateDraftLegOdds,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import { usePickerCatalog } from "@/components/tipsters/usePickerCatalog";
import { createMyCoupon, getSuggestedCatalogOdds } from "@/lib/apiClient";
import { formatOdds } from "@/lib/format";
import type {
  CatalogMatch,
  CatalogMatchesResponse,
  CurrencyCode,
  StakeInputMode,
} from "@/types/api";

export const COUPON_BUILDER_TITLE = "Nowy kupon";
export const COUPON_BUILDER_DESCRIPTION =
  "Wybierz mecz i zdarzenie, ustaw kurs i stawkę. " +
  "Jeśli w bazie jest już kurs tego zdarzenia, pole wypełni się samo — możesz je zmienić.";
export const COUPON_BUILDER_HINT =
  "Drugie zdarzenie tego samego meczu łączy się z pierwszym. " +
  "Wpisz kurs łączony z bukmachera — nie iloczyn kursów i nie kurs pierwszego zdarzenia.";
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
  applyTax?: boolean;
}

export function CouponBuilder({
  catalog,
  favoriteLeagueIds,
  favoritesUnavailable = false,
  draftStorageKey,
  unitSize,
  currency,
  applyTax = false,
}: CouponBuilderProps) {
  const draft = useCouponDraft(catalog, favoriteLeagueIds, draftStorageKey);
  return (
    <BetsPanel
      title={COUPON_BUILDER_TITLE}
      description={COUPON_BUILDER_DESCRIPTION}
    >
      <BetsSubsection title="Katalog">
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
      </BetsSubsection>
      <CouponSlipForm
        catalog={catalog}
        knownMatches={draft.knownMatches}
        legs={draft.legs}
        mode={draft.mode}
        stakeRaw={draft.stakeRaw}
        unitSize={unitSize}
        currency={currency}
        applyTax={applyTax}
        error={draft.error}
        isSubmitting={draft.isSubmitting}
        onOddsChange={draft.handleOddsChange}
        onRemove={draft.handleRemove}
        onModeChange={draft.setMode}
        onStakeChange={draft.setStakeRaw}
        onSave={draft.handleSave}
      />
    </BetsPanel>
  );
}

type SuggestionTokens = MutableRefObject<Map<number, number>>;

function addCatalogEvent(
  legs: DraftCouponLeg[],
  matchId: number,
  eventId: number,
  tokens: SuggestionTokens,
  setLegs: Dispatch<SetStateAction<DraftCouponLeg[]>>,
  setError: Dispatch<SetStateAction<string | null>>,
): void {
  const result = addEventToDraftLegs(legs, matchId, eventId);
  if ("error" in result) {
    setError(draftLegErrorMessage(result.error));
    return;
  }
  setError(null);
  setLegs(result.legs);
  const added = result.legs.find((leg) => leg.matchId === matchId);
  if (!added || isCombinedLeg(added.eventIds)) {
    // kurs łączony wpisuje użytkownik; spóźniona podpowiedź nie może wrócić
    bumpSuggestionToken(tokens, matchId);
    return;
  }
  queueSuggestedOdds(matchId, eventId, tokens, setLegs);
}

function bumpSuggestionToken(
  tokens: SuggestionTokens,
  matchId: number,
): number {
  const nextToken = (tokens.current.get(matchId) ?? 0) + 1;
  tokens.current.set(matchId, nextToken);
  return nextToken;
}

function queueSuggestedOdds(
  matchId: number,
  eventId: number,
  tokens: SuggestionTokens,
  setLegs: Dispatch<SetStateAction<DraftCouponLeg[]>>,
): void {
  const token = bumpSuggestionToken(tokens, matchId);
  void getSuggestedCatalogOdds(matchId, eventId)
    .then((suggestion) => {
      if (tokens.current.get(matchId) !== token) {
        return;
      }
      const odds = suggestion.odds;
      if (odds === null) {
        return;
      }
      setLegs((current) =>
        applySuggestedLegOdds(current, matchId, eventId, formatOdds(odds)),
      );
    })
    .catch(() => {
      // brak podpowiedzi zostawia puste pole do ręcznego kursu
    });
}

function useCouponDraft(
  catalog: CatalogMatchesResponse,
  favoriteLeagueIds: number[],
  storageKey: string,
) {
  const router = useRouter();
  const picker = usePickerCatalog(catalog.matches, favoriteLeagueIds);
  const submittingRef = useRef(false);
  const suggestionTokens = useRef(new Map<number, number>());
  const [matchId, setMatchId] = useState(catalog.matches[0]?.id ?? 0);
  const [eventId, setEventId] = useState(catalog.events[0]?.id ?? 0);
  const [legs, setLegs] = useState<DraftCouponLeg[]>([]);
  const [mode, setMode] = useState<StakeInputMode>("money");
  const [stakeRaw, setStakeRaw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [restoredMatches, setRestoredMatches] = useState<CatalogMatch[]>([]);
  const knownMatches = mergeCatalogMatches(picker.knownMatches, restoredMatches);
  const selectedMatchId = useVisibleMatchId(picker, matchId, setMatchId);

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

  function handleAddEvent(nextEventId: number) {
    addCatalogEvent(
      legs,
      selectedMatchId,
      nextEventId,
      suggestionTokens,
      setLegs,
      setError,
    );
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
    matchId: selectedMatchId,
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
      applyPickerMatches(picker.changeDate(nextDate), selectedMatchId, setMatchId),
    handleAllLeaguesChange: (nextValue: boolean) =>
      applyPickerMatches(
        picker.changeIncludeAllLeagues(nextValue),
        selectedMatchId,
        setMatchId,
      ),
    handleOddsChange: (id: number, odds: string) =>
      setLegs(updateDraftLegOdds(legs, id, odds)),
    handleRemove: (id: number, eventIdToRemove: number) =>
      setLegs(removeEventFromDraftLegs(legs, id, eventIdToRemove)),
  };
}

function useVisibleMatchId(
  picker: { pickerMatches: CatalogMatch[]; matchQuery: string },
  matchId: number,
  setMatchId: (id: number) => void,
): number {
  const selectedMatchId = resolveCatalogMatchId(
    picker.pickerMatches,
    picker.matchQuery,
    matchId,
  );
  useEffect(() => {
    if (selectedMatchId !== matchId) {
      setMatchId(selectedMatchId);
    }
  }, [selectedMatchId, matchId, setMatchId]);
  return selectedMatchId;
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
  applyTax: boolean;
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
  applyTax,
  error,
  isSubmitting,
  onOddsChange,
  onRemove,
  onModeChange,
  onStakeChange,
  onSave,
}: CouponSlipFormProps) {
  return (
    <form onSubmit={(event) => event.preventDefault()} className="space-y-5">
      <BetsSubsection
        title="Zdarzenia na kuponie"
        description={COUPON_BUILDER_HINT}
        divided
      >
        <DraftLegsList
          legs={legs}
          matches={knownMatches}
          events={catalog.events}
          isSubmitting={isSubmitting}
          onOddsChange={onOddsChange}
          onRemove={onRemove}
        />
      </BetsSubsection>
      <BetsSubsection title="Stawka" divided>
        <CouponStakeFields
          legs={legs}
          mode={mode}
          stakeRaw={stakeRaw}
          unitSize={unitSize}
          currency={currency}
          applyTax={applyTax}
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
      </BetsSubsection>
    </form>
  );
}

function draftLegErrorMessage(error: "duplicate_event" | "max_legs"): string {
  if (error === "max_legs") {
    return "Kupon może mieć maksymalnie 8 zdarzeń.";
  }
  return "To zdarzenie jest już dodane do tego meczu.";
}
