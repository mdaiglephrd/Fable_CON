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
  fixtureGetProceeding,
} from './fixtures';
import type { Proceeding } from './docketEngine';
import type {
  CaseReader,
  CitatorReport,
  DeadlineCalcResponse,
  DocketEvent,
  Paged,
  ResearchProject,
  SavedAlert,
  SearchResponse,
  StatuteDetail,
  StatuteListItem,
  TopicDetail,
  TopicNode,
  WikiArticle,
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
  return req(`/history/${encodeURIComponent(docketId)}${qs({ type })}`);
}

/** GET /stats?range= — outcome aggregates. */
export async function getStats(range: 'all' | '3yr' | '1yr' = 'all'): Promise<Record<string, unknown>> {
  return req(`/stats${qs({ range })}`);
}

/** POST /deadlines/calculate */
export async function calculateDeadlines(input: {
  family: string;
  triggerEvent: string;
  date: string;
}): Promise<DeadlineCalcResponse> {
  return req(`/deadlines/calculate`, { method: 'POST', body: JSON.stringify(input) });
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
// Workspace CRUD (projects / alerts / wiki) — in-memory when on fixtures
// ---------------------------------------------------------------------------

const memProjects: ResearchProject[] = [];
const memAlerts: SavedAlert[] = [];

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

export async function listWiki(): Promise<Paged<WikiArticle>> {
  return req(`/wiki`);
}

export async function getWikiArticle(articleId: string): Promise<WikiArticle> {
  return req(`/wiki/${encodeURIComponent(articleId)}`);
}

export async function createWikiRevision(
  articleId: string,
  input: { author?: string; diff?: unknown },
): Promise<unknown> {
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
  return req(
    `/wiki/${encodeURIComponent(articleId)}/revisions/${encodeURIComponent(String(revisionId))}/review`,
    { method: 'POST', body: JSON.stringify({ action }) },
  );
}
