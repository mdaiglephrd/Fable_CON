# Metadata Extraction Spec — by document type

This is the working spec for **what to capture from each CON record** so the research console
(case reader, docket console, citator, topics, statutes, deadline calculator, stats) has the data it
needs. You perform ingestion; this tells you exactly what each field is, where it comes from, which
database column/table holds it, and which console view consumes it.

Read this alongside:
- `DESIGN.md` → "RESEARCH LAYER (v2)" — the exact table/column definitions.
- `docs/03-ingestion-runbook.md` — how to run the loaders.
- `tests/fixtures/handoff/con-corpus.js` — a fully-worked example (the *Riverstone* record) showing every
  field populated.

## How data gets in — two intake paths + one editorial pass

1. **Tag export (you already produce this).** A CSV/JSON, one row per document, loaded by
   `ingest/load_tags.py`. It carries the *objective, structured* fields (identifiers, dates, parties,
   outcome, service type). The research layer **adds columns** to this export — see §A.
2. **Document-text intake (new).** The document bodies (OCR text / PDFs) are run through Azure AI
   Document Intelligence and emitted as JSONL, loaded by `ingest/load_document_text.py`. This carries
   *content*: full text + numbered paragraphs. Format in §B.
3. **Editorial pass (in the console).** The *analytical* fields a machine cannot reliably decide —
   headnotes, key-number classification, treatment/good-law signal, editorial synopsis, citation
   treatment — are authored/verified by a person through the console, reusing the existing
   `validation_status` workflow (`Unvalidated → Validated / Corrected / Rejected`).

**Source legend used in every table below:**

| Code | Meaning |
|---|---|
| **T** | Tagger-supplied — a column in the tag export (§A) |
| **X** | Auto-extractable from document text (OCR / layout / regex / parse) — via §B intake |
| **E** | Editorial — human legal analysis in the console validation pass |
| **D** | Derived — computed by the system from other rows + the statutory framework (you store nothing) |

`T/X` = either path is acceptable; pick whichever your workflow makes cheaper.

---

## §A. Tag-export columns (extends the existing v1 export)

The v1 columns still apply (see `docs/03`). **Add** these columns for the research layer. Blank is
allowed — the loader treats blank as "not provided" and never overwrites a populated value.

### A.1 New matter-level columns (repeat on each of the matter's document rows)
`contact_officer`, `project_description`, `estimated_cost` (number), `primary_service_area`
(`;`-separated county names), `docket_family` (CON | DET | DET-EQT | DET-ASC | LNR-ASC | LNR-EQT — if
omitted, the loader derives it from the docket id), `letter_of_intent_date`, `deemed_complete_date`,
`decision_deadline`, `batching_cycle`, `competing_docket_ids` (`;`-separated canonical dockets).

### A.2 New document-level columns
`title` (short display caption), `text_source` (ocr | native | tag).

> Analytical fields (headnotes, treatment, topics, synopsis, citation edges, counsel roles) are **not**
> tag-export columns — they are editorial (E) and are entered in the console, OR provided in richer
> optional side-files if your tagging team produces them (formats in §D).

---

## §B. Document-text intake JSONL (one object per document)

`ingest/load_document_text.py` consumes this (the output of your Document Intelligence run):

```json
{"entry_id": 9000030, "text_source": "ocr", "di_model": "prebuilt-layout", "di_confidence": 0.98,
 "full_text": "...entire document text...",
 "paragraphs": [{"num": "1", "text": "In February 2023, Riverstone Imaging filed..."},
                {"num": "2", "text": "The Department, in its initial decision..."}]}
```
→ populates `con.document_text` (full_text, char_count, di_model, di_confidence) and
`con.opinion_paragraph` (one row per paragraph; `plain_text` set now, `segs_json` defaults to a single
plain segment and is enriched with cross-links during the editorial pass).

---

## §0. Universal fields — every document (regardless of type)

| Field | Source | Column / table |
|---|---|---|
| entry_id | T | `document.entry_id` (key) |
| docket_id (+ variants) | T/X | `document.docket_id`, `matter_docket_variant` |
| docket_family | T/D | `matter.docket_family` |
| doc_type (controlled, 14) | T | `document.doc_type` |
| doc_date, decision_level (1–5), phase | T | `document.*` |
| title / short caption | T/X | `document.title` |
| page_count, file_name, source_path | T | `document.*` |
| ocr_status, ocr_confidence, text_source | X | `document.*`, `document_text.*` |
| full_text | X | `document_text.full_text` |
| validation_status, validated_by/date, duplicate_of | T/E | `document.*` |

---

## §1. Matter / docket rollup — `con.matter`

One row per docket; most fields roll up from the documents but should be captured explicitly when known.

| Field | Source | Notes / column |
|---|---|---|
| applicant, facility, county, service_area | T | v1 |
| service_type[] (controlled, 26), matter_type, action_type | T | v1 |
| bed_count / units, year_filed | T | v1 |
| contact_officer | T/X | DCH project officer of record |
| project_description | T/X | one-line summary of the project |
| estimated_cost | T/X | total capital cost (DECIMAL) |
| primary_service_area[] | T/X | PSA county list — drives the service-area map |
| letter_of_intent_date, deemed_complete_date, decision_deadline, batching_cycle | T/X | lifecycle dates that feed the docket timeline + deadline calculator |
| competing_docket_ids[] | T/D | other applicants in the same batching group |
| final_outcome (controlled, 13), final_decision_date | T/D | v1 |
| phases_present[], highest_review_level | D | v1 |
| precedent_signal | D | valid / questioned / overturned (closed CON, from citator); noprecedent (DET) |

---

## §2. Application-stage documents — *Letter of Intent · CON Application/Request*

| Field | Source | Notes |
|---|---|---|
| filing_date (application), letter_of_intent_date | T/X | sets the review cycle / batching window (docket stage 0–1) |
| proposed service_type + action_type | T/X | map to the controlled vocabularies |
| bed / unit count | T/X | |
| project_description | T/X | |
| estimated_project_cost, capital_expenditure | X | → `matter.estimated_cost` |
| primary_service_area (counties) | X | → `matter.primary_service_area` |
| deemed_complete_date, 30-day deadline, decision_deadline | X | feed the Deadline Calculator + stage 1 dateLine |
| opposition filed (Y/N) + intervenor names | T/X | "OPPOSITION FILED" marker; intervenors → `con.counsel` (side=Intervenor) |
| referral-data / need basis asserted | E | narrative, optional — supports service-area analysis |
| contact_officer | T/X | |

---

## §3. Agency decisions — *Initial/Desk Decision (level 1) · Final Agency Decision / Commissioner Order*

| Field | Source | Notes / target |
|---|---|---|
| decision_date | T/X | `document.doc_date` / `opinion.decided_date` |
| decision_maker (planning officer / commissioner) | T/X | `document.decision_maker` |
| outcome (controlled) | T/X | Granted / Denied / Approved with conditions / … |
| conditions_text | X/E | attached CON conditions, if any |
| need_methodology_findings, service_area_used | E | the reasoning the *Riverstone* line turns on → `opinion.editorial_synopsis` / paragraphs |
| rules_applied[] (111-2-2-.xx), statutes_cited[] | X | → `con.citation` (cited_statute_id) |
| utilization / threshold findings | X/E | |
| finality_basis | D/E | HB 1339 regime (HO decision = final) vs legacy Commissioner review → `opinion.treatment_note` / regime note |
| effective_date, appeal_deadline (+30 days) | X/D | deadline derived by `common/deadline_rules.py` |
| adopts / modifies / reverses (Final Order vs HO) | X/E | `opinion.disposition_json` |
| full opinion text + numbered paragraphs | X | `con.document_text`, `con.opinion_paragraph` |
| counsel / parties | X | `con.counsel` |

---

## §4. Administrative appeal — *Hearing Officer Decision (OSAH, level 2)*

| Field | Source | Notes |
|---|---|---|
| osah_case_no | T/X | e.g. `OSAH-DCH-CON-23-118-Walsh` → `opinion.court_docket_no` |
| hearing_officer (ALJ) | T/X | `opinion.byline` / `document.decision_maker` |
| hearing_dates[], hearing_days | X | evidentiary hearing window → `con.docket_event` (Hearing) |
| decision_date, outcome | T/X | Affirmed / Reversed / Recommended-grant |
| is_recommended vs initial + adoption_status/date | X/E | was it adopted by the Commissioner? |
| issues_decided, holding_summary | E | `opinion.editorial_synopsis` |
| parties + intervenors | X | `con.counsel` |
| statutes / rules applied | X | `con.citation` |
| opinion text + paragraphs | X | `con.document_text`, `con.opinion_paragraph` |

---

## §5. Judicial opinions — *Court Order/Opinion: Superior (3) · Court of Appeals & Supreme (4)*

The richest type. This is what fills the case-reader and citator.

| Field | Source | Target |
|---|---|---|
| caption_parts (rich, party-v-party) | X | `opinion.caption_json` (segment tuples) |
| tribunal_line (court · division · published?) | X | `opinion.tribunal_line`, `opinion.is_published` |
| reporter_citations[] | X | `con.reporter_citation` (e.g. `372 Ga. App. 488`, `902 S.E.2d 144`) |
| court_docket_no | X | `opinion.court_docket_no` (`A25A0917`, `S26C0411`, `2024CV-3318`) |
| decided_date, argued_date | X | `opinion.decided_date`, `opinion.argued_date` |
| byline (authoring judge), panel / concurrences | X | `opinion.byline` (+ paragraphs) |
| disposition (Affirmed/Reversed/Remanded/Cert-denied) | X | `opinion.disposition_json` |
| standard_of_review | E | `opinion.standard_of_review` |
| intro + numbered paragraphs w/ cross-links | X→E | text=X; case/statute/topic links=E → `opinion.intro_text`, `opinion_paragraph.segs_json` |
| headnotes[] + key-number topic | E | `con.headnote` + `con.document_topic` |
| editorial_synopsis | E | `opinion.editorial_synopsis` |
| treatment / good-law flag + note | E | `opinion.treatment_level`, `opinion.treatment_note_json` |
| subsequent_history | X/E | `opinion.subsequent_history` |
| counsel[] (role, name, firm) | X | `con.counsel` |
| briefs[] | X | `con.brief` |
| table of authorities (cases/statutes cited) | X→E | `con.citation` (citing_entry_id set) |
| citing cases (how-cited) | D | reverse of `con.citation` (cited_entry_id) |

---

## §6. Determinations & LNRs — *DET · DET-EQT · DET-ASC · LNR-ASC · LNR-EQT*

| Field | Source | Notes |
|---|---|---|
| det_number, subtype (family) | T/X | subtype drives the docket-engine stage 1–2 copy |
| requestor, facility, county | T/X | |
| subject | T/X | equipment / ASC operation / activity claimed exempt |
| request_received_date, sufficiency_date, letter_issued_date | T/X | feed the DET 5-stage timeline |
| outcome | T/X | Reviewable / Not-Reviewable / CON-Required / Conditioned / LNR-Issued |
| reviewability_analysis | E | |
| statutory_basis[] (§31-6-2(23), §31-6-43(e)) | X | → `con.citation` |
| equipment_aggregation_notes (EQT) | E | anti-fragmentation / component-cost aggregation |
| filing_fee, exemption_basis (LNR) | X | |
| conditions (LNR issued w/ conditions) | X/E | |
| precedent note | D | DET binds parties only (§31-6-44) — supplied by the engine |

---

## §7. Supporting filings

| Type | Key fields (Source) | Also emits |
|---|---|---|
| **Order** (procedural) | order_type, issuing_tribunal, judge/officer, date, parties_affected, ruling_summary (X/E) | `con.docket_event` (Order) |
| **Notice** | notice_type (opposition / appeal / hearing / public), date, filing_party, deadline_triggered (X/D) | `con.docket_event` (Notice) |
| **Transcript** | hearing_date(s), tribunal, ALJ/judge, volume, pages, witnesses (T/X) | |
| **Exhibit** | exhibit_no, sponsoring_party, description, linked hearing/filing (T/X) | |
| **Brief/Memorandum** | title, party_side, attorney, firm, filed_date, page_count, court (T/X) | `con.brief` |
| **Correspondence** | date, from, to, subject (T/X) | |
| **HFR Opinion** | opinion_type, author, date, subject (T/X) | |
| **Settlement/Withdrawal** | kind, date, parties, terms_summary (T/X/E) | terminal outcome; `con.docket_event` |

Every supporting filing should also produce a **`con.docket_event`** row (date, event_type, actor,
description) so it appears on the History timeline and docket chronology.

---

## §8. Statutes & rules — `con.statute` (content records, loaded once, not per-docket)

| Field | Source | Notes |
|---|---|---|
| statute_id | T | `31-6-43`, `rule-111-2-2-.40` |
| kind | T | OCGA \| RULE |
| citation_label, title | T/X | `O.C.G.A. § 31-6-43 — Granting or Denying CON` |
| full_text, subsections[] | X | |
| cross_references[] | X/E | → `con.statute_xref` |
| effective_date, regime_note | E | HB 1339 (2024) era flags |
| citing_cases | D | reverse of `con.citation.cited_statute_id` |

---

## §9. Cross-cutting relational extractions (span multiple documents)

These are not a single document's fields — they are relationships extracted across the corpus. They are
what make the console a *research* tool rather than a file list.

| Extraction | Source | Target table | Powers |
|---|---|---|---|
| **Citation / citator edge** — citing doc → cited case/statute, with treatment, depth (1–4), pinpoint, snippet | X→E | `con.citation` | Citator ("how cited"), Table of Authorities, treatment flags, `matter.precedent_signal` |
| **Headnote + key number** — numbered holding + its CON key-number topic | E | `con.headnote`, `con.document_topic` | Document headnotes, Topics & Key Numbers tree |
| **Counsel** — role, attorney, firm, side | X | `con.counsel` | Document counsel block |
| **Proceeding stage** — per docket: stage, tribunal, date, outcome, summary, filings_count, decision_maker, duration, has_opinion | X→D | `con.proceeding_stage` | Docket console (flowchart / timeline / table) |
| **Docket event** — per filing: date, type, actor, description | X | `con.docket_event` | History view, docket chronology |

> **Proceeding stages are mostly derived.** You supply the key dates and outcomes per document; the
> statutory framework in `common/proceeding.py` (ported from the design's docket-engine) synthesizes the
> full stage-by-stage timeline (CON = 8 stages, DET-family = 5). You do **not** hand-author every stage.

---

## Editorial (E) fields — minimum viable vs. full

If tagging capacity is limited, prioritize in this order; the console degrades gracefully and flags
anything still `Unvalidated`:

1. **Objective X/T fields** for all documents (identifiers, dates, parties, outcome, text) — makes
   search, the docket timeline, and stats work.
2. **Citation edges (X)** — makes the citator and precedent signal work; the single highest-leverage
   analytical extraction.
3. **Treatment level + headnotes/topics (E)** for the *decided opinions* only (levels 2–4) — makes the
   case reader and topic browse authoritative.
4. **Editorial synopsis (E)** — nice-to-have; the console shows the intro paragraph if absent.

---

## §D. Optional editorial side-file formats

If your tagging team produces analytical data outside the console, load it with these shapes (all keyed
by `entry_id`); otherwise enter it in the console. (Loaders for these are thin and follow the
`ingest/load_tags.py` idempotent-upsert pattern.)

- **Headnotes**: `{entry_id, headnotes:[{num, topic_id, topic_label, text}]}`
- **Citations**: `{citing_entry_id, edges:[{cited_entry_id|cited_statute_id|cited_external, treatment, depth, pinpoint, snippet, topic_id}]}`
- **Counsel**: `{entry_id|docket_id, counsel:[{role, attorney_name, firm, party_side}]}`
- **Reporter citations**: `{entry_id, citations:["372 Ga. App. 488","902 S.E.2d 144"]}`

Everything above maps 1:1 to the tables defined in `DESIGN.md` → "RESEARCH LAYER (v2)".
