/*
 * RESULTS (/results?q=…&scope=…) — faceted results list. Facet sidebar,
 * list/snippet toggle, sort menu, active-filter chips, result cards with
 * treatment flag, key-number chips, and Docket View / Cited by cross-links.
 * Structure from the comp's <!-- RESULTS --> section.
 *
 * Fixture mode searches the bundled corpus exactly like the comp; live mode
 * folds GET /search + /matters hits into the same card shape.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { useToast } from '../components/Toast';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';
import { FACET_DEFS, fixtureSearch, SCOPE_DEFS } from '../lib/fixtures';
import { recordRecentSearch } from '../lib/recentSearches';
import { renderSegs } from '../lib/segments';
import type { ResultCard } from '../lib/types';

/** Explicit tri-state for the live /search fetch — never conflate "loading"
 * or "errored" with "no live data", which used to silently fall back to
 * bundled fixture content in production. */
type LiveSearchState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; cards: ResultCard[] };

const SORT_LABELS: Record<string, string> = {
  relevance: 'Relevance',
  'date-desc': 'Date (newest)',
  'date-asc': 'Date (oldest)',
  court: 'Court level',
};

const COURT_ORDER: Record<string, number> = {
  'Ga. Ct. App.': 1,
  'Ga. Sup. Ct.': 2,
  'Superior Court': 3,
  OSAH: 4,
  'DCH Commissioner': 5,
  'DCH Planning': 6,
};

/** Fold a live /search response into result cards (best-effort mapping). */
function liveHitsToCards(hits: import('../lib/types').SearchHit[]): ResultCard[] {
  return hits.map((h, i) => {
    const r = h.record as Record<string, string | number | null>;
    const docketId = String(r.docket_id ?? r.docketId ?? '');
    return {
      rank: i + 1,
      score: h.rank != null ? String(h.rank) : '—',
      caseId: r.entry_id != null ? String(r.entry_id) : null,
      docketId: docketId || null,
      dktType: String(r.docket_family ?? 'CON'),
      dktNum: docketId,
      docType: h.type === 'matter' ? 'Matter' : h.type === 'document' ? 'Document' : 'Event',
      title: String(r.title ?? r.applicant ?? r.facility ?? r.description ?? docketId),
      cite: String(r.doc_type ?? r.matter_type ?? ''),
      court: String(r.court ?? r.county ?? ''),
      date: String(r.doc_date ?? r.final_decision_date ?? r.event_date ?? ''),
      outcome: String(r.final_outcome ?? ''),
      outcomeColor: 'var(--text2)',
      flagGlyph: '●',
      flagBg: 'var(--surface2)',
      flagColor: 'var(--text2)',
      flagBorder: 'var(--border2)',
      flagTitle: '',
      snippet: [String(r.project_description ?? r.description ?? '')],
      keys: [],
      citedBy: 0,
      length: '',
    };
  });
}

export default function Results() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const q = searchParams.get('q') ?? '';
  const scope = searchParams.get('scope') ?? 'all';

  // Facet preselection from the advanced builder (?f=dim|val,dim|val…).
  const [facetSel, setFacetSel] = useState<Record<string, boolean>>(() => {
    const out: Record<string, boolean> = {};
    for (const pair of (searchParams.get('f') ?? '').split(',')) {
      if (pair.includes('|')) out[pair] = true;
    }
    return out;
  });
  const [snippetView, setSnippetView] = useState(false);
  const [sortBy, setSortBy] = useState('relevance');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [liveState, setLiveState] = useState<LiveSearchState>({ status: 'loading' });
  const [retryTick, setRetryTick] = useState(0);
  const sortRef = useRef<HTMLDivElement>(null);

  // Live-API search (fixture mode computes synchronously below). USE_FIXTURES
  // is the only reason to skip the live fetch — never treat "still loading"
  // or "the fetch failed" as "show fixtures instead".
  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    setLiveState({ status: 'loading' });
    api
      .search(q || '*', scope === 'all' ? 'all' : 'matters')
      .then((res) => alive && setLiveState({ status: 'ok', cards: liveHitsToCards(res.hits) }))
      .catch((err: Error) => alive && setLiveState({ status: 'error', message: err.message }));
    return () => {
      alive = false;
    };
  }, [q, scope, retryTick]);

  // Record every query the user actually runs (genuine client-side search
  // history — see lib/recentSearches.ts), regardless of fixtures/live mode.
  useEffect(() => {
    if (q.trim()) recordRecentSearch(q, scope);
  }, [q, scope]);

  const retryLiveSearch = () => setRetryTick((t) => t + 1);

  const { cards, queryDisplay } = useMemo(() => {
    if (api.USE_FIXTURES) return fixtureSearch(q, scope, facetSel);
    if (liveState.status === 'ok') {
      return { cards: liveState.cards, queryDisplay: q || 'All CON Sources' };
    }
    return { cards: [] as ResultCard[], queryDisplay: q || 'All CON Sources' };
  }, [q, scope, facetSel, liveState]);

  const sorted = useMemo(() => {
    const list = [...cards];
    if (sortBy === 'date-desc') list.sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
    else if (sortBy === 'date-asc') list.sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
    else if (sortBy === 'court') list.sort((a, b) => (COURT_ORDER[a.court] ?? 9) - (COURT_ORDER[b.court] ?? 9));
    return list.map((c, i) => ({ ...c, rank: i + 1 }));
  }, [cards, sortBy]);

  const activeFilters = useMemo(() => {
    const out: { key: string; category: string; value: string }[] = [];
    for (const g of FACET_DEFS) {
      for (const item of g.items) {
        const key = `${g.dim}|${item.val}`;
        if (facetSel[key]) out.push({ key, category: g.title, value: item.label });
      }
    }
    return out;
  }, [facetSel]);

  const toggleFacet = (key: string) => setFacetSel((s) => ({ ...s, [key]: !s[key] }));
  const scopeLabel = (SCOPE_DEFS[scope] ?? SCOPE_DEFS.all).label;

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
      {/* Results header */}
      <div style={{ padding: '18px 32px 14px', background: 'var(--surface)', borderBottom: '1px solid var(--surface2)' }}>
        <div className="breadcrumb">
          <span className="crumb-current">{scopeLabel}</span>
          <span className="crumb-sep">›</span>
          <span className="crumb-current">Results</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
          <div>
            <h1 className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}>
              <span style={{ color: 'var(--text2)', fontWeight: 400 }}>Results for</span> &ldquo;{queryDisplay}&rdquo;
            </h1>
            <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 6, display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
              <span>
                {!api.USE_FIXTURES && liveState.status === 'loading' ? (
                  <em style={{ color: 'var(--text3)' }}>searching…</em>
                ) : (
                  <>
                    <strong style={{ color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{sorted.length}</strong>{' '}
                    {sorted.length === 1 ? 'document' : 'documents'}
                  </>
                )}
              </span>
              <span style={{ color: 'var(--border2)' }}>|</span>
              <span>
                Searched: <em>Determinations, Briefs, Statutes, Rules</em>
              </span>
              <span style={{ color: 'var(--border2)' }}>|</span>
              <Link to="/" className="text-link">
                Edit search
              </Link>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
              <span style={{ color: 'var(--text3)' }}>Sort:</span>
              <div style={{ position: 'relative' }} ref={sortRef}>
                <button
                  className="btn-outline"
                  style={{ padding: '6px 10px', fontWeight: 500, color: 'var(--text)' }}
                  onClick={() => setShowSortMenu((v) => !v)}
                >
                  {SORT_LABELS[sortBy]}
                  <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden>
                    <path d="M2 4 L5 7 L8 4" stroke="currentColor" strokeWidth={1.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {showSortMenu && (
                  <>
                    <button className="menu-overlay" tabIndex={-1} onClick={() => setShowSortMenu(false)} aria-label="Close sort menu" />
                    <div
                      style={{
                        position: 'absolute',
                        top: 'calc(100% + 4px)',
                        left: 0,
                        background: 'var(--surface)',
                        border: '1px solid var(--border2)',
                        borderRadius: 2,
                        boxShadow: '0 4px 16px rgba(0,0,0,.3)',
                        zIndex: 1000,
                        minWidth: 180,
                        padding: '4px 0',
                      }}
                    >
                      {Object.entries(SORT_LABELS).map(([id, label]) => (
                        <button
                          key={id}
                          onClick={() => {
                            setSortBy(id);
                            setShowSortMenu(false);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            width: '100%',
                            textAlign: 'left',
                            padding: '8px 14px',
                            fontSize: 13,
                            color: sortBy === id ? 'var(--accent-text)' : 'var(--text)',
                            fontWeight: sortBy === id ? 600 : 400,
                          }}
                        >
                          {label}
                          {sortBy === id && <span style={{ fontSize: 11 }}>✓</span>}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', border: '1px solid var(--border2)', borderRadius: 2, overflow: 'hidden' }}>
              <button
                title="List view"
                onClick={() => setSnippetView(false)}
                style={{
                  padding: '6px 10px',
                  background: snippetView ? 'var(--surface2)' : 'var(--border2)',
                  color: snippetView ? 'var(--text2)' : 'var(--text)',
                }}
              >
                <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
                  <path d="M2 4 L14 4 M2 8 L14 8 M2 12 L14 12" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
                </svg>
              </button>
              <button
                title="Snippet view"
                onClick={() => setSnippetView(true)}
                style={{
                  padding: '6px 10px',
                  background: snippetView ? 'var(--border2)' : 'var(--surface2)',
                  color: snippetView ? 'var(--text)' : 'var(--text2)',
                  borderLeft: '1px solid var(--border2)',
                }}
              >
                <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
                  <rect x="2" y="3" width="12" height="4" stroke="currentColor" strokeWidth={1.3} fill="none" />
                  <rect x="2" y="9" width="12" height="4" stroke="currentColor" strokeWidth={1.3} fill="none" />
                </svg>
              </button>
            </div>
            <button
              onClick={() => showToast('Search alert created for this query')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '7px 14px',
                background: 'var(--surface)',
                border: '1px solid var(--brand-red)',
                color: 'var(--accent-text)',
                borderRadius: 2,
                fontWeight: 600,
                fontSize: 12,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
                <path
                  d="M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11"
                  stroke="currentColor"
                  strokeWidth={1.4}
                  fill="none"
                  strokeLinejoin="round"
                />
              </svg>
              Create search alert
            </button>
          </div>
        </div>

        {/* Active filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
          <span className="label-upper" style={{ letterSpacing: 1, fontWeight: 600 }}>
            Filters:
          </span>
          {activeFilters.map((f) => (
            <span key={f.key} className="filter-chip">
              <span style={{ color: 'var(--text3)' }}>{f.category}:</span>
              <strong style={{ fontWeight: 600 }}>{f.value}</strong>
              <button
                onClick={() => toggleFacet(f.key)}
                style={{
                  marginLeft: 2,
                  color: 'var(--accent-text)',
                  fontSize: 14,
                  lineHeight: 1,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 14,
                  height: 14,
                }}
              >
                ×
              </button>
            </span>
          ))}
          {activeFilters.length > 0 ? (
            <button
              onClick={() => setFacetSel({})}
              style={{ fontSize: 11, color: 'var(--text2)', textDecoration: 'underline' }}
            >
              Clear all
            </button>
          ) : (
            <span style={{ fontSize: 12, color: 'var(--text3)' }}>None applied</span>
          )}
        </div>
        {!api.USE_FIXTURES && liveState.status === 'error' && (
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--status-denied)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span>Search failed: {liveState.message}</span>
            <button onClick={retryLiveSearch} className="text-link" style={{ fontWeight: 600 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Facets */}
        <aside className="facet-aside">
          {FACET_DEFS.map((g) => (
            <div key={g.dim} className="facet-group">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <h3 style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)', textTransform: 'uppercase', letterSpacing: 1.2, margin: 0 }}>
                  {g.title}
                </h3>
                <span style={{ fontSize: 10, color: 'var(--text3)' }}>▾</span>
              </div>
              {g.items.map((item) => {
                const key = `${g.dim}|${item.val}`;
                const checked = !!facetSel[key];
                return (
                  <div key={key} className={`facet-item${checked ? ' checked' : ''}`} onClick={() => toggleFacet(key)}>
                    <input type="checkbox" checked={checked} readOnly style={{ margin: 0, accentColor: '#8E1B1F', pointerEvents: 'none' }} />
                    <span style={{ flex: 1 }}>{item.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums' }}>{item.count}</span>
                  </div>
                );
              })}
              {g.more && (
                <button className="text-link" style={{ fontSize: 11, marginTop: 6 }}>
                  + Show more
                </button>
              )}
            </div>
          ))}
        </aside>

        {/* Result list */}
        <div style={{ flex: 1, minWidth: 0, padding: '8px 32px 40px' }}>
          {!api.USE_FIXTURES && liveState.status === 'loading' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 14 }} aria-busy="true" aria-label="Loading results">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="card"
                  style={{ padding: '18px 22px 20px', opacity: 0.6 }}
                >
                  <div style={{ height: 12, width: '40%', background: 'var(--surface2)', borderRadius: 2, marginBottom: 10 }} />
                  <div style={{ height: 16, width: '70%', background: 'var(--surface2)', borderRadius: 2, marginBottom: 10 }} />
                  <div style={{ height: 12, width: '90%', background: 'var(--surface2)', borderRadius: 2 }} />
                </div>
              ))}
            </div>
          )}

          {!api.USE_FIXTURES && liveState.status === 'error' && (
            <div className="card" style={{ textAlign: 'center', padding: '60px 20px', marginTop: 14 }}>
              <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
                Search failed
              </div>
              <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 18 }}>{liveState.message}</div>
              <button className="btn-primary" onClick={retryLiveSearch}>
                Retry search
              </button>
            </div>
          )}

          {(api.USE_FIXTURES || liveState.status === 'ok') && sorted.map((c) => (
            <article
              key={c.rank}
              className="result-card"
              style={{ padding: snippetView ? '11px 22px 13px' : '18px 22px 20px', marginTop: snippetView ? 6 : 14 }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                {/* Treatment flag */}
                <div
                  title={c.flagTitle}
                  className="serif"
                  style={{
                    flexShrink: 0,
                    width: 18,
                    height: 18,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: c.flagBg,
                    color: c.flagColor,
                    borderRadius: '50%',
                    fontWeight: 700,
                    fontSize: 11,
                    marginTop: 4,
                    border: `1px solid ${c.flagBorder}`,
                  }}
                >
                  {c.flagGlyph}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Header line */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                      <DktBadge type={c.dktType} size="lg" />
                      <span className="mono" style={{ fontSize: 11, color: 'var(--text)', fontWeight: 500 }}>
                        {c.dktNum}
                      </span>
                      <span style={{ color: 'var(--border2)' }}>|</span>
                      <div className="label-upper">{c.docType}</div>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span>#{c.rank}</span>
                      <span style={{ color: 'var(--border2)' }}>|</span>
                      <span>
                        Relevance <strong style={{ color: 'var(--text)' }}>{c.score}</strong>
                      </span>
                    </div>
                  </div>

                  {/* Title */}
                  <Link to={c.caseId ? `/document/${c.caseId}` : `/docket/${c.docketId}`} style={{ display: 'block', textAlign: 'left', marginTop: 4 }}>
                    <h2
                      className="serif"
                      style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', margin: 0, lineHeight: 1.3, letterSpacing: '-0.2px' }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                    >
                      <em style={{ fontStyle: 'italic' }}>{c.title}</em>
                    </h2>
                  </Link>

                  {/* Citation line */}
                  <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 5, display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
                    <span className="mono" style={{ color: 'var(--text)' }}>{c.cite}</span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span>
                      <strong style={{ color: 'var(--text)' }}>{c.court}</strong>
                    </span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span>{c.date}</span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: c.outcomeColor, fontWeight: 600 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.outcomeColor, display: 'inline-block' }} />
                      {c.outcome}
                    </span>
                  </div>

                  {/* Snippet (hidden in compact/snippet view) */}
                  {!snippetView && (
                    <div className="serif" style={{ marginTop: 11, fontSize: 13.5, lineHeight: 1.6, color: 'var(--text)' }}>
                      {renderSegs(c.snippet)}
                    </div>
                  )}

                  {/* Footer */}
                  {c.keys.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14, flexWrap: 'wrap' }}>
                      <span className="label-upper" style={{ marginRight: 2 }}>
                        Key Numbers:
                      </span>
                      {c.keys.map((k) => (
                        <Link key={k.id} to={`/topics/${k.id}`} className="key-chip">
                          <span className="key-num">{k.num}</span>
                          {k.label}
                        </Link>
                      ))}
                    </div>
                  )}

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 18,
                      marginTop: 12,
                      paddingTop: 12,
                      borderTop: '1px solid var(--surface2)',
                      fontSize: 12,
                    }}
                  >
                    <Link to={`/docket/${c.docketId ?? c.caseId}`} className="text-link" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden>
                        <path d="M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Docket View
                    </Link>
                    <Link
                      to={`/citator/${c.caseId ?? c.docketId}`}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                    >
                      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden>
                        <path d="M3 8 L13 8 M8 3 L13 8 L8 13" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Cited by <strong style={{ color: 'var(--text)' }}>{c.citedBy}</strong>
                    </Link>
                    <button
                      onClick={() => showToast('Alert set on this docket')}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text)' }}
                    >
                      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden>
                        <path
                          d="M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11"
                          stroke="currentColor"
                          strokeWidth={1.4}
                          fill="none"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Set alert
                    </button>
                    <button
                      onClick={() => showToast('Annotation panel coming soon')}
                      style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text)' }}
                    >
                      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden>
                        <path d="M4 3 L4 13 L8 11 L12 13 L12 3 Z" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinejoin="round" />
                      </svg>
                      Annotate
                    </button>
                    <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text3)' }}>{c.length}</div>
                  </div>
                </div>
              </div>
            </article>
          ))}

          {/* Empty state */}
          {(api.USE_FIXTURES || liveState.status === 'ok') && sorted.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '60px 20px', marginTop: 14 }}>
              <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
                {activeFilters.length > 0 ? 'No results match your filters' : 'No results found'}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 18 }}>
                {activeFilters.length > 0
                  ? 'Try removing a filter or broadening your search terms.'
                  : 'Try broadening your search terms, or check back as the database continues to be populated.'}
              </div>
              <button
                className="btn-primary"
                onClick={() => {
                  setFacetSel({});
                  navigate('/results?q=&scope=all');
                }}
              >
                Clear all filters &amp; scope
              </button>
            </div>
          )}

          {/* Pagination */}
          {(api.USE_FIXTURES || liveState.status === 'ok') && sorted.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, margin: '32px 0 16px', fontSize: 12 }}>
              <button style={{ padding: '6px 10px', color: 'var(--text3)' }} disabled>
                ‹ Prev
              </button>
              <button style={{ padding: '6px 11px', background: 'var(--surface)', color: 'var(--text)', borderRadius: 2, fontWeight: 600 }}>1</button>
              <button style={{ padding: '6px 11px', color: 'var(--text)' }}>2</button>
              <button style={{ padding: '6px 11px', color: 'var(--text)' }}>3</button>
              <button style={{ padding: '6px 11px', color: 'var(--text)' }}>…</button>
              <button style={{ padding: '6px 11px', color: 'var(--text)' }}>242</button>
              <button className="text-link" style={{ padding: '6px 10px' }}>
                Next ›
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
