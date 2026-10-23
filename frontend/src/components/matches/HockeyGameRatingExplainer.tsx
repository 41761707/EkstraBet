import { ExpandableSection } from "@/components/ExpandableSection";

const INTRO =
  "Ocena 5 jest oceną wyjściową dla każdego zawodnika. Wartości powyżej oznaczają występ lepszy od średniej, natomiast wartości poniżej - gorszy. " +
  "Aspekty gry ofensywny jak i defensywne liczone są osobno na podstawie różnych aspektów gry."

const ROUNDING =
  "Każdy składnik zaokrąglamy do jednego miejsca po przecinku."

const EXCLUDED =
  "Aktualnie algorytm nie bierze pod uwagę uderzeń, czasu na lodzie i celności strzałów.";

const GOALIE =
  "Ocena bramkarza liczona jest inaczej, zgodnie z następujących schematem: Bierzemy skuteczność obron z sezonu, " +
  "na przykład 90.7%, i mnożymy ją przez strzały na bramkę w tym meczu. " +
  "Na tej podstawie obliczamy, ile obron oczekujemy od bramkarza w danym meczu. " +
  "Każda obrona powyżej tej liczby dodaje 1.0, a każda poniżej odejmuje 1.0. " +
  "Przy 30 strzałach oczekujemy 27.2 obrony, więc 30 obron daje +2.8.";

interface RatingWeightRow {
  item: string;
  counted: string;
  weight: string;
}

const OFFENSE_WEIGHTS: readonly RatingWeightRow[] = [
  { item: "Gol", counted: "każdy gol", weight: "+1.0" },
  { item: "Asysta", counted: "każda asysta", weight: "+1.0" },
  {
    item: "Strzał",
    counted: "strzał celny, który nie jest golem",
    weight: "+0.1",
  },
  {
    item: "Gol kolegi",
    counted: "plus/minus powyżej punktów (liczone w grze w równowadze)",
    weight: "+0.2",
  },
  {
    item: "Wznowienie",
    counted: "wygrane minus przegrane",
    weight: "+0.02",
  },
  {
    item: "Pusta bramka",
    counted: "gol do pustej bramki",
    weight: "−0.3",
  },
];

const DEFENSE_WEIGHTS: readonly RatingWeightRow[] = [
  {
    item: "Bramka stracona",
    counted:
      "punkty w grze równej powyżej plus/minus. Gol w przewadze się nie liczy",
    weight: "−0.35",
  },
  { item: "Kara mniejsza", counted: "każda kara 2 minuty", weight: "−0.15" },
  { item: "Kara większa", counted: "każda kara 5 minut", weight: "−0.3" },
  {
    item: "Blok",
    counted: "każdy zablokowany strzał",
    weight: "+0.1",
  },
  {
    item: "Bramkarz",
    counted: "obrony powyżej albo poniżej liczby z sezonu",
    weight: "+1.0",
  },
];

const EXAMPLE_ROWS: readonly {
  night: string;
  included: string;
  rating: string;
}[] = [
  {
    night: "1 gol, 2 asysty, 4 strzały celne, plus/minus +3",
    included: "Produkcja +3.0, trzy strzały poza golem +0.3, defensywa 0.0",
    rating: "8.3",
  },
  {
    night: "Te same punkty, plus/minus −1",
    included: "Ta sama ofensywa +3.3, cztery bramki stracone −1.4",
    rating: "6.9",
  },
  {
    night: "Bramkarz, 30 obron z 30 strzałów",
    included: "Sezon 90.7% razy 30 strzałów to 27.2 oczekiwanej obrony. Zostało +2,8",
    rating: "7.8",
  },
];

/** Static weights and three nights. It does not calculate a rating. */
export function HockeyGameRatingExplainer() {
  return (
    <ExpandableSection title="Jak liczymy ocenę">
      <div className="space-y-3">
        <p>{INTRO}</p>
        <RatingWeightTable title="Ofensywa" rows={OFFENSE_WEIGHTS} />
        <RatingWeightTable title="Defensywa" rows={DEFENSE_WEIGHTS} />
        <GoalieNote />
        <p>{ROUNDING}</p>
        <ExampleNightsTable />
        <p>{EXCLUDED}</p>
      </div>
    </ExpandableSection>
  );
}

function GoalieNote() {
  return (
    <div className="space-y-2">
      <p className="font-medium text-text">Bramkarz</p>
      <table className="w-full border border-border text-sm">
        <tbody>
          <tr>
            <td className="px-3 py-2 text-text">{GOALIE}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function RatingWeightTable({
  title,
  rows,
}: {
  title: string;
  rows: readonly RatingWeightRow[];
}) {
  return (
    <div className="space-y-2">
      <p className="font-medium text-text">{title}</p>
      <table className="w-full border border-border text-sm">
        <thead className="text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Składnik</th>
            <th className="px-3 py-2 font-medium">Liczymy</th>
            <th className="px-3 py-2 font-medium">Za jedną sztukę</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.item} className="border-t border-border">
              <td className="px-3 py-2 text-text">{row.item}</td>
              <td className="px-3 py-2 text-text">{row.counted}</td>
              <td className="px-3 py-2 text-text">{row.weight}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExampleNightsTable() {
  return (
    <table className="w-full border border-border text-sm">
      <thead className="text-left text-muted">
        <tr>
          <th className="px-3 py-2 font-medium">Noc</th>
          <th className="px-3 py-2 font-medium">Co weszło</th>
          <th className="px-3 py-2 font-medium">Ocena</th>
        </tr>
      </thead>
      <tbody>
        {EXAMPLE_ROWS.map((row) => (
          <tr key={row.night} className="border-t border-border">
            <td className="px-3 py-2 text-text">{row.night}</td>
            <td className="px-3 py-2 text-text">{row.included}</td>
            <td className="px-3 py-2 text-text">{row.rating}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
