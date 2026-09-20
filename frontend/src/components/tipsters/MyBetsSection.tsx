import { BankrollSetupForm } from "@/components/tipsters/BankrollSetupForm";
import { CouponBuilder } from "@/components/tipsters/CouponBuilder";
import { CouponHistoryTable } from "@/components/tipsters/CouponHistoryTable";
import { PerformanceBreakdown } from "@/components/tipsters/PerformanceBreakdown";
import { TopUpForm } from "@/components/tipsters/TopUpForm";
import { ProfileSection } from "@/components/profile/ProfileSection";
import { StatusMessage } from "@/components/StatusMessage";
import { couponDraftStorageKey } from "@/components/tipsters/couponDraftStorage";
import {
  formatTipsterAmount,
  formatTipsterProfit,
  isOwnerBankroll,
} from "@/components/tipsters/tipsterModel";
import type {
  BankrollSettings,
  CatalogMatchesResponse,
  CouponPage,
  CurrencyCode,
  PerformanceBreakdown as TipsterPerformance,
  PublicBankroll,
} from "@/types/api";

export const MY_BETS_TITLE = "Moje zakłady";
export const MY_BETS_DESCRIPTION =
  "Własne kupony, bankroll i rozliczenia z boxscore meczu.";
export const PUBLIC_COUPONS_TITLE = "Kupony";
export const PUBLIC_COUPONS_DESCRIPTION =
  "Publiczna historia kuponów tego użytkownika.";
export const SYSTEM_COUPONS_DESCRIPTION =
  "Publiczna historia kuponów konta systemowego.";
export const CATALOG_LOAD_ERROR_TITLE = "Nie udało się wczytać katalogu";

interface MyBetsSectionProps {
  isOwnProfile: boolean;
  isSystemProfile: boolean;
  bankroll: BankrollSettings | PublicBankroll | null;
  bankrollError?: string;
  coupons: CouponPage | null;
  couponsError?: string;
  performance: TipsterPerformance | null;
  performanceError?: string;
  catalog: CatalogMatchesResponse | null;
  catalogError?: string;
  favoriteLeagueIds?: number[];
  favoritesUnavailable?: boolean;
  profilePath: string;
  searchParams: Record<string, string | undefined>;
}

export function MyBetsSection(props: MyBetsSectionProps) {
  const copy = myBetsSectionCopy(props.isOwnProfile, props.isSystemProfile);
  return (
    <ProfileSection title={copy.title} description={copy.description}>
      <div className="space-y-6">
        {props.isOwnProfile ? (
          <OwnBetsBody {...props} />
        ) : (
          <PublicBetsBody {...props} />
        )}
      </div>
    </ProfileSection>
  );
}

function myBetsSectionCopy(isOwnProfile: boolean, isSystemProfile: boolean) {
  if (isOwnProfile) {
    return { title: MY_BETS_TITLE, description: MY_BETS_DESCRIPTION };
  }
  if (isSystemProfile) {
    return {
      title: PUBLIC_COUPONS_TITLE,
      description: SYSTEM_COUPONS_DESCRIPTION,
    };
  }
  return {
    title: PUBLIC_COUPONS_TITLE,
    description: PUBLIC_COUPONS_DESCRIPTION,
  };
}

function OwnBetsBody(props: MyBetsSectionProps) {
  const ownerBankroll = isOwnerBankroll(props.bankroll) ? props.bankroll : null;
  const hasCoupons = (props.coupons?.total ?? 0) > 0;
  const currency = ownerBankroll?.currency ?? "PLN";

  return (
    <>
      {props.bankrollError ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać bankrolla"
          message={props.bankrollError}
        />
      ) : null}
      {ownerBankroll ? (
        <OwnerBankrollPanel
          bankroll={ownerBankroll}
          hasCoupons={hasCoupons}
        />
      ) : props.bankrollError ? null : (
        <BankrollSetupForm existing={null} hasCoupons={false} />
      )}
      {ownerBankroll ? (
        <OwnerCreator {...props} bankroll={ownerBankroll} />
      ) : null}
      <CouponsAndPerformance
        coupons={props.coupons}
        couponsError={props.couponsError}
        performance={props.performance}
        performanceError={props.performanceError}
        profilePath={props.profilePath}
        searchParams={props.searchParams}
        currency={currency}
        isOwnProfile
        isSystemProfile={props.isSystemProfile}
      />
    </>
  );
}

function PublicBetsBody(props: MyBetsSectionProps) {
  const currency = props.bankroll?.currency ?? "PLN";
  return (
    <>
      <PublicBankrollSummary bankroll={props.bankroll} />
      <CouponsAndPerformance
        coupons={props.coupons}
        couponsError={props.couponsError}
        performance={props.performance}
        performanceError={props.performanceError}
        profilePath={props.profilePath}
        searchParams={props.searchParams}
        currency={currency}
        isOwnProfile={false}
        isSystemProfile={props.isSystemProfile}
      />
    </>
  );
}

interface OwnerBankrollPanelProps {
  bankroll: BankrollSettings;
  hasCoupons: boolean;
}

function OwnerBankrollPanel({
  bankroll,
  hasCoupons,
}: OwnerBankrollPanelProps) {
  return (
    <div className="space-y-4">
      <BankrollSummary bankroll={bankroll} />
      <BankrollSetupForm existing={bankroll} hasCoupons={hasCoupons} />
      <TopUpForm currency={bankroll.currency} />
    </div>
  );
}

interface OwnerCreatorProps extends MyBetsSectionProps {
  bankroll: BankrollSettings;
}

function OwnerCreator(props: OwnerCreatorProps) {
  return (
    <div className="space-y-6">
      {props.catalogError ? (
        <StatusMessage
          variant="error"
          title={CATALOG_LOAD_ERROR_TITLE}
          message={props.catalogError}
        />
      ) : props.catalog ? (
        <CouponBuilder
          catalog={props.catalog}
          favoriteLeagueIds={props.favoriteLeagueIds ?? []}
          favoritesUnavailable={props.favoritesUnavailable ?? false}
          draftStorageKey={couponDraftStorageKey(props.profilePath)}
          unitSize={props.bankroll.unit_size}
          currency={props.bankroll.currency}
        />
      ) : null}
    </div>
  );
}

interface CouponsAndPerformanceProps {
  coupons: CouponPage | null;
  couponsError?: string;
  performance: TipsterPerformance | null;
  performanceError?: string;
  profilePath: string;
  searchParams: Record<string, string | undefined>;
  currency: CurrencyCode;
  isOwnProfile: boolean;
  isSystemProfile: boolean;
}

function CouponsAndPerformance({
  coupons,
  couponsError,
  performance,
  performanceError,
  profilePath,
  searchParams,
  currency,
  isOwnProfile,
  isSystemProfile,
}: CouponsAndPerformanceProps) {
  return (
    <>
      {couponsError ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać kuponów"
          message={couponsError}
        />
      ) : coupons ? (
        <CouponHistoryTable
          coupons={coupons}
          currency={currency}
          profilePath={profilePath}
          searchParams={searchParams}
          isOwnProfile={isOwnProfile}
          isSystemProfile={isSystemProfile}
        />
      ) : null}
      {performanceError ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać analityki"
          message={performanceError}
        />
      ) : performance ? (
        <PerformanceBreakdown data={performance} currency={currency} />
      ) : null}
    </>
  );
}

function BankrollSummary({ bankroll }: { bankroll: BankrollSettings }) {
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
      <SummaryItem
        label="Saldo"
        value={formatTipsterAmount(bankroll.current_balance, bankroll.currency)}
      />
      <SummaryItem
        label="Kapitał startowy"
        value={formatTipsterAmount(bankroll.initial_capital, bankroll.currency)}
      />
      <SummaryItem
        label="Unit"
        value={formatTipsterAmount(bankroll.unit_size, bankroll.currency)}
      />
      <SummaryItem
        label="Otwarta stawka"
        value={formatTipsterAmount(bankroll.open_stake, bankroll.currency)}
      />
      <SummaryItem
        label="Zrealizowany PnL"
        value={formatTipsterProfit(bankroll.realized_pnl, bankroll.currency)}
      />
    </dl>
  );
}

function PublicBankrollSummary({
  bankroll,
}: {
  bankroll: BankrollSettings | PublicBankroll | null;
}) {
  if (!bankroll) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak bankrolla"
        message="To konto nie ma jeszcze skonfigurowanego bankrolla."
      />
    );
  }

  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      <SummaryItem
        label="Saldo"
        value={formatTipsterAmount(bankroll.current_balance, bankroll.currency)}
      />
      <SummaryItem label="Waluta" value={bankroll.currency} />
    </dl>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted px-3 py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-text">{value}</dd>
    </div>
  );
}
