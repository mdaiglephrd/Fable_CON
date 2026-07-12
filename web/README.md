# Georgia CON Research Console (`web/`)

React SPA for the CON research layer — a high-fidelity recreation of the design
handoff in `web/design-reference/` (do not ship that folder). Phase 1 delivers
the global shell, the full route table, and the five core screens; everything
else renders a routed "coming in phase 2" page so navigation never dead-ends.

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

Core (phase 1, high fidelity to the comp):

| Route                 | Screen                                                      |
| --------------------- | ----------------------------------------------------------- |
| `/`                   | Home — hero search, quick actions, docket types, activity   |
| `/results?q=&scope=`  | Search results — facets, sort, list/snippet toggle          |
| `/document/:entryId`  | Case reader — treatment banner, headnotes, opinion, sidebar |
| `/docket/:docketId`   | Docket console — flowchart / timeline / table, tooltips     |
| `/citator/:entryId`   | Trace™ citator — flags, citing cases, authorities           |

`/document/:entryId` and `/docket/:docketId` are the deep-link routes the
Copilot agent depends on — do not rename them.

Phase-2 placeholders (routed, breadcrumbed): `/topics`, `/topics/:topicId`,
`/statutes`, `/statute/:statuteId`, `/history`, `/alerts`, `/submit`,
`/applications`, `/stats`, `/calculator`, `/compare`, `/map`, `/kb`, `/wiki`,
`/wiki/:articleId`, `/research`, `/search/new`, `/projects/new`, `/library`,
`/projects/:projectId`, `/proceedings`, `/proceedings/history`, `/tools`,
`/upload`, `/reports`.

## Phase 2

The placeholder views above get their full implementations (topic tree,
statute reader, wiki + review flow, alerts manager, submission wizard, stats,
calculator, compare, map, research projects), wired to the already-typed API
client (`src/lib/api.ts` covers cases, proceedings, citator, topics, statutes,
history, stats, deadlines, search/matters/documents, and projects/alerts/wiki
CRUD).
