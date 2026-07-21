export function normalizeSearchText(value: string): string {
  return value
    .toLocaleLowerCase("pl")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export function normalizeSeasonYears(value: string): string | null {
  const years = value.match(/\d{2,4}/g);
  if (!years || years.length < 2) {
    return null;
  }

  const firstYear = Number(years[0].length === 2 ? `20${years[0]}` : years[0]);
  const secondYear =
    years[1].length === 2
      ? Math.floor(firstYear / 100) * 100 + Number(years[1])
      : Number(years[1]);
  if (!Number.isInteger(firstYear) || !Number.isInteger(secondYear)) {
    return null;
  }

  return `${firstYear}/${secondYear}`;
}

export function isSeasonYearsMatch(actual: string, expected: string): boolean {
  const normalizedActual = normalizeSearchText(actual);
  const normalizedExpected = normalizeSearchText(expected);
  const actualSeason = normalizeSeasonYears(actual);
  const expectedSeason = normalizeSeasonYears(expected);
  return (
    Boolean(actualSeason && expectedSeason && actualSeason === expectedSeason) ||
    normalizedActual === normalizedExpected ||
    normalizedActual.replace(/\s/g, "") ===
      normalizedExpected.replace(/\s/g, "")
  );
}
