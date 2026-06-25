#!/usr/bin/env node
/** stdin filter for git filter-branch --msg-filter */
const strip = (line) =>
  /cursoragent@cursor\.com/i.test(line) ||
  /^Co-authored-by:\s*Cursor\b/i.test(line) ||
  /^Made-with:\s*Cursor\b/i.test(line);

let data = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { data += chunk; });
process.stdin.on('end', () => {
  const cleaned = data
    .split(/\r?\n/)
    .filter((line) => !strip(line))
    .map((line) => line.replace(/cursor\/harden-server-error-handling/g, 'feature branch'))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trimEnd();
  process.stdout.write(cleaned + (cleaned ? '\n' : ''));
});
