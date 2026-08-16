import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/apiShared";
import {
  EMPTY_RATING_PROGRESS_MESSAGE,
  mapRatingProgressLoadError,
} from "@/components/leagues/ratingProgressLoadModel";

describe("mapRatingProgressLoadError", () => {
  it("treats HTTP 404 as an empty season", () => {
    expect(mapRatingProgressLoadError(new ApiError(404, "Not found"))).toEqual({
      status: "empty",
      message: EMPTY_RATING_PROGRESS_MESSAGE,
    });
  });

  it("keeps other API errors as failures", () => {
    expect(
      mapRatingProgressLoadError(new ApiError(500, "Database error")),
    ).toEqual({
      status: "error",
      message: "Database error",
    });
  });

  it("falls back when the error has no message", () => {
    expect(mapRatingProgressLoadError({})).toEqual({
      status: "error",
      message:
        "Spróbuj ponownie za chwilę. Jeśli problem się powtórzy, odśwież stronę.",
    });
  });
});
