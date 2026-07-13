# 08 — Harvey tagging guide (Phase 2)

A step-by-step guide for a **human operator** using Harvey Vaults and Harvey
Review Tables to read each document Phase 1 loaded
([07-tag-etl-runbook.md](07-tag-etl-runbook.md)) and assign its Georgia CON
Tagging Taxonomy (Axis 1–4) values. This is a documentation deliverable, not
a pipeline — nothing here runs automatically. The only code involved is the
final load step, which reuses `ingest/load_axis_tags.py` (already part of
Phase 1's codebase).

Prerequisites: `python -m schema.migrate` has been run (so
`con.vocab_axis1_proceeding_type`, `con.vocab_axis2_authority_type`,
`con.axis3_substantive_issue`, `con.axis4_procedural_issue`,
`con.document_axis1`–`con.document_axis4` exist), and `ingest.tag_orchestrate`
has loaded the documents you're about to tag (their text lives in
`con.document_text.full_text`).

## 0. Axis 1–4 reference

The taxonomy is authoritative in `GeorgiaCONTaggingTaxonomy_2.docx` and
transcribed verbatim into `common/axis_taxonomy.py` — that module (not this
document) is the source of truth Harvey's configuration should be checked
against, so the two can never silently drift apart. Structure:

| Axis | Cardinality | What it captures |
|---|---|---|
| **Axis 1** — Proceeding Type | Exactly one | `CON` (incl. LOIs), `DET`, `DET-ASC` (incl. LNR-ASC pre-2019), `DET-EQT` (incl. LNR-EQT pre-2019), `Other` (rare escape hatch) |
| **Axis 2** — Authority Type | Exactly one | Statute, Rule, DCH Desk Decision, CON Appeals Panel Decision, OSAH ALJ Decision, DCH Commissioner Final Order, Superior Court Opinion, GA Court of Appeals Opinion, GA Supreme Court Opinion, Application (non-authority), Additional Information (non-authority), **Masterfile** |
| **Axis 3** — Substantive Issue | Zero or more | The 100–900 key-number series (`con.axis3_substantive_issue`; 125 rows incl. section headers) |
| **Axis 4** — Procedural Issue | Zero or more | The P100–P900 series (`con.axis4_procedural_issue`; 59 rows incl. section headers) |

To pull a current, live copy of the full Axis 3/4 code lists (for building
Harvey's dropdown/checklist options):

```sql
SELECT code, parent_code, label, citation, sort_order FROM con.axis3_substantive_issue ORDER BY sort_order;
SELECT code, parent_code, label, citation, sort_order FROM con.axis4_procedural_issue ORDER BY sort_order;
```

or, from Python:

```python
from common.axis_taxonomy import AXIS3_SUBSTANTIVE_ISSUE, AXIS4_PROCEDURAL_ISSUE
```

**The Masterfile rule, stated plainly**: a document tagged `Masterfile` on
Axis 2 must carry **no** Axis 3 or Axis 4 tags. This is enforced twice —
`ingest/load_axis_tags.py` rejects a row that violates it before writing
anything, and `schema/migrations/0011_axis_tag_tables.sql`'s triggers
(`trg_axis2_masterfile_guard`, `trg_axis3_masterfile_guard`,
`trg_axis4_masterfile_guard`) reject the write at the database level even if
something bypasses the loader. You do not need to trust yourself (or Harvey)
to remember this — the system will refuse the invalid combination either way.

**A pitfall that will otherwise cost you real re-work**: about 36% of the
real document corpus lives under a Laserfiche folder literally named
`1 Master File`. **That folder name is not the same thing as the Axis 2
`Masterfile` value.** `1 Master File` is Laserfiche's own per-docket
case-file *container* (as opposed to, say, a docket's correspondence or
appeal subfolder) — most documents under it are ordinary Applications,
Appendices, Decisions, etc., each getting its own ordinary Axis 2 value.
Reserve the Axis 2 `Masterfile` value for what it actually means: **a single
large document that itself consolidates most or all pleadings up to some
case phase.** If you're unsure whether a specific document qualifies, it
almost certainly doesn't — tag it by what it actually is (Application,
Order, Correspondence, etc.) instead.

## 1. Structuring Harvey Vaults — one per document type

Phase 1 already populated `con.document.doc_type` and `con.document.phase`
wherever the crosswalk could infer them from the real folder position (see
[07-tag-etl-runbook.md §4](07-tag-etl-runbook.md)). Use the **actual observed
distribution**, not a guessed list, to decide how many vaults to create:

```sql
SELECT doc_type, phase, COUNT(*) AS n
FROM con.document
GROUP BY doc_type, phase
ORDER BY n DESC;
```

For each `(doc_type, phase)` combination (or each `doc_type` alone, if your
Harvey seat's vault count is limited — coarser grouping is fine, since Axis
1–4 tagging doesn't depend on how the vaults are split, only on getting the
right document in front of a reviewer), create one Harvey Vault and load it
with:

- the document's `con.document_text.full_text` (the OCR'd/native text Phase 1
  extracted — this is what the reviewer and Harvey actually read), and
- enough identifying metadata to route a tag back to the right row:
  `entry_id` (**required** — this is the join key `ingest/load_axis_tags.py`
  writes on), `docket_id`, `file_name`, `source_path`.

A starter export query per vault:

```sql
SELECT d.entry_id, d.docket_id, d.file_name, d.source_path, dt.full_text
FROM con.document d
JOIN con.document_text dt ON dt.entry_id = d.entry_id
WHERE d.doc_type = 'Application/Request' AND d.phase = 'Initial Application'
  AND NOT EXISTS (SELECT 1 FROM con.document_axis1 a1 WHERE a1.entry_id = d.entry_id);
```

(The `NOT EXISTS` clause keeps a vault focused on **not-yet-tagged**
documents — drop it if you want to re-review already-tagged ones.)

Rows with `doc_type IS NULL` or `phase IS NULL` (the crosswalk couldn't infer
either from the folder position) are real documents that still need tagging
— route them into a catch-all vault rather than skipping them; do not treat
a missing `doc_type` as evidence the document doesn't matter.

## 2. Configuring the Harvey Review Table

Set up Review Table columns mapping 1:1 onto the axes:

| Review Table column | Type | Source of allowed values | Notes |
|---|---|---|---|
| `axis1` | Single-select | `con.vocab_axis1_proceeding_type.code` | Required for every document eventually, but may be left blank on a given pass (incremental tagging is supported — see §4). |
| `axis2` | Single-select (incl. `Masterfile`) | `con.vocab_axis2_authority_type.code` | Selecting `Masterfile` should clear `axis3`/`axis4` in the same Review Table row before export — see the pitfall above and §4. |
| `axis3` | Multi-select / tag list | `con.axis3_substantive_issue.code` (label = `label`, grouped by `parent_code`) | Zero or more. Disable/hide when `axis2 = Masterfile`. |
| `axis4` | Multi-select / tag list | `con.axis4_procedural_issue.code` (label = `label`, grouped by `parent_code`) | Zero or more. Disable/hide when `axis2 = Masterfile`. |

If your Harvey configuration supports conditional field logic, wire the
Masterfile constraint into the UI itself (grey out / clear Axis 3–4 the
moment Axis 2 is set to `Masterfile`) so a reviewer never has to remember the
rule by hand — but even if the UI can't enforce it, the loader and the
database triggers still will; a violating row simply gets rejected rather
than silently corrupting data.

## 3. The review workflow

For each document in a vault:

1. Read the extracted text (and, if Harvey's viewer supports it, the
   original scanned/native document via `source_path`).
2. Assign **Axis 1** (exactly one) — which proceeding track this document
   belongs to.
3. Assign **Axis 2** (exactly one) — what kind of authority this document
   *is*. This is about the document's own nature (an application? a court
   opinion? a large consolidated case file?), not the topic it discusses.
4. If Axis 2 is **not** `Masterfile`: assign **Axis 3** (zero or more
   substantive-issue codes) and **Axis 4** (zero or more procedural-issue
   codes) that the document actually addresses. It's normal for many
   documents (routine correspondence, notices) to get zero Axis 3/4 codes —
   don't force a tag that doesn't fit.
5. If Axis 2 **is** `Masterfile`: leave Axis 3 and Axis 4 empty. Do not tag
   substantive/procedural issues on a Masterfile record itself — those
   belong on the individual pleadings it consolidates, if/when those are
   tagged as separate documents.

Tag at the most specific applicable Axis 3/4 code (a child code like `2A0`
rather than its parent header `200`) when one clearly fits; the round-hundred
header codes exist mainly for cases that only fit at that broader level.

## 4. Incremental tagging is expected, not an edge case

You do not need all four axes decided in one pass. `ingest/load_axis_tags.py`
treats a blank axis in an export row as "not provided this pass" and leaves
that axis's existing value(s) untouched — it never blanks prior work. Typical
pattern: a first pass assigns Axis 1/2 across a whole vault quickly, then a
second, slower pass adds Axis 3/4 where a reviewer has time to read closely.

## 5. Exporting from Harvey and loading into SQL

Export the Review Table to CSV or JSON with (at minimum) these columns:

```
entry_id, axis1, axis2, axis3, axis4
```

- `axis3`/`axis4` are multi-value: `;`-separated in CSV (e.g. `110;120`), or
  a JSON array with `--json`.
- Leave a column blank/absent to mean "not tagged this pass" (see §4).

Then load it with the same loader Phase 1's codebase already ships:

```bash
# validate first — the default is a dry run (no DB writes):
python -m ingest.load_axis_tags harvey_export.csv --rejects rejects.csv

# then write:
python -m ingest.load_axis_tags harvey_export.csv --apply --rejects rejects.csv

# JSON export:
python -m ingest.load_axis_tags harvey_export.json --json --apply
```

Full signature:
`python -m ingest.load_axis_tags path [--json] [--apply] [--batch-size 500] [--rejects out.csv]`

Rejected rows (unknown `entry_id`, an axis value not in the controlled
vocabulary, or a Masterfile-with-Axis-3/4 violation) go to `--rejects` with
the specific reason — read it and fix the export (or the tagging) rather than
re-exporting blind. The loader is idempotent: re-running the same export
(or a corrected one) converges rather than duplicating anything.

## 6. Verification

```sql
-- Coverage: how many loaded documents have each axis tagged at all?
SELECT
  (SELECT COUNT(*) FROM con.document) AS total_documents,
  (SELECT COUNT(*) FROM con.document_axis1) AS axis1_tagged,
  (SELECT COUNT(*) FROM con.document_axis2) AS axis2_tagged,
  (SELECT COUNT(DISTINCT entry_id) FROM con.document_axis3) AS axis3_tagged,
  (SELECT COUNT(DISTINCT entry_id) FROM con.document_axis4) AS axis4_tagged;

-- Must always return zero: the Masterfile rule is enforced by triggers, but
-- this is a cheap sanity check against anything that bypassed them.
SELECT a2.entry_id
FROM con.document_axis2 a2
WHERE a2.value = 'Masterfile'
  AND (EXISTS (SELECT 1 FROM con.document_axis3 a3 WHERE a3.entry_id = a2.entry_id)
    OR EXISTS (SELECT 1 FROM con.document_axis4 a4 WHERE a4.entry_id = a2.entry_id));

-- Most-used Axis 3/4 codes (a quick sanity read on whether tagging looks reasonable):
SELECT a3.code, ax.label, COUNT(*) AS n
FROM con.document_axis3 a3
JOIN con.axis3_substantive_issue ax ON ax.code = a3.code
GROUP BY a3.code, ax.label
ORDER BY n DESC;
```

## 7. If Harvey can't be pointed at `ingest/load_axis_tags.py` directly

The guide above assumes an operator exports from Harvey and runs the loader
by hand. If your Harvey deployment can call out to a script or webhook
directly, it can invoke the same CLI (or import `ingest.load_axis_tags.
load_tag_rows(conn, rows)` as a library call) instead of a manual
export/import step — the contract (one row per `entry_id`, blank = not
provided this pass, Masterfile rule enforced before any write) is identical
either way. No second loader or alternate schema is needed.
