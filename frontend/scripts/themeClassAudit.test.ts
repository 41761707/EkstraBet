import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import {
  auditExitCode,
  auditSource,
  collectForbiddenFromContent,
  isAllowed,
  loadAllowlist,
} from "./themeClassAudit.mjs";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(SCRIPT_DIR, "..");
const SRC_DIR = path.join(FRONTEND_ROOT, "src");
const ALLOWLIST_PATH = path.join(SRC_DIR, "theme-class-allowlist.json");

const fixtureRoots: string[] = [];

function writeAllowlist(
  allowlistPath: string,
  entries: Array<{ path: string; pattern: string; reason: string }>,
): void {
  fs.writeFileSync(
    allowlistPath,
    JSON.stringify({ entries }),
    "utf8",
  );
}

function createAuditFixture(
  files: Record<string, string>,
  entries: Array<{ path: string; pattern: string; reason: string }> = [],
): { srcDir: string; allowlistPath: string } {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "theme-audit-"));
  fixtureRoots.push(root);
  const srcDir = path.join(root, "src");
  fs.mkdirSync(srcDir, { recursive: true });

  for (const [relative, content] of Object.entries(files)) {
    const full = path.join(srcDir, relative);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content, "utf8");
  }

  const allowlistPath = path.join(srcDir, "theme-class-allowlist.json");
  writeAllowlist(allowlistPath, entries);
  return { srcDir, allowlistPath };
}

afterEach(() => {
  while (fixtureRoots.length > 0) {
    const root = fixtureRoots.pop();
    if (root) {
      fs.rmSync(root, { recursive: true, force: true });
    }
  }
});

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

  it("flags responsive and stacked variants so md:bg-slate-* cannot slip through", () => {
    const hits = collectForbiddenFromContent(
      'className="md:bg-slate-900 sm:hover:text-white"',
      "components/Card.tsx",
    );
    expect(hits.map((hit) => hit.className)).toEqual([
      "md:bg-slate-900",
      "sm:hover:text-white",
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

  it("flags directional border, shadow, and arbitrary hex utilities", () => {
    const hits = collectForbiddenFromContent(
      'className="border-t-slate-700 border-x-slate-200 shadow-white ' +
        'bg-[#0f172a] hover:text-[#e2e8f0]/80"',
      "components/Card.tsx",
    );
    expect(hits.map((hit) => hit.className)).toEqual([
      "border-t-slate-700",
      "border-x-slate-200",
      "shadow-white",
      "bg-[#0f172a]",
      "hover:text-[#e2e8f0]/80",
    ]);
  });

  it("does not flag JS hex constants, CSS variables, or token utilities", () => {
    const hits = collectForbiddenFromContent(
      [
        'export const CHART_COLOR_NEGATIVE = "#d95757";',
        'style={{ backgroundColor: "#52b788" }}',
        "--page: #0b1120;",
        'className="bg-[var(--page)] border-t-accent border-l-4"',
      ].join("\n"),
      "lib/chartColors.ts",
    );
    expect(hits).toEqual([]);
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

describe("auditSource", () => {
  it("returns hits and exit code 1 for bg-slate-900 outside the allowlist", () => {
    const { srcDir, allowlistPath } = createAuditFixture({
      "components/Card.tsx": 'export const c = "bg-slate-900";\n',
    });

    const hits = auditSource(srcDir, allowlistPath);
    expect(hits).toEqual([
      {
        relativePath: "components/Card.tsx",
        line: 1,
        className: "bg-slate-900",
      },
    ]);
    expect(auditExitCode(hits)).toBe(1);
  });

  it("passes when the same class is on the allowlist", () => {
    const { srcDir, allowlistPath } = createAuditFixture(
      {
        "lib/chartColors.ts": 'export const track = "bg-slate-500";\n',
      },
      [
        {
          path: "lib/chartColors.ts",
          pattern: "^bg-slate-500$",
          reason: "data series color, not UI chrome",
        },
      ],
    );

    const hits = auditSource(srcDir, allowlistPath);
    expect(hits).toEqual([]);
    expect(auditExitCode(hits)).toBe(0);
  });

  it("scans css and ignores non-source files", () => {
    const { srcDir, allowlistPath } = createAuditFixture({
      "app/globals.css": ".x { @apply text-white; }\n",
      "notes.md": "bg-slate-900\n",
    });

    const hits = auditSource(srcDir, allowlistPath);
    expect(hits.map((hit) => hit.relativePath)).toEqual(["app/globals.css"]);
  });
});

describe("loadAllowlist", () => {
  it("reads path, pattern and reason from the allowlist file", () => {
    const { allowlistPath } = createAuditFixture(
      {},
      [
        {
          path: "lib/chartColors.ts",
          pattern: "^bg-slate-500$",
          reason: "data series",
        },
      ],
    );

    const allowlist = loadAllowlist(allowlistPath);
    expect(allowlist).toHaveLength(1);
    expect(allowlist[0]?.pathSuffix).toBe("lib/chartColors.ts");
    expect(allowlist[0]?.reason).toBe("data series");
    expect(allowlist[0]?.pattern.test("bg-slate-500")).toBe(true);
  });
});

describe("lint wiring", () => {
  it("exposes audit:theme and runs it from npm run lint", () => {
    const pkg = JSON.parse(
      fs.readFileSync(path.join(FRONTEND_ROOT, "package.json"), "utf8"),
    ) as { scripts: Record<string, string> };

    expect(pkg.scripts["audit:theme"]).toContain("audit-theme-classes.mjs");
    expect(pkg.scripts.lint).toContain("audit-theme-classes.mjs");
  });

  it("current frontend/src is clean against the committed allowlist", () => {
    expect(auditSource(SRC_DIR, ALLOWLIST_PATH)).toEqual([]);
  });
});
