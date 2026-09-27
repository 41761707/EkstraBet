import { ApplyTaxToggle } from "@/components/tipsters/ApplyTaxToggle";
import { BankrollSetupForm } from "@/components/tipsters/BankrollSetupForm";
import { BetsPanel } from "@/components/tipsters/BetsPanel";
import { CouponBuilder } from "@/components/tipsters/CouponBuilder";
import { CouponHistoryTable } from "@/components/tipsters/CouponHistoryTable";
import { PerformanceBreakdown } from "@/components/tipsters/PerformanceBreakdown";
import { TopUpForm } from "@/components/tipsters/TopUpForm";
import { ProfileSection } from "@/components/profile/ProfileSection";
import { StatusMessage } from "@/components/StatusMessage";
import { couponDraftStorageKey } from "@/components/tipsters/couponDraftStorage";
import { parseBoolean } from "@/lib/searchParams";
import {
  formatTipsterAmount,
  formatTipsterProfit,
  isOwnerBankroll,
  isPublicCouponHistoryVisible,
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
  "Własne kupony, kapitał i rozliczenia na podstawie statystyk meczu.";
export const PUBLIC_COUPONS_TITLE = "Kupony";
export const SYSTEM_COUPONS_DESCRIPTION =
  "Publiczna historia kuponów konta systemowego.";
export const PUBLIC_BANKROLL_TITLE = "Kapitał";
export const BANKROLL_LOAD_ERROR_TITLE = "Nie udało się wczytać kapitału";
export const BANKROLL_SUMMARY_TITLE = "Podsumowanie";
export const PUBLIC_BANKROLL_DESCRIPTION =
  "Publiczne saldo. Lista kuponów tego użytkownika jest prywatna.";
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
  draftStorageKey?: string;
}

export function MyBetsSection(props: MyBetsSectionProps) {
  const copy = myBetsSectionCopy(props.isOwnProfile, props.isSystemProfile);
  return (
    <ProfileSection title={copy.title} description={copy.description}>
      <MyBetsContent {...props} />
    </ProfileSection>
  );
}

/** Bankroll, creator and history without the profile-card chrome. */
export function MyBetsContent(props: MyBetsSectionProps) {
  const applyTax = parseBoolean(props.searchParams.apply_tax);
  return (
    <div className="space-y-8">
      <ApplyTaxToggle
        checked={applyTax}
        pathname={props.profilePath}
        searchParams={props.searchParams}
      />
      {props.isOwnProfile ? (
        <OwnBetsBody {...props} applyTax={applyTax} />
      ) : (
        <PublicBetsBody {...props} />
      )}
    </div>
  );
}

function myBetsSectionCopy(isOwnProfile: boolean, isSystemProfile: boolean) {
  if (isOwnProfile) {
    return { title: MY_BETS_TITLE, description: MY_BETS_DESCRIPTION };
  }
  if (isPublicCouponHistoryVisible(isOwnProfile, isSystemProfile)) {
    return {
      title: PUBLIC_COUPONS_TITLE,
      description: SYSTEM_COUPONS_DESCRIPTION,
    };
  }
  return {
    title: PUBLIC_BANKROLL_TITLE,
    description: PUBLIC_BANKROLL_DESCRIPTION,
  };
}

function OwnBetsBody(props: MyBetsSectionProps & { applyTax: boolean }) {
  const ownerBankroll = isOwnerBankroll(props.bankroll) ? props.bankroll : null;
  const hasCoupons = (props.coupons?.total ?? 0) > 0;
  const currency = ownerBankroll?.currency ?? "PLN";

  return (
    <>
      {props.bankrollError ? (
        <StatusMessage
          variant="error"
          title={BANKROLL_LOAD_ERROR_TITLE}
          message={props.bankrollError}
        />
      ) : null}
      {ownerBankroll ? (
        <BetsPanel title={BANKROLL_SUMMARY_TITLE}>
          <BankrollSummary bankroll={ownerBankroll} />
        </BetsPanel>
      ) : props.bankrollError ? null : (
        <BankrollSetupForm existing={null} hasCoupons={false} />
      )}
      {ownerBankroll ? (
        <OwnerCreator
          {...props}
          bankroll={ownerBankroll}
          applyTax={props.applyTax}
        />
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
      {ownerBankroll ? (
        <OwnerCapitalActions
          bankroll={ownerBankroll}
          hasCoupons={hasCoupons}
        />
      ) : null}
    </>
  );
}

function PublicBetsBody(props: MyBetsSectionProps) {
  const currency = props.bankroll?.currency ?? "PLN";
  const showCouponHistory = isPublicCouponHistoryVisible(
    false,
    props.isSystemProfile,
  );
  return (
    <>
      <PublicBankrollSummary bankroll={props.bankroll} />
      {showCouponHistory ? (
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
      ) : null}
    </>
  );
}

interface OwnerBankrollPanelProps {
  bankroll: BankrollSettings;
  hasCoupons: boolean;
}

function OwnerCapitalActions({
  bankroll,
  hasCoupons,
}: OwnerBankrollPanelProps) {
  return (
    <>
      <BankrollSetupForm existing={bankroll} hasCoupons={hasCoupons} />
      <TopUpForm currency={bankroll.currency} />
    </>
  );
}

interface OwnerCreatorProps extends MyBetsSectionProps {
  bankroll: BankrollSettings;
  applyTax: boolean;
}

function OwnerCreator(props: OwnerCreatorProps) {
  return (
    <>
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
          draftStorageKey={
            props.draftStorageKey ?? couponDraftStorageKey(props.profilePath)
          }
          unitSize={props.bankroll.unit_size}
          currency={props.bankroll.currency}
          applyTax={props.applyTax}
        />
      ) : null}
    </>
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
  const currency = bankroll.currency;
  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,2fr)]">
      <SummaryItem
        label="Aktualne saldo"
        value={formatTipsterAmount(bankroll.current_balance, currency)}
        featured
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <SummaryItem
          label="Kapitał startowy"
          value={formatTipsterAmount(bankroll.initial_capital, currency)}
        />
        <SummaryItem
          label="Jednostka (unit)"
          value={formatTipsterAmount(bankroll.unit_size, currency)}
        />
        <SummaryItem
          label="W obiegu"
          value={formatTipsterAmount(bankroll.open_stake, currency)}
        />
        <SummaryItem
          label="Zysk"
          value={formatTipsterProfit(bankroll.realized_pnl, currency)}
        />
      </div>
    </div>
  );
}

function PublicBankrollSummary({
  bankroll,
}: {
  bankroll: BankrollSettings | PublicBankroll | null;
}) {
  if (!bankroll) {
    return (
      <BetsPanel title={BANKROLL_SUMMARY_TITLE}>
        <StatusMessage
          variant="empty"
          title="Brak kapitału"
          message="To konto nie ma jeszcze skonfigurowanego kapitału."
        />
      </BetsPanel>
    );
  }

  return (
    <BetsPanel title={BANKROLL_SUMMARY_TITLE}>
      <div className="grid gap-3 sm:grid-cols-2">
        <SummaryItem
          label="Saldo"
          value={formatTipsterAmount(bankroll.current_balance, bankroll.currency)}
          featured
        />
        <SummaryItem label="Waluta" value={bankroll.currency} />
      </div>
    </BetsPanel>
  );
}

function SummaryItem({
  label,
  value,
  featured = false,
}: {
  label: string;
  value: string;
  featured?: boolean;
}) {
  const className = featured
    ? "flex h-full flex-col justify-center rounded-xl border border-border " +
      "bg-accent-soft px-5 py-5"
    : "flex h-full flex-col justify-center rounded-lg border border-border " +
      "bg-surface-raised px-4 py-3";
  const valueClassName = featured
    ? "mt-1 text-3xl font-semibold tracking-tight text-text"
    : "mt-1 text-lg font-semibold text-text";
  return (
    <div className={className}>
      <p className="text-sm text-muted">{label}</p>
      <p className={valueClassName}>{value}</p>
    </div>
  );
}
