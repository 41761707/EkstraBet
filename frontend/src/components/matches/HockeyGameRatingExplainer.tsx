import { ExpandableSection } from "@/components/ExpandableSection";

const INTRO =
  "Liczba jest w skali punktów z protokołu. " +
  "Ofensywa i defensywa sumują się do oceny ogólnej. " +
  "Skali nie przycinamy.";

const ROUNDING =
  "Każdy składnik zaokrąglamy do jednego miejsca po przecinku i dopiero potem sumujemy. " +
  "Jeden minor (−0.15) na karcie jest −0.2, a dwa minory (−0.30) są −0.3.";

const EXCLUDED =
  "Nie wchodzą hity, czas na lodzie i celność strzałów.";

const GOALIE =
  "Bramkarza liczymy inaczej. Bierzemy skuteczność obron z sezonu, " +
  "na przykład 90,7%, i mnożymy ją przez strzały na bramkę w tym meczu. " +
  "Wychodzi, ile obron powinien mieć. " +
  "Każda obrona powyżej tej liczby dodaje 1.0, a każda poniżej odejmuje 1.0. " +
  "Przy 30 strzałach oczekujemy 27,2 obrony, więc 30 obron daje +2,8.";

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
    weight: "+0.10",
  },
  {
    item: "Gol kolegi",
    counted: "plus/minus powyżej punktów w grze równej",
    weight: "+0.20",
  },
  {
    item: "Wznowienie",
    counted: "wygrane minus przegrane",
    weight: "+0.02",
  },
  {
    item: "Pusta bramka",
    counted: "gol do pustej bramki",
    weight: "−0.30",
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
  { item: "Kara większa", counted: "każda kara 5 minut", weight: "−0.30" },
  {
    item: "Blok",
    counted: "każdy zablokowany strzał",
    weight: "+0.10",
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
    rating: "+3.3",
  },
  {
    night: "Te same punkty, plus/minus −1",
    included: "Ta sama ofensywa +3.3, cztery bramki stracone −1.4",
    rating: "+1.9",
  },
  {
    night: "Bramkarz, 30 obron z 30 strzałów",
    included: "Sezon 90,7% razy 30 strzałów to 27,2 oczekiwanej obrony. Zostało +2,8",
    rating: "+2.8",
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
        <p>{GOALIE}</p>
        <p>{ROUNDING}</p>
        <ExampleNightsTable />
        <p>{EXCLUDED}</p>
      </div>
    </ExpandableSection>
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
