#!/usr/bin/env node
/*
 * One-shot generator: evaluates tests/fixtures/handoff/con-corpus.js (a plain
 * browser IIFE that assigns window.CON_CORPUS) and writes the resulting data
 * as web/src/lib/corpus.json for the fixture-mode API client.
 *
 * Run from web/:  npm run generate:corpus
 * The output is committed; re-run only when the handoff corpus changes.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const srcPath = fileURLToPath(
  new URL('../../tests/fixtures/handoff/con-corpus.js', import.meta.url),
);
const outPath = fileURLToPath(new URL('../src/lib/corpus.json', import.meta.url));

const source = readFileSync(srcPath, 'utf8');
const windowShim = {};
new Function('window', source)(windowShim);

if (!windowShim.CON_CORPUS || !windowShim.CON_CORPUS.cases) {
  throw new Error('con-corpus.js did not populate window.CON_CORPUS.cases');
}

writeFileSync(outPath, JSON.stringify(windowShim.CON_CORPUS, null, 2) + '\n');
const ids = Object.keys(windowShim.CON_CORPUS.cases);
console.log(`Wrote ${outPath} with ${ids.length} cases: ${ids.join(', ')}`);
