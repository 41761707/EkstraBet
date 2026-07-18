/**
 * Decode dynamic route params that may still contain percent-encoding.
 */
export function decodeRouteParam(value: string): string {
  let decoded = value;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const next = decodeURIComponent(decoded.replace(/\+/g, " "));
      if (next === decoded) {
        break;
      }
      decoded = next;
    } catch {
      break;
    }
  }

  return decoded;
}

export function leaguePath(
  slug: string,
  query?: Record<string, string | number | undefined | null>,
): string {
  const params = new URLSearchParams();
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
  }

  const encodedSlug = encodeURIComponent(decodeRouteParam(slug));
  const search = params.toString();
  return search ? `/leagues/${encodedSlug}?${search}` : `/leagues/${encodedSlug}`;
}
