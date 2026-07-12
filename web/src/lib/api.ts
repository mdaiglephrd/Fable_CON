/*
 * Typed API client for the research-layer endpoints (api/routers/*.py).
 *
 * - Base URL from VITE_API_BASE (default '/api').
 * - When VITE_USE_FIXTURES=true (the default in dev) every read endpoint is
 *   served from the bundled con-corpus fixtures so the console runs
 *   standalone; workspace CRUD is kept in-memory.
 */
import {
  caseIdForDocket,
  fixtureGetCase,
  fixtureGetCitator,
  fixtureGetHistory,
  fixtureGetProceeding,
} from './fixtures';
import { computeDeadlines } from './deadlineRules';
import wikiFixturesJson from './wikiFixtures.json';
import type { Proceeding } from './docketEngine';
import type {
  CaseReader,
  CitatorReport,
  DeadlineCalcResponse,
  DocketEvent,
  Paged,
  ReportEvent,
  ResearchProject,
  SavedAlert,
  SearchResponse,
  StatuteDetail,
  StatuteListItem,
  TopicDetail,
  TopicNode,
  WikiArticleDetail,
  WikiBodyBlock,
  WikiIndex,
  WikiPendingEdit,
  WikiRevision,
} from './types';

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api';

const fixturesFlag = import.meta.env.VITE_USE_FIXTURES as string | undefined;
export const USE_FIXTURES: boolean =
  fixturesFlag != null ? fixturesFlag === 'true' : import.meta.env.DEV;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v));
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

// ---------------------------------------------------------------------------
// Research-layer reads
// ---------------------------------------------------------------------------

/** GET /cases/{id} — the case-reader payload. */
export async function getCase(entryId: string | number): Promise<CaseReader> {
  if (USE_FIXTURES) {
    const rec = fixtureGetCase(String(entryId));
    if (!rec) throw new ApiError(404, `No opinion found for ${entryId}.`);
    return rec;
  }
  return req<CaseReader>(`/cases/${encodeURIComponent(String(entryId))}`);
}

export interface ProceedingResponse extends Proceeding {
  docketId: string;
  source?: string;
  events?: DocketEvent[];
  facility?: string;
  projectTitle?: string;
  headerNum?: string;
  county?: string;
}

/** GET /dockets/{docketId}/proceeding — docket-engine proceeding view. */
export async function getProceeding(docketId: string): Promise<ProceedingResponse> {
  if (USE_FIXTURES) {
    const p = fixtureGetProceeding(docketId);
    if (!p) throw new ApiError(404, `Docket ${docketId} not found.`);
    return p;
  }
  return req<ProceedingResponse>(`/dockets/${encodeURIComponent(docketId)}/proceeding`);
}

/** GET /citator/{id} — how-cited flags, citing cases, table of authorities. */
export async function getCitator(entryId: string | number): Promise<CitatorReport> {
  if (USE_FIXTURES) {
    const id = caseIdForDocket(String(entryId)) ?? String(entryId);
    const report = fixtureGetCitator(id);
    if (!report) throw new ApiError(404, `No citator report for ${entryId}.`);
    return report;
  }
  return req<CitatorReport>(`/citator/${encodeURIComponent(String(entryId))}`);
}

/** GET /topics — full key-number tree. */
export async function getTopics(): Promise<{ topics: TopicNode[]; total: number }> {
  return req(`/topics`);
}

/** GET /topics/{topicId} — key-number detail + documents. */
export async function getTopic(topicId: string): Promise<TopicDetail> {
  return req(`/topics/${encodeURIComponent(topicId)}`);
}

/** GET /statutes */
export async function getStatutes(kind?: 'OCGA' | 'RULE'): Promise<Paged<StatuteListItem>> {
  return req(`/statutes${qs({ kind })}`);
}

/** GET /statutes/{id} */
export async function getStatute(statuteId: string): Promise<StatuteDetail> {
  return req(`/statutes/${encodeURIComponent(statuteId)}`);
}

/** GET /history/{docketId}?type= — docket_event timeline. */
export async function getHistory(
  docketId: string,
  type?: string,
): Promise<{ docketId: string; items: DocketEvent[]; total: number }> {
  if (USE_FIXTURES) {
    const all = fixtureGetHistory(docketId);
    if (!all) throw new ApiError(404, `Docket ${docketId} not found.`);
    const items = type ? all.filter((e) => e.type === type) : all;
    return { docketId, items, total: items.length };
  }
  return req(`/history/${encodeURIComponent(docketId)}${qs({ type })}`);
}

/** GET /stats?range= — outcome aggregates. */
export async function getStats(range: 'all' | '3yr' | '1yr' = 'all'): Promise<Record<string, unknown>> {
  return req(`/stats${qs({ range })}`);
}

/** POST /deadlines/calculate — fixture mode computes from the local port of
 * common/deadline_rules.py (see lib/deadlineRules.ts). */
export async function calculateDeadlines(input: {
  family: string;
  triggerEvent: string;
  date: string;
}): Promise<DeadlineCalcResponse> {
  if (USE_FIXTURES) {
    const base = new Date(`${input.date}T00:00:00`);
    if (isNaN(base.getTime())) throw new ApiError(400, `Invalid date ${input.date}.`);
    const deadlines = computeDeadlines(input.family, input.triggerEvent, base).map((d) => ({
      label: d.label,
      dueDate: d.dueDate.toISOString().slice(0, 10),
      basisStatute: d.basisStatute,
      description: d.description,
    }));
    return { ...input, deadlines };
  }
  return req(`/deadlines/calculate`, { method: 'POST', body: JSON.stringify(input) });
}

/** GET /reports/events — weekly DCH report events (live only; the Reports
 * view renders bundled digest fixtures when USE_FIXTURES). */
export async function reportEvents(
  params: Record<string, string | number | undefined> = {},
): Promise<Paged<ReportEvent>> {
  return req(`/reports/events${qs(params)}`);
}

// ---------------------------------------------------------------------------
// v1 inventory endpoints (search / matters / documents)
// ---------------------------------------------------------------------------

/** GET /search?q=&scope= — full-text search over matters/documents/events. */
export async function search(q: string, scope = 'all', limit = 50): Promise<SearchResponse> {
  return req(`/search${qs({ q, scope, limit })}`);
}

/** GET /matters — filtered matter list (facet parameters pass through). */
export async function searchMatters(
  params: Record<string, string | number | undefined>,
): Promise<Paged<Record<string, unknown>>> {
  return req(`/matters${qs(params)}`);
}

/** GET /matters/{docketId} */
export async function getMatter(docketId: string): Promise<Record<string, unknown>> {
  return req(`/matters/${encodeURIComponent(docketId)}`);
}

/** GET /documents — filtered document list. */
export async function searchDocuments(
  params: Record<string, string | number | undefined>,
): Promise<Paged<Record<string, unknown>>> {
  return req(`/documents${qs(params)}`);
}

// ---------------------------------------------------------------------------
// Workspace CRUD (projects / alerts / wiki) — in-memory when on fixtures,
// seeded with the comp's sample workspace so every screen renders standalone.
// ---------------------------------------------------------------------------

const memProjects: ResearchProject[] = [
  {
    projectId: 'mri-need-bartow-psa',
    name: 'MRI need — Bartow PSA',
    description:
      'Every determination construing the MRI need methodology (Rule 111-2-2-.40) in the Bartow primary service area, for the Riverstone remand.',
    tags: ['III. Substantive Review', 'IV. Imaging (MRI/CT/PET)'],
    status: 'open',
    createdAt: 'Jun 18, 2026',
    items: [
      { itemId: 1, entryId: null, docketId: '2026007', note: 'Riverstone Imaging — Ct. App. opinion; remand posture' },
      { itemId: 2, entryId: null, docketId: '2026002', note: 'In re Three Rivers Imaging — Commissioner final order' },
      { itemId: 3, entryId: null, docketId: '2025028', flagged: true, note: 'Cardiac cath methodology — different rule, not relevant' },
    ],
  },
  {
    projectId: 'cardiac-cath-denials',
    name: 'Cardiac cath denials 2024–2026',
    description: 'Denial patterns under the Rule 111-2-2-.22(4)(c) volume threshold.',
    tags: ['III. Substantive Review', 'V. Adjudication'],
    status: 'complete',
    createdAt: 'May 2, 2026',
    items: [
      { itemId: 1, entryId: null, docketId: '2025028', note: 'Northridge — 612 projected cases below the 750 minimum' },
      { itemId: 2, entryId: null, docketId: '2026004', flagged: true, note: 'Psychiatric beds — different methodology' },
    ],
  },
];

const memAlerts: SavedAlert[] = [
  {
    alertId: 'alert-docket-riverstone',
    alertType: 'Docket Watch',
    name: 'Riverstone Imaging, LLC v. DCH — CON 2026007',
    description: 'Alert when any new filing, decision, or related citation is added to this docket.',
    frequency: 'Immediate',
    active: true,
    createdAt: 'Mar 2, 2026',
    newCount: 2,
    latest: [
      ['b', 'Apr. 8, 2026'],
      ' — Notice of Remand Status Report filed by Riverstone Imaging, LLC.',
    ],
  },
  {
    alertId: 'alert-search-mri-need',
    alertType: 'Search Alert',
    name: '"MRI need methodology" — All CON Sources',
    description: 'Alert when new determinations, decisions, or opinions match this search.',
    frequency: 'Daily digest',
    active: true,
    createdAt: 'Feb 11, 2026',
    newCount: 1,
    latest: [
      ['b', 'Apr. 14, 2026'],
      ' — 1 new result: ',
      ['i', 'Three Rivers Health, LLC v. DCH'],
      ', 376 Ga. App. 102 (Mar. 2026).',
    ],
  },
  {
    alertId: 'alert-statute-rule40',
    alertType: 'Statute Watch',
    name: 'Ga. Comp. R. & Regs. 111-2-2-.40 — MRI Need Methodology',
    description: 'Alert when this rule section is amended or a rulemaking notice is published.',
    frequency: 'Immediate',
    active: true,
    createdAt: 'Jan 20, 2026',
    newCount: 0,
    latest: [
      'Proposed amendments open for public comment through ',
      ['b', 'Jul. 15, 2026'],
      '. See ',
      ['stat', 'Rule 111-2-2-.40', 'rule-111-2-2-.40'],
      '.',
    ],
  },
];

export async function listProjects(): Promise<Paged<ResearchProject>> {
  if (USE_FIXTURES) return { items: memProjects, total: memProjects.length };
  return req(`/projects`);
}

export async function createProject(input: {
  name: string;
  description?: string;
  tags?: string[];
}): Promise<ResearchProject> {
  if (USE_FIXTURES) {
    const project: ResearchProject = {
      projectId: input.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40),
      name: input.name,
      description: input.description,
      tags: input.tags ?? [],
      status: 'open',
      createdAt: new Date().toISOString(),
      items: [],
    };
    memProjects.unshift(project);
    return project;
  }
  return req(`/projects`, { method: 'POST', body: JSON.stringify(input) });
}

export async function getProject(projectId: string): Promise<ResearchProject> {
  if (USE_FIXTURES) {
    const p = memProjects.find((x) => x.projectId === projectId);
    if (!p) throw new ApiError(404, `Project ${projectId} not found.`);
    return p;
  }
  return req(`/projects/${encodeURIComponent(projectId)}`);
}

export async function addProjectItem(
  projectId: string,
  item: { entryId?: number | string; docketId?: string; flagged?: boolean; note?: string },
): Promise<unknown> {
  if (USE_FIXTURES) {
    const p = memProjects.find((x) => x.projectId === projectId);
    if (!p) throw new ApiError(404, `Project ${projectId} not found.`);
    const entryId = item.entryId == null ? null : Number(item.entryId) || null;
    p.items = [
      ...(p.items ?? []),
      { ...item, entryId, itemId: (p.items?.length ?? 0) + 1 },
    ];
    return item;
  }
  return req(`/projects/${encodeURIComponent(projectId)}/items`, {
    method: 'POST',
    body: JSON.stringify(item),
  });
}

export async function completeProject(projectId: string): Promise<unknown> {
  if (USE_FIXTURES) {
    const p = memProjects.find((x) => x.projectId === projectId);
    if (p) p.status = 'complete';
    return p ?? {};
  }
  return req(`/projects/${encodeURIComponent(projectId)}/complete`, { method: 'POST' });
}

export async function listAlerts(): Promise<Paged<SavedAlert>> {
  if (USE_FIXTURES) return { items: memAlerts, total: memAlerts.length };
  return req(`/alerts`);
}

export async function createAlert(input: {
  name: string;
  query?: unknown;
  scope?: string;
  frequency?: string;
}): Promise<SavedAlert> {
  if (USE_FIXTURES) {
    const alert: SavedAlert = {
      alertId: `alert-${memAlerts.length + 1}`,
      active: true,
      createdAt: new Date().toISOString(),
      ...input,
    };
    memAlerts.unshift(alert);
    return alert;
  }
  return req(`/alerts`, { method: 'POST', body: JSON.stringify(input) });
}

export async function deleteAlert(alertId: string): Promise<unknown> {
  if (USE_FIXTURES) {
    const i = memAlerts.findIndex((a) => a.alertId === alertId);
    if (i >= 0) memAlerts[i].active = false;
    return {};
  }
  return req(`/alerts/${encodeURIComponent(alertId)}`, { method: 'DELETE' });
}

// --- Wiki ------------------------------------------------------------------

interface WikiFixtureArticle extends Omit<WikiArticleDetail, 'pending'> {
  group: string;
  body: WikiBodyBlock[];
  revisions: WikiRevision[];
}

interface WikiFixtureShape {
  groups: string[];
  articles: WikiFixtureArticle[];
  pending: WikiPendingEdit;
}

const WIKI_FIXTURE = wikiFixturesJson as unknown as WikiFixtureShape;

// In-memory review state (fixture mode): one pending suggested edit that can
// be approved (merged into the article body) or rejected.
let memWikiPending: WikiPendingEdit | null = { ...WIKI_FIXTURE.pending };
const memWikiApplied: Record<string, { heading: string; text: string; date: string }> = {};
const WIKI_APPLIED_DATE = 'Jun 25, 2026'; // the console's frozen "today"

export async function listWiki(): Promise<WikiIndex> {
  if (USE_FIXTURES) {
    const groups = WIKI_FIXTURE.groups
      .map((group) => ({
        group,
        articles: WIKI_FIXTURE.articles
          .filter((a) => a.group === group)
          .map((a) => {
            const applied = memWikiApplied[a.articleId];
            return {
              id: a.articleId,
              title: a.title,
              readTime: a.readTime,
              lead: a.lead,
              updatedAt: applied ? applied.date : a.updated,
              justUpdated: !!applied,
            };
          }),
      }))
      .filter((g) => g.articles.length > 0);
    const pendingTitle = memWikiPending
      ? WIKI_FIXTURE.articles.find((a) => a.articleId === memWikiPending?.articleId)?.title
      : null;
    return {
      groups,
      total: WIKI_FIXTURE.articles.length,
      pendingArticleId: memWikiPending?.articleId ?? null,
      pendingArticleTitle: pendingTitle ?? null,
    };
  }
  return req<WikiIndex>(`/wiki`);
}

export async function getWikiArticle(articleId: string): Promise<WikiArticleDetail> {
  if (USE_FIXTURES) {
    const raw = WIKI_FIXTURE.articles.find((a) => a.articleId === articleId);
    if (!raw) throw new ApiError(404, `Wiki article ${articleId} not found.`);
    const applied = memWikiApplied[articleId];
    const body: WikiBodyBlock[] = applied
      ? [...raw.body, { h: applied.heading }, { p: [applied.text] }]
      : raw.body;
    const revisions: WikiRevision[] = [
      ...(applied
        ? [{ date: applied.date, text: 'Published suggested update from completed research', highlight: true }]
        : []),
      ...raw.revisions,
    ];
    return {
      ...raw,
      body,
      revisions,
      updated: applied ? applied.date : raw.updated,
      justUpdated: !!applied,
      pending: memWikiPending?.articleId === articleId ? memWikiPending : null,
    };
  }
  const raw = await req<Record<string, unknown>>(`/wiki/${encodeURIComponent(articleId)}`);
  return {
    articleId: String(raw.articleId ?? articleId),
    group: (raw.groupName as string | undefined) ?? undefined,
    title: raw.title as string | undefined,
    updated: raw.updatedAt as string | undefined,
    body: Array.isArray(raw.body) ? (raw.body as WikiBodyBlock[]) : undefined,
    revisions: Array.isArray(raw.revisions) ? (raw.revisions as WikiRevision[]) : undefined,
    pending: null,
  };
}

export async function createWikiRevision(
  articleId: string,
  input: { author?: string; diff?: unknown },
): Promise<unknown> {
  if (USE_FIXTURES) {
    const diff = (input.diff ?? {}) as { newHeading?: string; newText?: string };
    memWikiPending = {
      articleId,
      revisionId: Date.now(),
      author: input.author,
      newHeading: diff.newHeading,
      newText: diff.newText,
      submittedAt: WIKI_APPLIED_DATE,
    };
    return memWikiPending;
  }
  return req(`/wiki/${encodeURIComponent(articleId)}/revisions`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function reviewWikiRevision(
  articleId: string,
  revisionId: string | number,
  action: 'approve' | 'reject',
): Promise<unknown> {
  if (USE_FIXTURES) {
    if (memWikiPending?.articleId === articleId) {
      if (action === 'approve') {
        memWikiApplied[articleId] = {
          heading: memWikiPending.newHeading ?? 'Suggested update',
          text: memWikiPending.newText ?? '',
          date: WIKI_APPLIED_DATE,
        };
      }
      memWikiPending = null;
    }
    return { articleId, revisionId, status: action === 'approve' ? 'approved' : 'rejected' };
  }
  return req(
    `/wiki/${encodeURIComponent(articleId)}/revisions/${encodeURIComponent(String(revisionId))}/review`,
    { method: 'POST', body: JSON.stringify({ action }) },
  );
}
