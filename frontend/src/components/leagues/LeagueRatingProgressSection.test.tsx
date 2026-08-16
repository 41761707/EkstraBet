import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  RatingProgressIdlePanel,
  RatingProgressLoadBody,
} from "@/components/leagues/LeagueRatingProgressSection";
import {
  COMPUTE_RATING_PROGRESS_HINT,
  COMPUTE_RATING_PROGRESS_LABEL,
  EMPTY_RATING_PROGRESS_TITLE,
  ERROR_RATING_PROGRESS_TITLE,
  LOADING_RATING_PROGRESS_LABEL,
} from "@/components/leagues/ratingProgressLoadModel";

describe("RatingProgressLoadBody", () => {
  it("shows the compute button only in the idle state", () => {
    const markup = renderToStaticMarkup(
      createElement(RatingProgressIdlePanel, { onCompute: () => undefined }),
    );
    expect(markup).toContain(COMPUTE_RATING_PROGRESS_LABEL);
    expect(markup).toContain(COMPUTE_RATING_PROGRESS_HINT);
    expect(markup).not.toContain("Sezon");
  });

  it("does not fetch markup while idle inside the expander body", () => {
    const markup = renderToStaticMarkup(
      createElement(RatingProgressLoadBody, {
        status: "idle",
        data: null,
        error: null,
        onCompute: () => undefined,
      }),
    );
    expect(markup).toContain(COMPUTE_RATING_PROGRESS_LABEL);
    expect(markup).not.toContain(LOADING_RATING_PROGRESS_LABEL);
  });

  it("shows a spinner while computing", () => {
    const markup = renderToStaticMarkup(
      createElement(RatingProgressLoadBody, {
        status: "loading",
        data: null,
        error: null,
        onCompute: () => undefined,
      }),
    );
    expect(markup).toContain(LOADING_RATING_PROGRESS_LABEL);
    expect(markup).not.toContain(COMPUTE_RATING_PROGRESS_LABEL);
  });

  it("shows an empty state after a missing-progress response", () => {
    const markup = renderToStaticMarkup(
      createElement(RatingProgressLoadBody, {
        status: "empty",
        data: null,
        error: null,
        onCompute: () => undefined,
      }),
    );
    expect(markup).toContain(EMPTY_RATING_PROGRESS_TITLE);
  });

  it("keeps a retry button after a compute failure", () => {
    const markup = renderToStaticMarkup(
      createElement(RatingProgressLoadBody, {
        status: "error",
        data: null,
        error: "Database error",
        onCompute: () => undefined,
      }),
    );
    expect(markup).toContain(ERROR_RATING_PROGRESS_TITLE);
    expect(markup).toContain("Database error");
    expect(markup).toContain(COMPUTE_RATING_PROGRESS_LABEL);
  });
});
