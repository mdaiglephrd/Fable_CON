# Handoff: Georgia CON Research Platform

## Overview
A legal/regulatory research tool for Georgia Certificate of Need (CON) law — a Westlaw/Lexis-style research console for healthcare CON attorneys and analysts. It covers case law search, docket tracking (CON and Determination proceedings), statutes/rules, a citator, topic/key-number browsing, a CON Wiki knowledge base, deadline calculation, comparison tools, service-area mapping, document submission, and saved research projects.

## About the Design Files
The files in this bundle are **design references built in HTML** (inline-styled React-like components, single-page, client-state routing) — they demonstrate intended look, content, and interaction, not production code to lift verbatim. The task is to **recreate these designs in the target codebase's environment** (React/Vue/Angular, or whatever the receiving app already uses) with its own component patterns, data layer, and routing — or, if no environment exists yet, choose the framework best suited to a research-console SPA (React + a router + a real backend for search/docket data) and implement there.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and copy are final/representative. Recreate pixel-close using the target codebase's styling system, not just as loose inspiration. Content (case names, citations, statutes) is representative sample data — see Data Model below; the app is built to run on that same data shape once backed by real records.

## Global Shell (present on every screen)
- **Top bar** (`--surface` bg, 3px solid `#8E1B1F` bottom border): left brand mark "PH"+"RD" (serif, PH in `--text`, RD in `--accent-text`) + "Research / Georgia CON" wordmark, both as a Home button. Center: scoped search bar — `<select>` scope dropdown + text input + red "Search" button (`#8E1B1F`, hover `#A82127`) + "Advanced" link opening the advanced search modal/view. Right: Alerts bell icon button (red dot badge, no count shown) and a user menu (circular avatar "JA" on `#8E1B1F`, name "J. Anderson" / "PHRD · Healthcare" two-line label, chevron). User menu dropdown: Personalization, Settings, divider, Log Out (red `#FCA5A5` text, `rgba(244,63,94,.12)` hover bg).
- **Left rail nav**: 228px fixed width, `--surface` bg, `--surface2` right border, vertical list of primary sections (Home, Research, Knowledge Base, My Proceedings, Analytics & Tools, Upload, Weekly Reports, Alerts, etc. — see nav items in the template's `leftRail` render). Active item highlighted.
- **Main content**: flexible width, scrollable, hosts one of ~27 mutually-exclusive views.
- **Breadcrumb pattern**: most non-Home views open with a `Home › Section › Subsection` breadcrumb row (12px, `--text2`, active-section links in `--accent-text` with underline-on-hover; current page plain `--text3`/`--text` text).
- **Toast notifications**: transient bottom or corner toast for actions like "Research project created," auto-dismiss ~3.2s.

## Routing / View Model
Single-page app with one `view` string in app state (`home`, `results`, `document`, `docket`, `topics`, `statute`, `citator`, `history`, `alerts`, `submit`, `applications`, `stats`, `calculator`, `compare`, `map`, `kb`, `wiki`, `statutes`, `research`, `newsearch`, `newproject`, `library`, `projectdetail`, `proceedings`, `matterhistory`, `tools`, `upload`, `reports`, plus modal-like states for advanced search, personalization, settings, wiki-review). Switching views is a single state transition (no deep linking/URL sync in this reference) — recreate with your router's route table, one route per view below, and scroll-to-top on navigation.

## Screens / Views
1. **Home** — hero search entry, quick actions/presets, docket-type shortcuts, recent activity.
2. **Search Results** — filterable/faceted case & docket results list; list vs. snippet view toggle; facet sidebar; result count and query breadcrumb.
3. **Document** — case/opinion reader: caption, citations, tribunal line, treatment banner (caution/good-law flags), editorial summary, full opinion text with cross-links (case/statute/topic), tabs (opinion/briefs), print/download actions.
4. **Docket View** — the "case console": stage-by-stage proceeding tracker (flowchart / timeline / table view toggle), substeps with status pills (COMPLETE/ACTIVE/PENDING/DENIED/etc.), outcome forks, deadline callouts, mini progress bar, precedent signal for closed dockets.
5. **Topics & Key Numbers** — hierarchical topic tree with expandable key numbers, each linking into relevant docs.
6. **Statute** — single O.C.G.A. section or DCH rule, full text, cross-references, citing-case list.
7. **Citator** — "how cited" report for a case: treatment history, citing cases table, depth-of-treatment tabs.
8. **History** — chronological event/filing timeline for a matter, filterable by type (orders/filings/hearings).
9. **Alerts** — saved-search / docket alert management list.
10. **Submit Document** — multi-step (3-step) submission wizard: doc details → metadata → review/save.
11. **Applications** — list of CON applications with status filter.
12. **Outcome Statistics (Stats)** — aggregate approval/denial analytics by docket type/region.
13. **Deadline Calculator** — event + date picker producing computed regulatory deadlines.
14. **Compare** — side-by-side comparison of two cases/dockets (left/right selectors).
15. **Service-Area Map** — map-based view with a metric selector (choropleth-style by county).
16. **Knowledge Base (landing)** — hub linking into CON Wiki and Statutes & Rules Index.
17. **CON Wiki** — index of wiki articles by group + featured article; article view with table of contents, body with cross-links, related articles, revision history, and a pending-edit review modal (approve/reject).
18. **Statutes & Rules Index** — browsable list of O.C.G.A. sections and DCH rules.
19. **Research (landing)** — entry point for Quick Search / New Research Project / Research Library.
20. **New Search (advanced builder)** — structured query builder: all-words, phrase, type, forum, outcome fields.
21. **New Research Project** — name/description/tags form to create a project.
22. **Research Library** — list of research projects, tabbed open vs. saved/complete, each a card with saved/flagged counts and tag chips.
23. **Research Project (detail)** — single project's saved/flagged documents, resume/complete actions.
24. **My Proceedings (landing)** — list of the user's tracked matters.
25. **Proceedings History** — history view scoped to one matter.
26. **Analytics & Tools (landing)** — hub linking Stats / Calculator / Compare / Map.
27. **Upload (landing)** — entry point into Submit Document.
28. **Weekly Reports** — periodic digest view.

Each view is implemented as one exclusive branch under `<main>`; recreate as one route/component per view, sharing the top bar + left rail shell as a layout wrapper.

## Design Tokens

### Colors (CSS custom properties, theme-scoped)
Dark theme (`data-theme="dark"`, default):
- `--page-bg: #020617` `--surface: #0F172A` `--surface2: #1E293B` `--border2: #334155`
- `--text: #F8FAFC` `--text2: #94A3B8` `--text3: #64748B`
- `--accent-text: #F43F5E` `--sel-bg: #F59E0B` `--sel-fg: #020617`

Light theme (`data-theme="light"`):
- `--page-bg: #F7F4EA` `--surface: #FFFFFF` `--surface2: #F1ECDD` `--border2: #D9D2C0`
- `--text: #181410` `--text2: #5F5950` `--text3: #8A8472`
- `--accent-text: #8E1B1F` `--sel-bg: #8E1B1F` `--sel-fg: #FFFFFF`

Fixed (non-themed) brand/status colors used across both themes:
- Brand red: `#8E1B1F` (buttons, top-bar border, brand mark), hover `#A82127`
- Status: complete/approved `#10B981` (bg `rgba(16,185,129,.12)`), active/gold `#F59E0B` (bg `rgba(245,158,11,.12)`), denied `#F43F5E` (bg `rgba(244,63,94,.12)`), pending/neutral `#94A3B8` / `#64748B`, current/challenged/legacy `#3B82F6` (bg `rgba(59,130,246,.12)`)
- Body text on dark shell prior to theme resolution: `#E2E8F0`
- Selection highlight: `#F59E0B` on `#020617`

### Typography
- **UI/body**: `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`, base 14px, line-height 1.45.
- **Serif (brand mark, headings, captions)**: `"Source Serif 4", Georgia, serif` — Google Font, weights 400/500/600/700, optical-size axis 8..60.
- **Monospace** (citations, docket numbers where used): `"JetBrains Mono"`, weights 400/500.

### Other tokens
- Border radius: small throughout — `2px` (buttons, inputs), `4–5px` (menus/cards), `50%` (avatars/dots).
- Shadows: dropdowns `0 10px 28px rgba(0,0,0,.45)`; search bar `0 1px 2px rgba(0,0,0,.2)`.
- Spacing: header/section padding typically `18px 32px`; breadcrumb bottom margin `8px`.

## Interactions & Behavior
- Theme toggle (dark/light) via `data-theme` attribute on the shell root — persist user choice.
- Search: type in top bar → Enter or Search button → navigates to Results view with query in state; scope `<select>` also re-runs against Results.
- Advanced search opens a structured builder (separate view/modal) with discrete fields (all words, phrase, doc type, forum, outcome); "Apply" merges into facet selection and returns to Results.
- User avatar button toggles a dropdown menu; a full-screen transparent overlay button closes it on outside click.
- Docket View has a 3-way display toggle (flowchart/timeline/table) — same underlying stage data, three renderings.
- Wiki articles support a pending-edit review flow: a "pending changes" banner opens a diff/review modal with Approve/Reject actions.
- Submit Document and New Research Project are linear multi-step forms with Back/Continue and a final save action that returns to Home/Results with a toast confirmation.
- Toasts: transient message + type (info, etc.), auto-clear after ~3.2s.
- Research projects: "resume" re-enters Results scoped to that project; "complete" marks it done and moves it to the saved/library tab.

## Data Model
Two plain-JS data modules are the reference "backend" shape — reproduce equivalent structures (or real API responses matching this shape) in the target app:

- **`con-corpus.js`** → `window.CON_CORPUS`: cases, statutes, rules, topics. Case records include id, badge/docket type, caption parts (rich-text segments), tribunal line, citations, docket number, decided date, subsequent history, a "treatment" object (good-law flag: level/word/color/rich-text explanation with cross-links), editorial summary, and full opinion text. Rich text uses a tagged-tuple segment format: plain strings for text, `["i", text]` italic, `["b", text]` bold, `["case", text, caseId]` / `["stat", text, statuteId]` / `["topic", text, keyId]` for cross-links — this lets prose reference other records without embedding React.
- **`docket-engine.js`**: builds the Docket View's stage/substep/status data for two docket-type families — CON (8 stages) and Determination variants (DET/DET-ASC/DET-EQT/LNR-ASC/LNR-EQT, 5 stages, with subtype-specific copy for stages 1–2). Status vocabulary: `complete, active, pending, nottaken, notreached, na, denied, challenged, applicable, current, legacy, approved, reviewable` — each with a label + color + tint background, reused everywhere a status pill appears.

Recreate this as a real data/API layer; the UI's job is only to render fields with this shape.

## Assets
No custom icon/image assets — all icons are inline SVG (stroke-only, ~13–16px, `currentColor`). Reference screenshots of the working prototype are in `screens/` in the source project (not required for implementation; SVGs and copy in the HTML are the source of truth).

## Files
- `Georgia CON Research.dc.html` — full application markup + view logic (all 27+ views, shell, state transitions).
- `con-corpus.js` — case/statute/rule/topic data.
- `docket-engine.js` — docket stage/status data builder.

Read the `.dc.html` top-to-bottom: the `<helmet><style>` block has the full color/theme token table; the body is the shell (top bar → left rail → main); each view is a clearly commented, mutually-exclusive block under `<main>` (search `<!-- SCREEN NAME -->`); the logic class at the bottom of the file holds all state and view-switching handlers (`switchView`, `goHome`, per-view setters).
