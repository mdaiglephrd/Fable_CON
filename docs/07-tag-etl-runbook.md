# 07 — Tag ETL runbook (Phase 1)

How the bulk SSD document corpus gets OCR'd and loaded, how to operate and
monitor the pipeline, and what to do when something sticks. Verified against
`ingest/tag_enumerate.py`, `ingest/tag_ocr.py`, `ingest/tag_crosswalk.py`,
`ingest/tag_process.py`, `ingest/tag_load.py`, `ingest/tag_orchestrate.py`,
and `schema/migrations/0010_axis_vocab.sql`–`0012_tag_source_file.sql`.

This is **Phase 1 only**: it loads untagged document records (OCR text +
file-level metadata) into the existing `con.matter`/`con.document`/
`con.document_text` tables, and stands up the Axis 1–4 schema those tags will
eventually live in. It does **not** apply Axis 1–4 tags — that is Phase 2, a
human process through Harvey, documented in
[08-harvey-tagging-guide.md](08-harvey-tagging-guide.md).

## 0. What this pipeline actually targets

The ~150,000-document SSD corpus is **the same Laserfiche `HealthPlanning`
repository** `con.document`/`con.matter` already model (confirmed via the
operator-supplied document index: Entry IDs 1,043–1,064,573 sit inside the
"~1M+ row" full-repository figure in `LESSONS.md`, and the folder convention
matches this repo's own tag-export fixtures). This pipeline therefore writes
into the **existing** tables via the **existing** loaders
(`ingest/load_tags.py`, `ingest/load_document_text.py`) — it does not stand up
a parallel schema or database. Only the Axis 1–4 tag structures
(`con.vocab_axis1_proceeding_type`, `con.vocab_axis2_authority_type`,
`con.axis3_substantive_issue`, `con.axis4_procedural_issue`,
`con.document_axis1`–`con.document_axis4`) are genuinely new.

## 1. Inputs

| Input | What it is | Required for |
|---|---|---|
| SSD root directory | The real, on-disk file tree of CON/DET/LNR documents | `ingest.tag_orchestrate`'s positional `root` argument |
| Document index (`.xlsx`) | Operator-supplied `Path, Name, Type, Entry ID, Page Count` export of the Laserfiche repository | `--index-xlsx`; the crosswalk that resolves a real file back to its Laserfiche Entry ID |

**The index's `Path` column does not exactly match the real on-disk
layout** (confirmed with the operator: real folders mirror the index's
hierarchy loosely — renamed/flattened segments, drift). `ingest/tag_crosswalk.py`
therefore does a **fuzzy** match (docket-scoped, name-similarity-scored, with
a page-count cross-check once OCR has run) rather than an exact path join.
Since `con.document.entry_id` is a `NOT NULL` primary key, a file that cannot
be resolved with reasonable confidence is **never** inserted with an invented
id — it is recorded `Unresolved` in the ledger and written to `--rejects` for
manual reconciliation, exactly like the unknown-docket / unknown-entry_id
reject paths `ingest/load_tags.py` and `ingest/load_document_text.py` already
implement.

## 2. Running the migration

```bash
python -m schema.migrate
```

Applies `0010_axis_vocab.sql`, `0011_axis_tag_tables.sql`,
`0012_tag_source_file.sql` (and anything else pending) onto the existing `con`
schema/database — no new database, no new connection variables. Re-running is
a no-op once applied (`con.schema_migrations` tracks it, same as every other
migration in this repo).

## 3. Running the pipeline

```bash
# Dry run (default): enumerates the corpus and hashes every file (a real
# read of each file, so this also surfaces unreadable files), but runs no
# OCR and touches no database.
python -m ingest.tag_orchestrate /path/to/ssd --index-xlsx index_documents_only_2.xlsx

# Real run: OCR + load, committing every 500 documents, with a rejects report.
python -m ingest.tag_orchestrate /path/to/ssd --index-xlsx index_documents_only_2.xlsx \
    --apply --batch-size 500 --rejects rejects.csv
```

Full signature:
`python -m ingest.tag_orchestrate root --index-xlsx PATH [--apply] [--batch-size 500] [--rejects out.csv]`

Prints: files seen / skipped (already done) / loaded / unresolved (crosswalk)
/ failed (OCR or DB) / commits.

**Keep the index `.xlsx` outside the SSD root.** `enumerate_candidate_files`
walks `root` recursively and treats every regular file it finds as a
candidate document — including the index file itself, if it's been dropped
inside the tree being scanned. It will still fail gracefully (not a
document, so OCR/crosswalk resolution fails and it lands in the `Failed`
bucket rather than corrupting anything), but it wastes a pass and clutters
the rejects report for no reason. Point `--index-xlsx` at a path outside
`root`.

**Batching**: files are processed in `enumerate_candidate_files`'s natural
directory-tree order (`os.walk` descends one subtree at a time), which
already clusters files by their real folder — and therefore by document
category — without buffering the whole corpus in memory before starting
work. A commit happens every `--batch-size` documents; a crash mid-run only
ever loses the currently-uncommitted batch.

**Resumability**: `con.tag_source_file` (migration `0012`) is the idempotency
ledger, keyed by `(path_hash, file_hash)` — the sha256 of the real file path
string, plus the sha256 of the file's bytes (`common/file_identity.py`). Only
a `Succeeded` row skips reprocessing (mirroring `con.processed_blob`'s
"only succeeded blocks reprocessing" rule already used by the Functions app);
`Failed`/`Unresolved` stay retryable, so fixing the underlying cause (or
improving the crosswalk match) and rerunning heals them without a manual
ledger edit. Re-running the whole command after any crash is always safe.

**OCR engine**: `openocr-python`, run in-process (`ingest/tag_ocr.py`
`OpenOcrEngine`) — no cloud OCR key/endpoint, unlike the existing Document
Intelligence path. `NativeTextEngine` (pdfplumber) is tried first for every
PDF; a PDF whose own text layer already looks real skips OpenOCR entirely — a
real cost/time win over 150,000 documents.

## 4. What gets written

For each **resolved** file (crosswalk found a confident Entry ID match):

- `con.matter` — a **stub** row if the docket doesn't exist yet
  (`completeness_flags = ["stub_from_tag_etl"]`, applicant parsed from the
  matched index row's own folder name), via `ingest.load_tags`'s exact
  `MATTER_MERGE_SQL`/shaping conventions. Existing matter data is never
  blanked (`COALESCE(source, target)`, same as every other loader here).
- `con.document` — `entry_id`, `docket_id`, `file_name`, `doc_type`/`phase`
  (inferred from the matched index row's folder position — see
  `ingest/tag_crosswalk.py`'s `infer_doc_type_phase`), `page_count`,
  `source_path` (the real on-disk path), `ocr_status`, `ocr_confidence`,
  `text_source`. `validation_status` defaults to `Unvalidated`, same as every
  other intake path.
- `con.document_text` — `full_text`, `char_count`, `text_source`
  (`ocr`/`native`), `di_model` (`openocr-python==<version>` or
  `pdfplumber-native`), `di_confidence`.
- `con.tag_source_file` — the ledger row (`Succeeded`).

For an **unresolved** file: only `con.tag_source_file` (`Unresolved`) is
written, plus a line in `--rejects` (`file_path,docket_id,detail_or_confidence`).

Nothing writes to `con.document_axis1`–`con.document_axis4` — those stay
empty until Phase 2.

## 5. A pitfall to know about before reading the rejects report

**A `1 Master File` folder name is not the same thing as the Axis 2
`Masterfile` authority-type value.** `1 Master File` is Laserfiche's own
per-docket case-file *container* folder (~36% of the real corpus lives under
one) — it has nothing to do with whether a specific document is a large
consolidated-pleadings "Masterfile" for Axis 2 tagging purposes. This
pipeline never infers Axis 2 from folder names at all (Phase 1 doesn't touch
Axis tags), but a human skimming `source_path` values during Phase 2 review
should not conflate the two. See
[08-harvey-tagging-guide.md](08-harvey-tagging-guide.md).

## 6. Monitoring

**Ledger status (SQL — the first place to look):**

```sql
SELECT status, COUNT(*) FROM con.tag_source_file GROUP BY status;

SELECT TOP 50 file_path, detail, processed_at
FROM con.tag_source_file
WHERE status IN ('Failed', 'Unresolved')
ORDER BY processed_at DESC;
```

**Crosswalk match quality**: keep every `--rejects` CSV. A high unresolved
rate against one particular docket subtree usually means the real on-disk
folder for that docket has drifted further from the index than
`ingest/tag_crosswalk.py`'s `MATCH_THRESHOLD`/`AMBIGUITY_MARGIN` tolerate —
both are module-level constants, tunable without touching the matching logic
itself (same "table edit, not a rewrite" philosophy `weekly_report_parser.py`
already uses for its section-header regexes).

**Coverage check:**

```sql
SELECT COUNT(*) FROM con.document WHERE entry_id IN (SELECT entry_id FROM con.tag_source_file);
SELECT COUNT(*) FROM con.document_text;
```

## 7. Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| Most files come back `Unresolved` | The real on-disk folder tree doesn't contain a recognizable docket id (`common/docket.py`'s `extract_dockets`), or the SSD subtree isn't in the index at all | Check a sample path by hand; if a docket id is present but oddly formatted, extend `common/docket.py`'s patterns (as done for `LNR-ASC`/`LNR-EQT` — see `LESSONS.md`); if genuinely outside the index, that subtree needs its own index export. |
| Many `Unresolved` results within one docket that clearly *is* in the index | Ambiguous near-tie between two candidates (e.g. "Appendix A" vs "Appendix B" with similar OCR'd names) | Lower `AMBIGUITY_MARGIN` or raise `_PAGE_COUNT_BONUS` in `ingest/tag_crosswalk.py` only after confirming with a few real examples that the page-count cross-check reliably disambiguates them; re-run (unresolved files stay retryable). |
| `entry_id not in con.document` errors from `load_document_text`-shaped writes | Should not happen through this pipeline (the document row is always written in the same `load_one_record` call before its text) — if seen, it means `ingest.tag_load.load_one_record` was called directly on a doc without going through `ingest.tag_process.process_one_file` first | File a repo issue; don't hand-construct `ProcessedDocument` outside the normal pipeline. |
| OCR is very slow / GPU not used | `openocr-python`'s ONNX/Torch backend selection is an installation-time choice, not a runtime flag here | Confirm which backend was installed (`pip show openocr-python`) and reinstall with the intended backend per the package's own docs. |
| A file's OCR text looks wrong/garbled but `ocr_status = 'Succeeded'` | OCR "succeeding" only means the engine ran without raising — it says nothing about accuracy | Use `validation_status` (already `Unvalidated` by default) and the existing research-console validation workflow to flag/correct it, same as any other intake path. |
| Rerunning after a crash seems to redo work that already finished | Confirm the batch that was in flight when the crash happened was never committed (`con.tag_source_file` won't show `Succeeded` for it) — this is expected, not a bug | Nothing to fix; that batch's files get reprocessed and converge via MERGE + the ledger. Only genuinely `Succeeded` files are skipped. |
| `ModuleNotFoundError: openocr` / `openpyxl` | Dependencies not installed in this environment | `pip install -r requirements.txt` (or `requirements-dev.txt` for local dev). |

## 8. Conversion to a timer-triggered Azure Function (future work, not implemented here)

`ingest/tag_enumerate.py`, `ingest/tag_process.py`, and `ingest/tag_load.py`
are already pure/DB-agnostic-where-appropriate and OCR-injected exactly the
way `functions/processing.py`'s snapshot/report handlers are today. The later
lift-and-shift: a timer trigger (mirroring `functions/function_app.py`'s
`daily_sweep`) calls `tag_enumerate` against whatever network-accessible path
replaces the local SSD (e.g. an Azure Files share), resolves each file's
Entry ID via the same crosswalk, and skips anything already `Succeeded` in
`con.tag_source_file` before calling `tag_process` + `tag_load` per file
exactly as `ingest/tag_orchestrate.py`'s CLI loop does today. No rewrite:
that loop body becomes the Function's timer handler body verbatim.
