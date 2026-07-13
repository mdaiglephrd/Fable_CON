# Georgia CON Research Console (`web/`)

React SPA for the CON research layer — a high-fidelity recreation of the design
handoff in `web/design-reference/` (do not ship that folder). All 28 handoff
screens (the phase-1 shell/router/core five plus the full phase-2 build-out)
are real implementations — there are no remaining placeholders.

## Stack

- **Vite 5 + React 18 + TypeScript** (strict, `tsc --noEmit` in the build)
- **react-router-dom v6** — one route per handoff view, lazy-loaded
- **vitest** — docket-engine parity test
- No UI libraries; all styling is hand-rolled CSS from the design tokens
  (`src/styles/tokens.css`, dark theme default, light theme via
  `data-theme="light"`, persisted to `localStorage`).

## Dev

```bash
cd web
npm ci
npm run dev          # http://localhost:5173 — fixture mode by default
```

In dev the console runs **standalone on bundled fixtures** (the con-corpus
sample data + the docket engine). Environment switches:

| Variable            | Default            | Meaning                                             |
| ------------------- | ------------------ | --------------------------------------------------- |
| `VITE_USE_FIXTURES` | `true` in dev      | `true` → serve reads from `src/lib/fixtures.ts`     |
| `VITE_API_BASE`     | `/api`             | Base URL of the FastAPI research API                |

Point at a live API:

```bash
VITE_USE_FIXTURES=false VITE_API_BASE=https://gacon-dev-api.azurewebsites.net npm run dev
```

## Test

```bash
npm test             # vitest — docket-engine parity (10 golden records)
```

`src/lib/docketEngine.ts` is the TypeScript port of
`tests/fixtures/handoff/docket-engine.js` and must stay byte-for-byte
in parity with `tests/fixtures/handoff/golden_proceeding.json` (which also
pins `common/proceeding.py`, the Python port). If the reference engine
changes, regenerate the golden file and fix all ports together.

`src/lib/corpus.json` is generated from the handoff corpus — re-run
`npm run generate:corpus` only when `tests/fixtures/handoff/con-corpus.js`
changes (the output is committed).

## Build

```bash
npm run build        # tsc --noEmit && vite build -> dist/
npm run preview      # serve the production build locally
```

## Deploy (Azure Static Web Apps, Free plan)

See `infra/README.md` step 7 ("Deploy the research console") and
`docs/06-research-console-buildout.md` Phase 4. Short version:

```bash
cd web
npm ci && npm run build
npx @azure/static-web-apps-cli deploy ./dist \
  --deployment-token <swa-deployment-token> --env production
```

`staticwebapp.config.json` ships with the build: SPA fallback rewrite to
`/index.html`, all routes restricted to `authenticated` (401 → redirect to
`/.auth/login/aad`), and the Entra ID identity provider. Before deploying,
replace `<tenant-id>` in `openIdIssuer` and set `AZURE_CLIENT_ID` /
`AZURE_CLIENT_SECRET` in the SWA portal (Configuration → Application
settings). Set `VITE_API_BASE` at build time to the API host and make sure
the API's `CONSOLE_ORIGIN` CORS allow-list includes the SWA hostname.

## Routes

Core (high fidelity to the comp; `/document/:entryId` and `/docket/:docketId`
are the deep-link routes the Copilot agent depends on — do not rename them):

| Route                 | Screen                                                      |
| --------------------- | ----------------------------------------------------------- |
| `/`                   | Home — hero search, quick actions, docket types, activity   |
| `/results?q=&scope=`  | Search results — facets, sort, list/snippet toggle          |
| `/document/:entryId`  | Case reader — treatment banner, headnotes, opinion, sidebar |
| `/docket/:docketId`   | Docket console — flowchart / timeline / table, tooltips     |
| `/citator/:entryId`   | Trace™ citator — flags, citing cases, authorities           |

Knowledge base, research, proceedings, and analytics (all real screens, wired
to `src/lib/api.ts`; fixture mode by default so every one renders standalone):

| Route                              | Screen                                                          |
| ----------------------------------- | ---------------------------------------------------------------- |
| `/topics`, `/topics/:topicId`       | Topic & key-number tree with detail (authorities, sub-keys, cases) |
| `/statutes`                        | Statutes & Rules index (O.C.G.A. + DCH rules, kind tabs)         |
| `/statute/:statuteId`              | Annotated statute/rule reader — TOC, cross-refs, citing cases    |
| `/history`, `/history/:docketId`   | Docket filing timeline, filterable by event type                |
| `/alerts`                          | Saved-search / docket-watch manager — list, create, deactivate  |
| `/applications`                    | Live docket tracker — status cards, type tabs, mini progress    |
| `/submit`                          | 3-step submission wizard (details → metadata → review)          |
| `/kb`                              | Knowledge Base landing — hub into Wiki / Statutes / Topics      |
| `/wiki`, `/wiki/:articleId`        | CON Wiki index + article (TOC, related, revisions, edit review) |
| `/research`                        | Research landing — quick search / new project / library entries |
| `/search/new`                      | Advanced structured query builder                                |
| `/projects/new`                    | New research project form                                        |
| `/library`                         | Research library — open vs. saved project cards                 |
| `/projects/:projectId`             | Project detail — saved/flagged documents, resume/complete       |
| `/proceedings`                     | My Proceedings landing — tracked matters, alerts/history hubs   |
| `/proceedings/history`             | Proceedings activity log — orders, filings, alerts, deadlines   |
| `/tools`                           | Analytics & Tools hub                                            |
| `/stats`                           | Outcome statistics — KPIs, by-service/year/type, appeal panel   |
| `/calculator`                      | Deadline calculator (docket family + trigger event + date)      |
| `/compare`                         | Side-by-side two-decision comparison                             |
| `/map`                             | Service-area map — 159-county tile choropleth                   |
| `/upload`                          | Upload landing                                                   |
| `/reports`                         | Weekly digest — filings, determinations, deadlines, alerts      |

Fixture-only data lives in `src/lib/{recentDockets.json, taxonomy.ts,
statutesData.ts, wikiFixtures.json, deadlineRules.ts, vocab.ts}`; the last two
are hand ports of `common/deadline_rules.py` and `common/vocab.py` used only
when `VITE_USE_FIXTURES=true` (the Python modules stay the source of truth —
keep them in sync by hand). `src/lib/taxonomy.ts` and `src/lib/statutesData.ts`
mirror the design comp's TAXONOMY/KEY_DETAILS and STATUTE_TOC/STATUTE_CONTENT/
RULES_CONTENT blocks.
