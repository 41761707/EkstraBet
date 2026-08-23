import { describe, expect, it } from "vitest";

import {
  collectForbiddenFromContent,
  isAllowed,
} from "./themeClassAudit.mjs";

describe("collectForbiddenFromContent", () => {
  it("flags dark-only Tailwind chrome classes", () => {
    const hits = collectForbiddenFromContent(
      'className="bg-slate-900 text-white hover:bg-sky-700"',
      "components/Card.tsx",
    );
    expect(hits.map((hit) => hit.className)).toEqual([
      "bg-slate-900",
      "text-white",
      "hover:bg-sky-700",
    ]);
  });

  it("does not flag semantic theme tokens or layout utilities", () => {
    const hits = collectForbiddenFromContent(
      'className="bg-surface text-muted border-border right-2"',
      "components/Field.tsx",
    );
    expect(hits).toEqual([]);
  });

  it("flags dark: variants so new UI cannot split palettes", () => {
    const hits = collectForbiddenFromContent(
      'className="bg-surface dark:bg-page"',
      "components/Card.tsx",
    );
    expect(hits.map((hit) => hit.className)).toEqual(["dark:"]);
  });
});

describe("isAllowed", () => {
  const allowlist = [
    {
      pathSuffix: "lib/chartColors.ts",
      pattern: /^bg-slate-500$/,
      reason: "data series",
    },
  ];

  it("rejects a dark-only class outside the allowlist", () => {
    expect(isAllowed("components/Card.tsx", "bg-slate-900", allowlist)).toBe(
      false,
    );
  });

  it("accepts an allowlisted data-color class", () => {
    expect(isAllowed("lib/chartColors.ts", "bg-slate-500", allowlist)).toBe(
      true,
    );
  });
});
