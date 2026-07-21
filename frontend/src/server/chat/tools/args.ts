export function numberArg(
  args: Record<string, unknown>,
  key: string,
  options?: { required?: boolean; min?: number; max?: number },
): number | undefined {
  const value = args[key];
  if (value === undefined || value === null || value === "") {
    if (options?.required) {
      throw new Error(`Missing required argument: ${key}`);
    }
    return undefined;
  }

  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed)) {
    throw new Error(`Argument ${key} must be an integer`);
  }
  if (options?.min !== undefined && parsed < options.min) {
    throw new Error(`Argument ${key} must be at least ${options.min}`);
  }
  if (options?.max !== undefined && parsed > options.max) {
    throw new Error(`Argument ${key} must be at most ${options.max}`);
  }
  return parsed;
}

export function stringArg(
  args: Record<string, unknown>,
  key: string,
  options?: { required?: boolean; maxLength?: number },
): string | undefined {
  const value = args[key];
  if (value === undefined || value === null || value === "") {
    if (options?.required) {
      throw new Error(`Missing required argument: ${key}`);
    }
    return undefined;
  }
  if (typeof value !== "string") {
    throw new Error(`Argument ${key} must be a string`);
  }
  return value.slice(0, options?.maxLength ?? 120);
}

export function booleanArg(
  args: Record<string, unknown>,
  key: string,
): boolean | undefined {
  const value = args[key];
  return typeof value === "boolean" ? value : undefined;
}

export function enumArg<T extends string>(
  args: Record<string, unknown>,
  key: string,
  allowed: readonly T[],
  fallback: T,
): T {
  const value = args[key];
  return typeof value === "string" && allowed.includes(value as T)
    ? (value as T)
    : fallback;
}
