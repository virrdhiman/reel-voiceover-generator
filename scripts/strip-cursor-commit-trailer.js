#!/usr/bin/env node
/**
 * Removes Cursor agent attribution from commit message files.
 * Used by .githooks/prepare-commit-msg (policy: no Cursor traces in git history).
 */
const fs = require('node:fs');

const file = process.argv[2];
if (!file || !fs.existsSync(file)) process.exit(0);

const strip = (line) =>
  /cursoragent@cursor\.com/i.test(line) ||
  /^Co-authored-by:\s*Cursor\b/i.test(line) ||
  /^Made-with:\s*Cursor\b/i.test(line);

const text = fs.readFileSync(file, 'utf8');
const cleaned = text
  .split(/\r?\n/)
  .filter((line) => !strip(line))
  .join('\n')
  .replace(/\n{3,}/g, '\n\n')
  .trimEnd();

if (cleaned !== text) {
  fs.writeFileSync(file, cleaned + (cleaned.endsWith('\n') ? '' : '\n'));
}
