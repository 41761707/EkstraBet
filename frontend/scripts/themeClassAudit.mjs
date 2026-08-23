import fs from "node:fs";
import path from "node:path";

export const FORBIDDEN_CLASS =
  /(?:^|[^a-zA-Z0-9-])((?:hover:|focus(?:-visible)?:|active:|disabled:|placeholder:|group-hover:|group-open:|odd:|even:)*(?:bg|text|border|ring|fill|stroke|from|to|via|divide|outline|accent|ring-offset|caret|decoration)-(?:slate|sky|white)(?:-\d{2,3})?(?:\/\d+)?)\b/g;

export const DARK_VARIANT = /\bdark:/g;

function lineNumber(content, index) {
  return content.slice(0, index).split("\n").length;
}

export function collectForbiddenFromContent(content, relativePath) {
  const hits = [];

  FORBIDDEN_CLASS.lastIndex = 0;
  let match = FORBIDDEN_CLASS.exec(content);
  while (match) {
    hits.push({
      relativePath,
      line: lineNumber(content, match.index),
      className: match[1],
    });
    match = FORBIDDEN_CLASS.exec(content);
  }

  DARK_VARIANT.lastIndex = 0;
  match = DARK_VARIANT.exec(content);
  while (match) {
    hits.push({
      relativePath,
      line: lineNumber(content, match.index),
      className: "dark:",
    });
    match = DARK_VARIANT.exec(content);
  }

  return hits;
}

export function loadAllowlist(allowlistPath) {
  const raw = JSON.parse(fs.readFileSync(allowlistPath, "utf8"));
  return (raw.entries ?? []).map((entry) => ({
    pathSuffix: String(entry.path).replaceAll("\\", "/"),
    pattern: new RegExp(entry.pattern),
    reason: entry.reason,
  }));
}

export function isAllowed(relativePath, className, allowlist) {
  const normalized = relativePath.replaceAll("\\", "/");
  return allowlist.some(
    (entry) =>
      normalized.endsWith(entry.pathSuffix) && entry.pattern.test(className),
  );
}

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
      continue;
    }
    if (/\.(ts|tsx|css)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

export function auditSource(srcDir, allowlistPath) {
  const allowlist = loadAllowlist(allowlistPath);
  const hits = [];

  for (const file of walk(srcDir)) {
    const relativePath = path.relative(srcDir, file).replaceAll("\\", "/");
    const content = fs.readFileSync(file, "utf8");
    for (const hit of collectForbiddenFromContent(content, relativePath)) {
      if (!isAllowed(relativePath, hit.className, allowlist)) {
        hits.push(hit);
      }
    }
  }

  return hits;
}
