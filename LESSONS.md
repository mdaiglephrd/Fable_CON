# LESSONS

One lesson per entry: a one-line summary, then why it mattered. Update entries
in place rather than adding duplicates.

- **The research console is the primary UI; Power Apps is retired, not deleted.**
  The design handoff superseded the Power Apps browse/validation screens — keeping the
  console primary avoids the Power Apps premium-connector license entirely, and the old
  artifacts stay in `m365/powerapp/` as marked reference so the decision is auditable.

- **Ported engines are held to golden parity, not re-implementation judgment.**
  `common/proceeding.py` and `web/src/lib/docketEngine.ts` must deep-equal fixtures
  generated from the real `docket-engine.js` (including its seeded pseudo-random
  precedent hash and en-US date strings). Byte-equal goldens caught drift that
  "looks right" review never would.

- **Free-tier levers are parameters, not forks.**
  SQL free offer, Doc Intelligence F0/S0, App Service F1/B1, deploySearch/deployOpenAI
  are all Bicep params with free defaults — one template serves the $0 pilot and the
  paid steady state, and docs/06 documents the outgrow ladder instead of a second stack.

- **Analytical legal fields are editorial data, not extraction targets.**
  Headnotes, treatment flags, topic keys, and synopses ride the existing
  validation_status workflow (entered in the console, flagged until Validated);
  docs/05 encodes the T/X/E/D split so ingestion never pretends a machine decided
  what only an editor can.

- **GA-####### is treated as a legacy variant of CON-####### — an assumption, not a fact.**
  The spec says legacy `GA-#######` ids are "embedded in names" and the digit count
  matches CON numbering, so `common/docket.py` canonicalizes GA→CON (constant
  `GA_MAPS_TO_CON`). If real data shows GA numbers are a separate space, flip the
  constant and re-run the tag load; matters keyed wrongly would need re-keying.

- **All cross-module names live in DESIGN.md; modules were built against it, not each other.**
  Parallel construction of schema/ingest/api/functions only stayed consistent because
  table names, env var names, and function signatures were fixed in one file first.

- **Snapshot diffs hold only the OLD snapshot in memory and stream the NEW one.**
  The full repository index is ~1M+ rows; two full dicts would approach the memory
  ceiling of a consumption-plan Azure Function. One dict + streaming halves it.

- **Failed ingestion blobs stay retryable: only `status='succeeded'` in con.processed_blob short-circuits.**
  If a failure row also blocked reprocessing, the Functions host's blob-retry and the daily
  sweep would both become no-ops after one bad run; a failed blob must be re-attemptable
  after the underlying cause (bad file, transient outage) is fixed.

- **Import Azure/pyodbc/pdfplumber lazily inside the functions that need them.**
  Test and import cleanliness depend on it: this build environment has no libodbc,
  and the API/functions modules must import with an empty environment. Config reads
  are lazy for the same reason — fail at call time with the missing variable named,
  never at import time.

- **Separator-less DET/LNR ids canonicalize as one digit group — revisit with real samples.**
  `DET2020014` becomes `DET-2020014` while `DET-2020-014` becomes `DET-2020-014`, so the
  same docket printed both ways would key two matters. No grouping rule can be inferred
  without real data; when samples arrive, if DET/LNR numbers have a fixed year+sequence
  shape, add a regrouping rule in `common/docket.py` and re-key.

- **The weekly-report parser is built against a synthetic fixture until the real PDF arrives.**
  Layout assumptions (section headers, label names) are isolated in regex tables at the
  top of `ingest/weekly_report_parser.py` so re-tuning against the real DCH report is a
  table edit, not a rewrite. Same for the tag export: column names are assumed to match
  DESIGN.md field names until a real export is provided.
