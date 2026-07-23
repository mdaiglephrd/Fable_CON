/*
 * RESEARCH LANDING (/research) — hero quick search, six entry cards
 * (Quick Search, New Project, Library, History, Citator, Docket View),
 * and the recent / saved searches columns. From the comp's
 * <!-- RESEARCH LANDING --> section.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { SectionHead } from '../components/Shell';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { SCOPE_DEFS } from '../lib/fixtures';
import { getRecentSearches, timeAgo, type RecentSearchEntry } from '../lib/recentSearches';
import type { SavedAlert } from '../lib/types';

const CARDS = [
  {
    to: '/search/new',
    icon: 'M4 3 L4 13 L8 11 L12 13 L12 3 Z',
    accentIcon: true,
    title: 'Quick Search',
    desc: 'Field-by-field advanced query builder with connectors and filters.',
  },
  {
    to: '/projects/new',
    icon: 'M8 3 L8 13 M3 8 L13 8',
    accentIcon: true,
    title: 'New Research Project',
    desc: 'Start a tagged project — mark dockets relevant or irrelevant as you review.',
  },
  {
    to: '/library',
    icon: 'M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4 M5 8 L11 8 M5 11 L9 11',
    accentIcon: false,
    title: 'Research Library',
    desc: 'Saved and open research projects, tagged by topic and key number.',
  },
  {
    to: '/history',
    icon: 'M8 2 A6 6 0 1 0 8.01 2 M8 4 L8 8 L10.5 9.5',
    accentIcon: false,
    title: 'Docket History',
    desc: 'The chronological filing timeline for any docket, filterable by event type.',
  },
  {
    to: '/citator/riverstone-imaging',
    icon: 'M3 8 L13 8 M8 3 L13 8 L8 13',
    accentIcon: true,
    title: 'Trace™ Citator',
    desc: 'Negative-treatment flags, citing decisions, and depth of treatment.',
  },
  {
    to: '/docket/riverstone-imaging',
    icon: 'M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5',
    accentIcon: false,
    title: 'Docket View',
    desc: 'A proceeding from letter of intent through judicial review, at a glance.',
  },
];

/** Explicit tri-state for GET /alerts — loading and error must never be
 * silently rendered as fabricated saved-search entries. */
type AlertsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; alerts: SavedAlert[] };

export default function Research() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [query, setQuery] = useState('');

  // Recent searches: no backend concept exists for this (there is no
  // /recent-searches endpoint) — it's derived from genuine queries the user
  // has actually run, recorded client-side by Results.tsx. See
  // lib/recentSearches.ts. This is a real (if minimal) history mechanism,
  // not fabricated demo data.
  const [recentSearches, setRecentSearches] = useState<RecentSearchEntry[]>([]);
  useEffect(() => {
    setRecentSearches(getRecentSearches());
  }, []);

  // Saved searches: GET /alerts (api.listAlerts) already gates fixture vs
  // live internally — fixture-mode calls return the bundled sample alerts,
  // live mode hits the real API. We only need loading/error/ok here so a
  // slow or failing fetch never gets confused with "no saved searches".
  const [alertsState, setAlertsState] = useState<AlertsState>({ status: 'loading' });
  useEffect(() => {
    let alive = true;
    setAlertsState({ status: 'loading' });
    api
      .listAlerts()
      .then((res) => alive && setAlertsState({ status: 'ok', alerts: res.items }))
      .catch((err: Error) => alive && setAlertsState({ status: 'error', message: err.message }));
    return () => {
      alive = false;
    };
  }, []);

  const run = (q: string, scope = 'all') => navigate(`/results?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run(query);
  };

  return (
    <section>
      <div
        style={{
          background: 'linear-gradient(180deg,var(--page-bg) 0%,var(--surface) 100%)',
          borderBottom: '1px solid var(--surface2)',
          padding: '24px 32px 30px',
        }}
      >
        <Breadcrumb items={[{ label: 'Home', to: '/' }, { label: 'Research' }]} />
        <h1 className="serif" style={{ fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: '0 0 4px', letterSpacing: '-0.4px' }}>Research</h1>
        <div style={{ fontSize: 13.5, color: 'var(--text2)', marginBottom: 18, maxWidth: 720 }}>
          Run a new search, revisit your research history, or trace the treatment and direct history of any decision.
        </div>
        <form
          onSubmit={submit}
          style={{ display: 'flex', background: 'var(--surface)', border: '1px solid var(--border2)', borderRadius: 2, boxShadow: '0 2px 8px rgba(20,20,20,.06)', overflow: 'hidden', maxWidth: 780 }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter terms, citation, case name, or section…"
            style={{ flex: 1, border: 'none', outline: 'none', padding: '15px 18px', fontSize: 15, background: 'var(--surface)', color: 'var(--text)' }}
          />
          <button type="submit" className="btn-search" style={{ padding: '0 26px', fontSize: 14, gap: 8 }}>
            <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.8} fill="none" />
              <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
            </svg>
            Search
          </button>
        </form>
      </div>

      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 1180 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14, marginBottom: 34 }}>
            {CARDS.map((c) => (
              <button
                key={c.title}
                className="hub-card"
                onClick={() => navigate(c.to)}
                style={{ padding: 18, flexDirection: 'column', gap: 9, minHeight: 140, alignItems: 'flex-start' }}
              >
                <div className={`hub-icon${c.accentIcon ? '' : ' neutral'}`} style={{ width: 34, height: 34 }}>
                  <svg width="17" height="17" viewBox="0 0 16 16" aria-hidden>
                    <path d={c.icon} stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>{c.title}</div>
                <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.45 }}>{c.desc}</div>
              </button>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 22 }}>
            <div>
              <SectionHead title="Recent searches" right={<Link to="/history" className="text-link">Docket history →</Link>} />
              <div className="list-card" style={{ overflow: 'hidden' }}>
                {recentSearches.length === 0 ? (
                  <div style={{ padding: '18px 16px', fontSize: 12.5, color: 'var(--text3)' }}>No recent searches yet.</div>
                ) : (
                  recentSearches.map((s) => (
                    <button
                      key={`${s.q}|${s.scope}|${s.at}`}
                      className="list-row row-hover"
                      onClick={() => run(s.q, s.scope)}
                      style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', textAlign: 'left', padding: '12px 16px' }}
                    >
                      <svg width="13" height="13" viewBox="0 0 16 16" style={{ flexShrink: 0, color: 'var(--text3)' }} aria-hidden>
                        <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.6} fill="none" />
                        <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
                      </svg>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13.5, color: 'var(--text)', fontWeight: 500, lineHeight: 1.3 }}>{s.q}</div>
                        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{(SCOPE_DEFS[s.scope] ?? SCOPE_DEFS.all).label}</div>
                      </div>
                      <span style={{ flexShrink: 0, fontSize: 11, color: 'var(--text2)' }}>{timeAgo(s.at)}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
            <div>
              <SectionHead title="Saved searches" />
              <div className="list-card" style={{ overflow: 'hidden' }}>
                {alertsState.status === 'loading' && (
                  <div style={{ padding: '18px 16px', fontSize: 12.5, color: 'var(--text3)' }}>Loading saved searches…</div>
                )}
                {alertsState.status === 'error' && (
                  <div style={{ padding: '18px 16px', fontSize: 12.5, color: 'var(--status-denied)' }}>
                    Saved searches unavailable — {alertsState.message}
                  </div>
                )}
                {alertsState.status === 'ok' && alertsState.alerts.length === 0 && (
                  <div style={{ padding: '18px 16px', fontSize: 12.5, color: 'var(--text3)' }}>No saved searches yet.</div>
                )}
                {alertsState.status === 'ok' &&
                  alertsState.alerts.map((s) => (
                    <div key={s.alertId} className="list-row" style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '12px 16px' }}>
                      <button
                        onClick={() => run(typeof s.query === 'string' ? s.query : (s.name ?? ''))}
                        style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 11, textAlign: 'left' }}
                      >
                        <svg width="13" height="13" viewBox="0 0 16 16" style={{ flexShrink: 0, color: 'var(--accent-text)' }} aria-hidden>
                          <path d="M4 3 L12 3 L12 13 L8 10 L4 13 Z" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinejoin="round" />
                        </svg>
                        <span>
                          <span style={{ display: 'block', fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>{s.name ?? s.alertId}</span>
                          {s.description && (
                            <span style={{ display: 'block', fontSize: 11.5, color: 'var(--text3)', marginTop: 1 }}>{s.description}</span>
                          )}
                        </span>
                      </button>
                      <button
                        onClick={() => showToast(`Search alert active for "${s.name ?? s.alertId}"`)}
                        className="btn-outline"
                        style={{ padding: '4px 9px', fontSize: 10.5 }}
                      >
                        {s.active === false ? 'Off' : 'Alerting'}
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
