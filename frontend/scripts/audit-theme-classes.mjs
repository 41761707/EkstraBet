import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditExitCode, auditSource } from "./themeClassAudit.mjs";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SRC_DIR = path.resolve(SCRIPT_DIR, "../src");
const ALLOWLIST_PATH = path.resolve(SRC_DIR, "theme-class-allowlist.json");

const hits = auditSource(SRC_DIR, ALLOWLIST_PATH);

if (hits.length > 0) {
  console.error("Audyt motywu: klasy dark-only poza allowlistą:\n");
  for (const hit of hits) {
    console.error(`  ${hit.relativePath}:${hit.line}  ${hit.className}`);
  }
  process.exit(auditExitCode(hits));
}

console.log("Audyt motywu: brak klas dark-only poza allowlistą.");
process.exit(auditExitCode(hits));
