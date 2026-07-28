/**
 * Fail-closed startup checks for production frontend configuration.
 * Runs once when the Next.js server process starts.
 */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }

  const { assertSafeRuntimeConfig } = await import("@/lib/runtimeConfig");
  assertSafeRuntimeConfig();
}
