/*
 * Parity test: the TypeScript docket engine must reproduce, byte for byte,
 * the output of the reference JS engine (tests/fixtures/handoff/docket-engine.js)
 * captured in tests/fixtures/handoff/golden_proceeding.json for all 10 records.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { build, type DocketRecord, type Proceeding } from './docketEngine';

interface GoldenEntry {
  rec: DocketRecord;
  proceeding: Proceeding;
}

const goldenPath = fileURLToPath(
  new URL('../../../tests/fixtures/handoff/golden_proceeding.json', import.meta.url),
);
const golden: Record<string, GoldenEntry> = JSON.parse(readFileSync(goldenPath, 'utf8'));
const entries = Object.entries(golden);

describe('docketEngine parity with golden_proceeding.json', () => {
  it('covers all 10 golden records', () => {
    expect(entries).toHaveLength(10);
  });

  it.each(entries)('%s: build(rec) deep-equals the golden proceeding', (_name, entry) => {
    const actual = build(entry.rec);
    // JSON round-trip drops nothing here (the engine emits only JSON-safe
    // values); it normalizes any `undefined`-valued keys so a stray extra key
    // would fail the comparison rather than being ignored by toEqual.
    expect(JSON.parse(JSON.stringify(actual))).toEqual(entry.proceeding);
  });
});
