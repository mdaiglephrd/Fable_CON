/*
 * Shared data types for the research console.
 *
 * The corpus shapes follow tests/fixtures/handoff/con-corpus.js (the design
 * handoff's authoritative data contract); the API shapes follow the camelCase
 * responses of api/routers/*.py, which were themselves written to mirror the
 * corpus. Where the two differ slightly (e.g. brief fields) the types carry
 * both variants as optionals.
 */

/**
 * Rich-text segment format (tagged tuples):
 *   "plain string"                -> text
 *   ["i", text]                   -> italic
 *   ["b", text]                   -> bold
 *   ["case", text, caseId]        -> link to a case document
 *   ["stat", text, statuteId]     -> link to a statute/rule section
 *   ["topic", text, keyId]        -> link to a topic key number
 */
export type Seg = string | [string, string] | [string, string, string];

export type TreatmentLevel = 'positive' | 'caution' | 'negative' | 'neutral';

export interface Treatment {
  level: TreatmentLevel | string;
  word?: string;
  glyph?: string;
  bg?: string;
  text?: Seg[] | string;
}

export interface Headnote {
  num?: string;
  key?: string;
  keyId?: string;
  topic?: string;
  text?: string;
}

export interface Counsel {
  role?: string;
  name?: string;
  firm?: string;
}

export interface BriefItem {
  title?: string;
  /** con-corpus.js shape: a single preformatted meta line. */
  meta?: string;
  /** api/routers/cases.py shape: individual fields. */
  side?: string;
  attorney?: string;
  firm?: string;
  filedDate?: string;
  pageCount?: number;
}

export interface CitatorFlag {
  label: string;
  count: number;
  color?: string;
}

export interface CitingCase {
  badge?: string;
  dktNum?: string;
  treat?: string;
  level?: TreatmentLevel | string;
  title?: string;
  cite?: string;
  depth?: number;
  snippet?: string;
  pinpoint?: string;
  keys?: [string, string][];
  target?: string | number | null;
}

export interface ToaItem {
  title?: string;
  cite?: string;
  pinpoint?: string;
  target?: string | number | null;
  kind?: 'case' | 'stat' | 'external' | string;
}

export interface CaseCitatorBlock {
  flags: CitatorFlag[];
  cases?: CitingCase[];
  toa?: ToaItem[];
}

export interface FlowStage {
  stageNum?: string;
  stageLabel?: string;
  court?: string;
  title?: string;
  cite?: string;
  date?: string;
  outcome?: string;
  oc?: string; // gray | red | gold | green
  marker?: string;
  summary?: string;
  filingsCount?: number;
  judge?: string;
  duration?: string;
  isCurrent?: boolean;
  hasOpinion?: boolean;
  opinionSelf?: boolean;
  connectorRed?: boolean;
  last?: boolean;
}

/** chrono rows: [day, month, year, tag, color, title, party] */
export type ChronoEvent = string[];

export interface Paragraph {
  num?: string;
  segs: Seg[];
}

/** The case-reader payload (GET /cases/{id} — mirrors con-corpus.js records). */
export interface CaseReader {
  id?: string;
  entryId?: string | number;
  docketId?: string | null;
  badge?: string;
  dktNum?: string;
  title?: string;
  captionParts?: Seg[];
  tribunalLine?: string;
  citations?: string[];
  docketNo?: string;
  decided?: string;
  subsequent?: string;
  treatment?: Treatment | null;
  editorial?: string;
  headnotes?: Headnote[];
  byline?: string;
  intro?: string;
  paragraphs?: Paragraph[];
  disposition?: Seg[];
  meta?: Record<string, string>;
  counsel?: Counsel[];
  briefs?: BriefItem[];
  docketDays?: string;
  docketDispositions?: number;
  flow?: FlowStage[];
  chrono?: ChronoEvent[];
  citator?: CaseCitatorBlock;
  standardOfReview?: string;
  isPublished?: boolean;
}

/** GET /citator/{id} */
export interface CitatorReport {
  entryId: string | number;
  flags: CitatorFlag[];
  citingCases: CitingCase[];
  tableOfAuthorities: ToaItem[];
}

/** GET /topics */
export interface TopicNode {
  topicId: string;
  keyNumber?: string;
  title?: string;
  description?: string;
  children: TopicNode[];
}

export interface TopicDetail {
  topicId: string;
  parentTopicId?: string;
  keyNumber?: string;
  title?: string;
  description?: string;
  headnoteCount?: number;
  children: { topicId: string; keyNumber?: string; title?: string }[];
  documents: {
    entryId?: number;
    docketId?: string;
    title?: string;
    docType?: string;
    date?: string;
    badge?: string;
    applicant?: string;
    facility?: string;
  }[];
}

/** GET /statutes */
export interface StatuteListItem {
  statuteId: string;
  kind?: 'OCGA' | 'RULE' | string;
  citationLabel?: string;
  title?: string;
  effectiveDate?: string;
}

export interface StatuteDetail extends StatuteListItem {
  fullText?: string;
  regimeNote?: string;
  subsections?: unknown;
  xrefs?: { statuteId: string; citationLabel?: string; title?: string }[];
  citingCases?: CitingCase[];
}

/** GET /history/{docketId} */
export interface DocketEvent {
  eventId?: number;
  date?: string;
  type?: string;
  court?: string;
  description?: string;
  actor?: string;
  entryId?: number;
}

/** POST /deadlines/calculate */
export interface ComputedDeadline {
  label: string;
  dueDate: string;
  basisStatute?: string;
  description?: string;
}

export interface DeadlineCalcResponse {
  family: string;
  triggerEvent: string;
  date: string;
  deadlines: ComputedDeadline[];
}

/** GET /search hit */
export interface SearchHit {
  type: 'matter' | 'document' | 'event' | string;
  rank: number | null;
  record: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  scope: string;
  fulltext: boolean;
  hits: SearchHit[];
}

export interface Paged<T> {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
}

/** Research projects / alerts / wiki (workspace CRUD). */
export interface ResearchProject {
  projectId: string;
  name?: string;
  description?: string;
  tags?: string[];
  status?: string;
  createdAt?: string;
  items?: ProjectItem[];
}

export interface ProjectItem {
  itemId?: number;
  entryId?: number | null;
  docketId?: string | null;
  flagged?: boolean;
  note?: string;
}

export interface SavedAlert {
  alertId: string;
  name?: string;
  query?: unknown;
  scope?: string;
  frequency?: string;
  active?: boolean;
  createdAt?: string;
  /** Fixture-only presentation fields (comp's alert cards). */
  alertType?: string;
  description?: string;
  latest?: Seg[];
  newCount?: number;
}

export interface WikiArticle {
  articleId: string;
  groupName?: string;
  title?: string;
  toc?: unknown;
  body?: unknown;
  status?: string;
  updatedAt?: string;
}

/** GET /wiki — index grouped by group_name. */
export interface WikiIndexArticle {
  id: string;
  title?: string;
  status?: string;
  updatedAt?: string;
  readTime?: string;
  lead?: string;
  justUpdated?: boolean;
}

export interface WikiIndexGroup {
  group: string;
  articles: WikiIndexArticle[];
}

export interface WikiIndex {
  groups: WikiIndexGroup[];
  total: number;
  /** Fixture-only: title of the article with a pending suggested edit. */
  pendingArticleId?: string | null;
  pendingArticleTitle?: string | null;
}

/**
 * Wiki article body block (fixture format, wikiFixtures.json):
 * heading | paragraph | note callout | bullet list — prose in segment format.
 */
export interface WikiBodyBlock {
  h?: string;
  p?: Seg[];
  note?: Seg[];
  list?: Seg[][];
}

export interface WikiRelatedLink {
  kind: string;
  label: string;
  target: string;
}

export interface WikiRevision {
  revisionId?: number | string;
  date?: string;
  text?: string;
  author?: string;
  status?: string;
  highlight?: boolean;
}

export interface WikiPendingEdit {
  articleId: string;
  revisionId: number | string;
  author?: string;
  sourceLabel?: string;
  submittedAt?: string;
  newHeading?: string;
  newText?: string;
}

/** GET /wiki/{id} — article detail (fixture-rich; live maps best-effort). */
export interface WikiArticleDetail {
  articleId: string;
  group?: string;
  title?: string;
  readTime?: string;
  updated?: string;
  lead?: string;
  body?: WikiBodyBlock[];
  related?: WikiRelatedLink[];
  revisions?: WikiRevision[];
  pending?: WikiPendingEdit | null;
  justUpdated?: boolean;
}

/** GET /reports/events row (con.weekly_report_event). */
export interface ReportEvent {
  eventId?: number;
  docketId?: string;
  section?: string;
  sectionHeading?: string;
  reportDate?: string;
  description?: string;
  facility?: string;
  [key: string]: unknown;
}

/**
 * A normalized result card for the Results view — the superset of what the
 * design comp renders per hit and what /search + /matters can supply.
 */
export interface ResultCard {
  rank: number;
  score: string;
  caseId: string | null;
  docketId: string | null;
  dktType: string;
  dktNum: string;
  docType: string;
  title: string;
  cite: string;
  court: string;
  date: string;
  outcome: string;
  outcomeColor: string;
  flagGlyph: string;
  flagBg: string;
  flagColor: string;
  flagBorder: string;
  flagTitle: string;
  snippet: Seg[];
  keys: { num: string; label: string; id: string }[];
  citedBy: number;
  length: string;
  /** facet dimensions used for client-side filtering */
  fSource?: string;
  fForum?: string;
  fService?: string;
  fOutcome?: string;
  fYear?: string;
  fTopic?: string;
  searchText?: string;
}
