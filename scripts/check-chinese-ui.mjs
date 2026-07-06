#!/usr/bin/env node
/**
 * check-chinese-ui.mjs - mojibake detection quality gate for Bolt desktop.
 *
 * Scans Chinese UI text files for garbled/mojibake characters that indicate
 * encoding corruption. The checked codepoints are:
 * U+9352, U+93C3, U+7481, U+922B, U+5BF0, U+6FEE, U+93B5, U+7039, U+FFFD.
 *
 * Also checks that tool protocol uses file.read / file.patch, not bare "file",
 * and old_string / new_string, not old_text / new_text.
 */

import { readFileSync, readdirSync } from 'fs';
import { join, relative } from 'path';

const MOJIBAKE_CHARS = new Set([
  '\u9352',
  '\u93C3',
  '\u7481',
  '\u922B',
  '\u5BF0',
  '\u6FEE',
  '\u93B5',
  '\u7039',
  '\uFFFD',
]);
const BARE_FILE_TOOL_RE = /tool:\s*['"]file['"]/;
const OLD_TEXT_RE = /old_text/;
const NEW_TEXT_RE = /new_text/;

const scanFiles = [
  'apps/desktop/src/App.tsx',
  'apps/desktop/src/App.test.tsx',
  'apps/desktop/src/uiWorkflowDogfood.test.tsx',
  'apps/desktop/src/dogfoodSmoke.test.ts',
  'apps/desktop/src/workflowClient.ts',
];

const scanDirs = [
  'docs/exec-plans/active',
  'docs/decisions',
];

function listMdFiles(dir) {
  try {
    return readdirSync(dir).filter((file) => file.endsWith('.md')).map((file) => join(dir, file));
  } catch {
    return [];
  }
}

const allFiles = [...scanFiles, ...scanDirs.flatMap(listMdFiles)];
let errors = 0;

for (const filePath of allFiles) {
  let content;
  try {
    content = readFileSync(filePath, 'utf-8');
  } catch {
    continue;
  }
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = [...line].find((char) => MOJIBAKE_CHARS.has(char));
    if (match) {
      console.error(`[ERROR] ${relative('', filePath)}:${i + 1}: mojibake "${match}" -> ${line.trim()}`);
      errors++;
    }
  }

  if (filePath.includes('apps/desktop/src/')) {
    if (BARE_FILE_TOOL_RE.test(content)) {
      console.error(`[ERROR] ${relative('', filePath)}: uses tool: "file" instead of "file.read" / "file.patch"`);
      errors++;
    }
    if (OLD_TEXT_RE.test(content)) {
      console.error(`[ERROR] ${relative('', filePath)}: uses old_text instead of old_string`);
      errors++;
    }
    if (NEW_TEXT_RE.test(content)) {
      console.error(`[ERROR] ${relative('', filePath)}: uses new_text instead of new_string`);
      errors++;
    }
  }
}

if (errors > 0) {
  console.error(`\n[ERROR] ${errors} mojibake/protocol errors found. Fix before commit.`);
  process.exit(1);
}

console.log('[OK] No mojibake or tool protocol violations detected.');
process.exit(0);
