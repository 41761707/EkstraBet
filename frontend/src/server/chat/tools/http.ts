import { getApiBaseUrl, getServerAuthHeaders } from "@/lib/auth";

export type PrimitiveParam = string | number | boolean | null | undefined;

export function buildUrl(
  path: string,
  params?: Record<string, PrimitiveParam>,
): string {
  const url = new URL(path, getApiBaseUrl());
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export async function fetchReadOnly<T>(
  path: string,
  params?: Record<string, PrimitiveParam>,
): Promise<T> {
  const authHeaders = await getServerAuthHeaders();
  const response = await fetch(buildUrl(path, params), {
    headers: {
      Accept: "application/json",
      ...authHeaders,
    },
    cache: "no-store",
    signal: AbortSignal.timeout(12_000),
  });

  if (!response.ok) {
    throw new Error(`Read-only API request failed: GET ${path}`);
  }

  return response.json() as Promise<T>;
}

export function getEndpoint(path: string): string {
  return `GET ${path}`;
}
