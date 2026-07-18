export function parsePositiveInt(value: string | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

export function parseIdList(value: string | undefined): number[] {
  if (!value?.trim()) {
    return [];
  }
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((id) => Number.isInteger(id) && id > 0);
}

export function serializeIdList(ids: number[]): string | undefined {
  if (ids.length === 0) {
    return undefined;
  }
  return ids.join(",");
}

export function parseBoolean(
  value: string | undefined,
  defaultValue = false,
): boolean {
  if (value === undefined) {
    return defaultValue;
  }
  return value === "true" || value === "1";
}

export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}
