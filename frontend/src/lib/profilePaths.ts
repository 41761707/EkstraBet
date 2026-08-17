import { decodeRouteParam } from "@/lib/leaguePaths";

/** Canonical private profile URL for a username. */
export function profilePath(username: string): string {
  return `/profile/${encodeURIComponent(username)}`;
}

/** Decode a dynamic `[username]` segment that may still be percent-encoded. */
export function decodeProfileUsername(value: string): string {
  return decodeRouteParam(value);
}

/** True when the route segment belongs to the signed-in user. */
export function isOwnProfile(
  routeUsername: string,
  currentUsername: string,
): boolean {
  return decodeProfileUsername(routeUsername) === currentUsername;
}
