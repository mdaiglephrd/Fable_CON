/*
 * HOME — hero search, quick actions, docket-type shortcuts, recent activity +
 * what's new. Structure/copy from the comp's <!-- HOME --> section.
 */
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { DktBadge } from '../components/DktBadge';
import {
  DOCKET_TYPE_TILES,
  RECENT_ITEMS,
  SAMPLE_QUERIES,
  SCOPE_DEFS,
  WHATS_NEW,
} from '../lib/fixtures';

function QuickIcon({ d }: { d: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const QUICK_ACTIONS = [
  {
    title: 'Browse Topics & Key Numbers',
    desc: 'CON-specific taxonomy — drill from major topics into key numbers and headnoted cases.',
    count: '6 topics · 142 keys',
    icon: 'M3 3 L13 3 M3 6 L13 6 M3 9 L9 9 M3 12 L11 12',
    to: '/topics/iii',
  },
  {
    title: 'Statutes & Rules Reader',
    desc: 'O.C.G.A. Title 31, Chapter 6 and Ga. Comp. R. & Regs. 111-2-2, annotated with citing cases.',
    count: 'Updated Jun 14, 2026',
    icon: 'M4 2 L4 14 M4 5 L12 5 L13 7 L12 9 L4 9',
    to: '/statute/31-6-43',
  },
  {
    title: 'Docket View',
    desc: 'See a CON proceeding from Letter of Intent through judicial review — at a glance.',
    count: 'Featured: Riverstone',
    icon: 'M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5',
    to: '/docket/riverstone-imaging',
  },
  {
    title: 'Trace™ Citator',
    desc: 'Negative-treatment alerts, citing decisions, and depth-of-treatment indicators.',
    count: '3 negative alerts',
    icon: 'M3 8 L13 8 M8 3 L13 8 L8 13',
    to: '/citator/riverstone-imaging',
  },
];

export default function Home() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('all');

  const runSearch = (e?: FormEvent, preset?: string) => {
    e?.preventDefault();
    const q = preset ?? query;
    navigate(`/results?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`);
  };

  return (
    <section style={{ padding: 0 }}>
      {/* Hero */}
      <div
        style={{
          background: 'linear-gradient(180deg,var(--page-bg) 0%,var(--surface) 100%)',
          borderBottom: '1px solid var(--surface2)',
          padding: '56px 64px 48px',
        }}
      >
        <div style={{ maxWidth: 980 }}>
          <div
            style={{
              fontSize: 11,
              letterSpacing: 2,
              color: 'var(--accent-text)',
              fontWeight: 600,
              textTransform: 'uppercase',
              marginBottom: 16,
            }}
          >
            Certificate of Need · State of Georgia
          </div>
          <h1
            className="serif"
            style={{ fontSize: 40, fontWeight: 600, color: 'var(--text)', margin: '0 0 14px', lineHeight: 1.15, letterSpacing: '-0.6px' }}
          >
            Authoritative research for Georgia
            <br />
            CON determinations and appeals.
          </h1>
          <p style={{ fontSize: 15, color: 'var(--text2)', maxWidth: 640, margin: '0 0 32px', lineHeight: 1.55 }}>
            All published agency determinations, hearing officer initial decisions, Commissioner final orders,
            and judicial review opinions under O.C.G.A. § 31-6-1 <em>et&nbsp;seq.</em> and
            Ga.&nbsp;Comp.&nbsp;R.&nbsp;&amp;&nbsp;Regs.&nbsp;111-2-2 — annotated, key-numbered, and citator-flagged.
          </p>

          {/* Hero search */}
          <form
            onSubmit={runSearch}
            style={{
              display: 'flex',
              background: 'var(--surface)',
              border: '1px solid var(--border2)',
              borderRadius: 2,
              boxShadow: '0 2px 8px rgba(20,20,20,.06)',
              overflow: 'hidden',
              maxWidth: 820,
            }}
          >
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              aria-label="Search scope"
              style={{
                border: 'none',
                borderRight: '1px solid var(--surface2)',
                fontSize: 13,
                background: 'var(--page-bg)',
                color: 'var(--text)',
                fontWeight: 500,
                padding: '0 14px',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {Object.entries(SCOPE_DEFS).map(([id, def]) => (
                <option key={id} value={id}>
                  {def.label}
                </option>
              ))}
            </select>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='Try: "MRI need methodology", or 31-6-44(c), or Riverstone Imaging'
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                padding: '18px 20px',
                fontSize: 15,
                background: 'var(--surface)',
                color: 'var(--text)',
              }}
            />
            <button type="submit" className="btn-search" style={{ padding: '0 28px', fontSize: 14, gap: 8 }}>
              <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
                <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.8} fill="none" />
                <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
              </svg>
              Search
            </button>
          </form>
          <div style={{ display: 'flex', gap: 18, marginTop: 14, fontSize: 12, color: 'var(--text2)', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1.2, fontSize: 10, fontWeight: 600 }}>
              Try
            </span>
            {SAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => runSearch(undefined, q)}
                style={{ color: 'var(--accent-text)', fontSize: 12, borderBottom: '1px solid transparent' }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--brand-red)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'transparent')}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div style={{ padding: '36px 64px 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, maxWidth: 1280 }}>
          {QUICK_ACTIONS.map((a) => (
            <button
              key={a.title}
              onClick={() => navigate(a.to)}
              className="card"
              style={{
                textAlign: 'left',
                padding: '20px 20px 22px',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                minHeight: 152,
                transition: 'border-color .15s, box-shadow .15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--brand-red)';
                e.currentTarget.style.boxShadow = '0 2px 12px rgba(142,27,31,.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--surface2)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div
                  style={{
                    width: 34,
                    height: 34,
                    background: 'rgba(244,63,94,0.14)',
                    color: 'var(--accent-text)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: 2,
                  }}
                >
                  <QuickIcon d={a.icon} />
                </div>
                <span style={{ fontSize: 11, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums' }}>{a.count}</span>
              </div>
              <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', lineHeight: 1.25 }}>
                {a.title}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.45 }}>{a.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Browse by docket type */}
      <div style={{ padding: '18px 64px 8px', maxWidth: 1280 }}>
        <div className="section-head">
          <h2 className="section-title">Browse by docket type</h2>
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>Sourced from the DCH Planning Section project lists</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 }}>
          {DOCKET_TYPE_TILES.map((t) => (
            <button
              key={t.type}
              onClick={() => navigate(`/results?q=${encodeURIComponent(`docket-type:${t.type}`)}&scope=all`)}
              style={{
                textAlign: 'left',
                background: 'var(--surface)',
                border: '1px solid var(--surface2)',
                borderTop: `3px solid ${t.fill}`,
                borderRadius: '0 0 2px 2px',
                padding: '13px 14px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                minHeight: 120,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(20,20,20,.06)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
            >
              <span
                className="mono"
                style={{
                  display: 'inline-flex',
                  alignSelf: 'flex-start',
                  padding: '3px 8px',
                  background: t.fill,
                  color: '#FFFFFF',
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: 0.4,
                  borderRadius: 1,
                }}
              >
                {t.label}
              </span>
              <div className="serif" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
                {t.full}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 'auto' }}>
                <span className="mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
                  {t.count}
                </span>
                <span style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 0.8 }}>dockets</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Two-col: Recent + What's New */}
      <div style={{ padding: '8px 64px 56px', display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 32, maxWidth: 1280, marginTop: 16 }}>
        {/* Recent activity */}
        <div>
          <div className="section-head">
            <h2 className="section-title">Recent research</h2>
            <Link
              to="/history"
              style={{ fontSize: 11, color: 'var(--accent-text)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}
            >
              View all →
            </Link>
          </div>
          <div className="card">
            {RECENT_ITEMS.map((r, i) => (
              <div
                key={i}
                className="row-hover"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  padding: '14px 18px',
                  borderBottom: '1px solid var(--surface2)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: r.flagColor, marginTop: 7, flexShrink: 0 }} />
                <div style={{ flexShrink: 0, paddingTop: 1 }}>
                  {r.badgeType ? (
                    <DktBadge type={r.badgeType} />
                  ) : (
                    <span
                      className="mono"
                      title="Appellate opinion"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '2px 7px',
                        background: 'var(--surface2)',
                        color: 'var(--text)',
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: 0.4,
                        borderRadius: 1,
                      }}
                    >
                      OPINION
                    </span>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Link
                    to={`/document/${r.caseId}`}
                    className="serif"
                    style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', textAlign: 'left', lineHeight: 1.3, display: 'block' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = 'var(--accent-text)';
                      e.currentTarget.style.textDecoration = 'underline';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = 'var(--text)';
                      e.currentTarget.style.textDecoration = 'none';
                    }}
                  >
                    {r.title}
                  </Link>
                  <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 3, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="mono" style={{ color: 'var(--text)' }}>{r.cite}</span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span>{r.court}</span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span>{r.date}</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, flexShrink: 0, paddingTop: 2 }}>
                  {r.action}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* What's New */}
        <div>
          <div className="section-head">
            <h2 className="section-title">What's new</h2>
            <span style={{ fontSize: 11, color: 'var(--text3)' }}>Updated daily · 4:30 AM ET</span>
          </div>
          <div className="card" style={{ padding: '4px 0' }}>
            {WHATS_NEW.map((n, i) => (
              <div key={i} className="row-hover" style={{ padding: '13px 18px', borderBottom: '1px solid var(--surface2)', cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 700,
                      letterSpacing: 1.2,
                      textTransform: 'uppercase',
                      color: n.tagColor,
                      background: n.tagBg,
                      padding: '2px 6px',
                      borderRadius: 1,
                    }}
                  >
                    {n.tag}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text3)' }}>{n.date}</span>
                </div>
                <div className="serif" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', lineHeight: 1.35 }}>
                  {n.lead &&
                    (n.em ? <em style={{ fontStyle: 'italic' }}>{n.lead}</em> : <strong>{n.lead}</strong>)}
                  {n.title}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
