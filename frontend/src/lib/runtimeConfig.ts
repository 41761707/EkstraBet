import "server-only";

/** Server-only frontend runtime env helpers (never import from Client Components). */

export const DEFAULT_API_BASE_URL = "http://localhost:8000";

export type AppEnvironment = "development" | "production" | "test";

export function getAppEnvironment(): AppEnvironment {
  const raw = (process.env.ENVIRONMENT ?? "development").trim().toLowerCase();
  if (raw === "production" || raw === "test") {
    return raw;
  }
  return "development";
}

export function isProductionEnvironment(): boolean {
  return getAppEnvironment() === "production";
}

/**
 * Uses only API_BASE_URL in production so NEXT_PUBLIC_* never becomes the
 * server-side source of truth for the FastAPI address.
 */
export function getApiBaseUrl(): string {
  if (isProductionEnvironment()) {
    const productionUrl = process.env.API_BASE_URL?.trim();
    if (!productionUrl) {
      throw new Error("API_BASE_URL is required when ENVIRONMENT=production");
    }
    return productionUrl.replace(/\/$/, "");
  }

  const configured =
    process.env.API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    DEFAULT_API_BASE_URL;
  return configured.replace(/\/$/, "");
}

/** Public app origin used to validate mutating BFF requests. */
export function getAppOrigin(): string | null {
  const raw = process.env.APP_ORIGIN?.trim();
  return raw ? raw.replace(/\/$/, "") : null;
}

/** Whether auth cookies should use the Secure attribute. */
export function isSecureAuthCookie(): boolean {
  return isProductionEnvironment() || process.env.NODE_ENV === "production";
}

/**
 * Collect critical production misconfigurations.
 * Empty list means the process may start.
 */
export function collectProductionConfigErrors(
  env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env,
): string[] {
  const errors: string[] = [];
  const environment = (env.ENVIRONMENT ?? "").trim().toLowerCase();
  if (environment !== "production") {
    return errors;
  }

  const authEnabled = (env.AUTH_ENABLED ?? "true").trim().toLowerCase();
  if (
    authEnabled === "false" ||
    authEnabled === "0" ||
    authEnabled === "no" ||
    authEnabled === "off"
  ) {
    errors.push("AUTH_ENABLED must be true in production");
  }

  const appOrigin = env.APP_ORIGIN?.trim() ?? "";
  if (!appOrigin) {
    errors.push("APP_ORIGIN is required in production");
  } else {
    try {
      const parsed = new URL(appOrigin);
      if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
        errors.push("APP_ORIGIN must be an http(s) origin");
      }
      if (appOrigin.endsWith("/")) {
        errors.push("APP_ORIGIN must not end with a trailing slash");
      }
    } catch {
      errors.push("APP_ORIGIN must be a valid absolute origin URL");
    }
  }

  const apiBaseUrl = env.API_BASE_URL?.trim() ?? "";
  if (!apiBaseUrl) {
    errors.push("API_BASE_URL is required in production");
  }

  const publicApi = env.NEXT_PUBLIC_API_BASE_URL?.trim() ?? "";
  if (publicApi) {
    errors.push(
      "NEXT_PUBLIC_API_BASE_URL must not be set in production (use BFF only)",
    );
  }

  const cookieName = env.AUTH_COOKIE_NAME?.trim() ?? "";
  if (!cookieName) {
    errors.push("AUTH_COOKIE_NAME is required in production");
  }

  if (isEnvFlagEnabled(env.CHAT_ENABLE_CURSOR)) {
    errors.push("CHAT_ENABLE_CURSOR must be false in production");
  }
  if (isEnvFlagEnabled(env.NEXT_PUBLIC_CHAT_ENABLE_CURSOR)) {
    errors.push(
      "NEXT_PUBLIC_CHAT_ENABLE_CURSOR must be false in production",
    );
  }

  return errors;
}

/** True for common truthy env flag strings (true/1/yes/on). */
function isEnvFlagEnabled(raw: string | undefined): boolean {
  const value = (raw ?? "").trim().toLowerCase();
  return (
    value === "true" || value === "1" || value === "yes" || value === "on"
  );
}

/** Throw when production configuration is unsafe (fail-closed). */
export function assertSafeRuntimeConfig(
  env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env,
): void {
  const errors = collectProductionConfigErrors(env);
  if (errors.length === 0) {
    return;
  }
  throw new Error(`Unsafe production configuration: ${errors.join("; ")}`);
}
