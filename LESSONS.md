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

- **A real data sample overturned a "separate corpus" assumption before any tag-ETL code was
  written.** The ~150K-document SSD corpus was initially assumed to be a candidate for a brand-new,
  independent schema/database — the task brief itself said "a new Azure SQL Database," and this
  repo's own docs/fixtures had no "150,000" figure anywhere to confirm otherwise. The operator then
  supplied the actual Laserfiche document index (`Path, Name, Type, Entry ID, Page Count`), whose
  Entry ID range (1,043–1,064,573) and folder convention matched this repo's existing fixtures
  exactly — proving it's the *same* population `con.document`/`con.matter` already model. The tag
  ETL (docs/07) writes into the existing tables because of that evidence, not despite the brief's
  wording. Lesson: when a bulk-data task's corpus identity is ambiguous, get a real sample before
  committing to new infrastructure — a spreadsheet answered in minutes what discovery alone could not.

- **`common/docket.py`'s `_LNR_RE` didn't recognize the `ASC`/`EQT` subtype `_DET_RE` already did** —
  `LNR-ASC2005006`/`LNR-EQT2005004` (pre-2019 Letters of Non-Reviewability, ~4.3% of the real SSD
  corpus) extracted as nothing at all. `common/docket_family.py` had silently worked around this with
  its own raw-string prefix check, with a comment documenting the gap as if it were permanent. Fixed
  by mirroring `_DET_RE`'s subtype-capturing group onto `_LNR_RE`; no existing test depended on the
  gap, and `docket_family.py` needed no logic change, only its now-stale comment corrected. Lesson:
  a real data sample can surface a bug in code you didn't intend to touch — fix it at the source
  rather than adding a second workaround next to the first one.

- **A Laserfiche folder literally named "1 Master File" is not the same thing as the Axis 2
  "Masterfile" tag value.** ~36% of the real SSD corpus lives under that folder, which is Laserfiche's
  own per-docket case-file *container* — most documents under it are ordinary Applications,
  Appendices, Decisions, etc. The Axis 2 "Masterfile" value means something narrower and different: a
  single large document that itself consolidates most/all pleadings up to a case phase. Phase 1 never
  infers Axis 2 from folder names (it doesn't touch Axis tags at all), but docs/08 calls the
  distinction out explicitly for Harvey reviewers, since the folder-name coincidence is exactly the
  kind of thing that silently causes systematic mis-tagging if no one names it.
