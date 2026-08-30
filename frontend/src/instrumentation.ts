import { WARSAW_TIME_ZONE } from "@/lib/date";

process.env.TZ = WARSAW_TIME_ZONE;

/**
 * Fail-closed startup checks for production frontend configuration.
 * Runs once when the Next.js server process starts.
 */
export async function register(): Promise<void> {
  process.env.TZ = WARSAW_TIME_ZONE;
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }

  const { assertSafeRuntimeConfig } = await import("@/lib/runtimeConfig");
  assertSafeRuntimeConfig();
}
