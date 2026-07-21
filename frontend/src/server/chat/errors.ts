/** Chat API error classes with HTTP status mapping. */

/** Timeout for OpenRouter fetch and Cursor Agent.prompt (30–60s band). */
export const LLM_REQUEST_TIMEOUT_MS = 45_000;

export class ChatRequestError extends Error {
  readonly status = 400 as const;

  constructor(message: string) {
    super(message);
    this.name = "ChatRequestError";
  }
}

export class ChatRateLimitError extends Error {
  readonly status = 429 as const;
  readonly retryAfterSec: number;

  constructor(message: string, retryAfterSec: number) {
    super(message);
    this.name = "ChatRateLimitError";
    this.retryAfterSec = retryAfterSec;
  }
}

export class ChatProviderError extends Error {
  readonly status = 502 as const;

  constructor(message: string) {
    super(message);
    this.name = "ChatProviderError";
  }
}

export function isTimeoutError(error: unknown): boolean {
  return (
    error instanceof Error &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

/**
 * Race a provider promise against a wall-clock timeout.
 * Does not cancel the underlying SDK call, but unblocks the Node worker.
 */
export async function withProviderTimeout<T>(
  promise: Promise<T>,
  timeoutMessage: string,
  timeoutMs: number = LLM_REQUEST_TIMEOUT_MS,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          reject(new ChatProviderError(timeoutMessage));
        }, timeoutMs);
      }),
    ]);
  } finally {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  }
}

export function chatErrorResponse(error: unknown): {
  body: { detail: string };
  status: number;
  headers?: HeadersInit;
} {
  if (error instanceof ChatRequestError) {
    return { body: { detail: error.message }, status: error.status };
  }
  if (error instanceof ChatRateLimitError) {
    return {
      body: { detail: error.message },
      status: error.status,
      headers: { "Retry-After": String(error.retryAfterSec) },
    };
  }
  if (error instanceof ChatProviderError) {
    return { body: { detail: error.message }, status: error.status };
  }
  const message =
    error instanceof Error ? error.message : "Unexpected chat route error.";
  return { body: { detail: message }, status: 500 };
}
