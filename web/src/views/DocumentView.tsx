/*
 * DOCUMENT (/document/:entryId) — the case reader. Caption, citations,
 * tribunal line, treatment banner, editorial summary, headnotes, opinion
 * paragraphs (segment format with case/stat/topic cross-links), disposition,
 * briefs/filings tabs, meta + counsel + citing-references sidebar, print.
 * Structure from the comp's <!-- DOCUMENT --> section.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { DktBadge } from '../components/DktBadge';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { flatText, renderSegs } from '../lib/segments';
import type { CaseReader, CitatorReport } from '../lib/types';

type DocTab = 'opinion' | 'headnotes' | 'briefs' | 'filings';

// Treatment banner styling by good-law level (comp's TREAT map).
const TREAT: Record<string, { bg: string; border: string; accent: string; word: string }> = {
  caution: { bg: 'rgba(245,158,11,0.14)', border: '#E5C97A', accent: '#F59E0B', word: '#F59E0B' },
  negative: { bg: 'rgba(244,63,94,0.14)', border: '#E5C0C0', accent: '#8E1B1F', word: 'var(--accent-text)' },
  positive: { bg: 'rgba(16,185,129,0.14)', border: '#B7D6BE', accent: '#10B981', word: '#10B981' },
  neutral: { bg: 'var(--surface2)', border: 'var(--border2)', accent: 'var(--text3)', word: 'var(--text2)' },
};

const TREAT_GLYPH: Record<string, string> = { positive: '✓', negative: '●', caution: '!', neutral: '●' };
const TREAT_COLOR: Record<string, string> = {
  positive: '#10B981',
  negative: '#8E1B1F',
  caution: '#F59E0B',
  neutral: 'var(--text2)',
};

function TabIcon({ d }: { d: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function DocumentView() {
  const { entryId = '' } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [doc, setDoc] = useState<CaseReader | null>(null);
  const [citator, setCitator] = useState<CitatorReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<DocTab>('opinion');

  useEffect(() => {
    let alive = true;
    setDoc(null);
    setError(null);
    setTab('opinion');
    api
      .getCase(entryId)
      .then((d) => alive && setDoc(d))
      .catch((e: Error) => alive && setError(e.message));
    api
      .getCitator(entryId)
      .then((c) => alive && setCitator(c))
      .catch(() => alive && setCitator(null));
    return () => {
      alive = false;
    };
  }, [entryId]);

  if (error) {
    return (
      <div style={{ padding: '80px 32px', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
        Document unavailable — {error}
      </div>
    );
  }
  if (!doc) {
    return <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading document…</div>;
  }

  const shortName = flatText(doc.captionParts) || doc.title || String(entryId);
  const citeYr = (doc.decided ?? '').match(/\d{4}/);
  const citation = `${shortName}, ${doc.citations?.[0] ?? doc.dktNum ?? ''}${citeYr ? ` (${citeYr[0]}).` : '.'}`;
  const treatment = doc.treatment;
  const tc = TREAT[treatment?.level ?? 'neutral'] ?? TREAT.neutral;
  const docketTarget = doc.docketId ?? String(entryId);
  const filings = (doc.chrono ?? []).map((e) => ({
    date: `${e[1]}. ${e[0]}, ${e[2]}`,
    title: e[5],
    who: e[6],
  }));
  const citingTotal = citator?.flags?.[0]?.count ?? doc.citator?.flags?.[0]?.count ?? 0;
  const citingPreview = (citator?.citingCases ?? []).slice(0, 3);

  const copyCite = () => {
    void navigator.clipboard?.writeText(citation);
    showToast('Citation copied to clipboard');
  };

  const tabs: { id: DocTab; label: string; icon: string }[] = [
    { id: 'opinion', label: 'Opinion', icon: 'M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4' },
    { id: 'headnotes', label: 'Headnotes', icon: 'M3 4 L13 4 M3 8 L13 8 M3 12 L11 12' },
    { id: 'briefs', label: 'Briefs', icon: 'M3 3 L11 3 L13 5 L13 14 L3 14 Z M5 8 L11 8 M5 11 L9 11' },
    { id: 'filings', label: 'Filings', icon: 'M3 2 L13 2 L13 14 L3 14 Z M5 5 L11 5 M5 8 L11 8 M5 11 L9 11' },
  ];

  return (
    <section style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Document toolbar */}
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--surface2)', padding: '14px 32px 0' }}>
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: 'Search results', to: '/results?q=&scope=all' },
            { label: shortName },
          ]}
        />

        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 20, paddingBottom: 14 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Treatment banner */}
            {treatment && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  background: tc.bg,
                  border: `1px solid ${tc.border}`,
                  borderLeft: `4px solid ${tc.accent}`,
                  padding: '9px 14px',
                  borderRadius: 2,
                  marginBottom: 14,
                }}
              >
                <div
                  className="serif"
                  style={{
                    width: 20,
                    height: 20,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: tc.accent,
                    color: 'var(--surface)',
                    borderRadius: '50%',
                    fontWeight: 700,
                    fontSize: 13,
                    flexShrink: 0,
                  }}
                >
                  {treatment.glyph ?? TREAT_GLYPH[treatment.level] ?? '●'}
                </div>
                <div style={{ flex: 1, fontSize: 12.5, color: 'var(--text2)' }}>
                  <strong style={{ color: tc.word }}>{treatment.word}</strong>
                  {renderSegs(treatment.text)}
                </div>
                <Link
                  to={`/citator/${entryId}`}
                  style={{
                    fontSize: 11,
                    color: 'var(--accent-text)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    whiteSpace: 'nowrap',
                    border: '1px solid var(--brand-red)',
                    padding: '5px 10px',
                    borderRadius: 2,
                    background: 'var(--surface)',
                  }}
                >
                  View Trace™
                </Link>
              </div>
            )}

            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
              <DktBadge type={doc.badge ?? 'CON'} size="lg" />
              <span className="mono" style={{ fontSize: 11.5, color: 'var(--text)', fontWeight: 500 }}>
                {doc.dktNum ?? doc.docketId}
              </span>
              <span style={{ color: 'var(--border2)' }}>|</span>
              <span className="label-upper" style={{ letterSpacing: 1.4 }}>
                {doc.tribunalLine}
              </span>
            </div>
            <h1
              className="serif"
              style={{ fontSize: 30, fontWeight: 600, color: 'var(--text)', margin: '0 0 8px', lineHeight: 1.18, letterSpacing: '-0.4px' }}
            >
              {renderSegs(doc.captionParts) ?? doc.title}
            </h1>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, fontSize: 13, color: 'var(--text2)', alignItems: 'center' }}>
              {(doc.citations ?? []).map((c, i) => (
                <span key={i} style={{ display: 'inline-flex', gap: 14, alignItems: 'center' }}>
                  {i > 0 && <span style={{ color: 'var(--border2)' }}>|</span>}
                  <span className="mono" style={{ color: 'var(--text)', fontWeight: 500 }}>{c}</span>
                </span>
              ))}
              {doc.docketNo && (
                <>
                  <span style={{ color: 'var(--border2)' }}>|</span>
                  <span>{doc.docketNo}</span>
                </>
              )}
              {doc.decided && (
                <>
                  <span style={{ color: 'var(--border2)' }}>|</span>
                  <span>
                    Decided <strong style={{ color: 'var(--text)' }}>{doc.decided}</strong>
                  </span>
                </>
              )}
              {doc.subsequent && (
                <>
                  <span style={{ color: 'var(--border2)' }}>|</span>
                  <span>{doc.subsequent}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Doc actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2, borderTop: '1px solid var(--surface2)', marginTop: 6 }}>
          {tabs.map((t) => (
            <button key={t.id} className={`doc-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
              <TabIcon d={t.icon} />
              {t.label}
            </button>
          ))}
          <button className="doc-tab" onClick={() => navigate(`/docket/${docketTarget}`)}>
            <TabIcon d="M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5" />
            Docket View
          </button>
          <button className="doc-tab" onClick={() => navigate(`/citator/${entryId}`)}>
            <TabIcon d="M3 8 L13 8 M8 3 L13 8 L8 13" />
            Trace™ Citator
          </button>
          <div style={{ flex: 1 }} />
          <button className="doc-action" onClick={copyCite}>
            <TabIcon d="M5 5 L5 2 L13 2 L13 11 L10 11 M3 5 L11 5 L11 14 L3 14 Z" />
            Copy cite
          </button>
          <button className="doc-action" onClick={() => showToast('Download — available when connected to document store')}>
            <TabIcon d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13" />
            Download
          </button>
          <button className="doc-action" onClick={() => window.print()}>
            <TabIcon d="M4 3 L12 3 L12 6 L4 6 Z M3 6 L13 6 L13 11 L3 11 Z M5 11 L5 14 L11 14 L11 11" />
            Print
          </button>
          <button
            className="btn-primary"
            style={{ margin: '0 4px', padding: '8px 14px', fontSize: 12 }}
            onClick={() => showToast('Alert set on this docket')}
          >
            <TabIcon d="M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11" />
            Set alert on this docket
          </button>
        </div>
      </div>

      {/* Two column body */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 0, background: 'var(--page-bg)' }}>
        {/* Document body */}
        <article className="doc-article">
          {/* Syllabus / editorial summary */}
          {tab === 'opinion' && doc.editorial && (
            <div style={{ background: 'var(--page-bg)', borderLeft: '3px solid var(--brand-red)', padding: '18px 22px', marginBottom: 30 }}>
              <div
                style={{
                  fontSize: 10,
                  letterSpacing: 1.6,
                  color: 'var(--accent-text)',
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  marginBottom: 8,
                  fontFamily: 'var(--font-ui)',
                }}
              >
                PHRD Editorial Summary
              </div>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--text2)' }}>{doc.editorial}</p>
            </div>
          )}

          {/* Headnotes */}
          {(tab === 'opinion' || tab === 'headnotes') && (doc.headnotes?.length ?? 0) > 0 && (
            <>
              <h2
                style={{
                  fontSize: 13,
                  letterSpacing: 1.6,
                  textTransform: 'uppercase',
                  color: 'var(--text3)',
                  borderBottom: '1px solid var(--surface2)',
                  paddingBottom: 8,
                  margin: '0 0 18px',
                  fontFamily: 'var(--font-ui)',
                  fontWeight: 700,
                }}
              >
                Headnotes &amp; Key Numbers
              </h2>
              {doc.headnotes!.map((h, i) => (
                <div key={i} style={{ display: 'flex', gap: 18, padding: '14px 0', borderBottom: '1px solid var(--surface2)' }}>
                  <div className="serif" style={{ flexShrink: 0, width: 36, fontSize: 24, fontWeight: 600, color: 'var(--accent-text)', lineHeight: 1 }}>
                    {h.num}
                  </div>
                  <div style={{ flex: 1 }}>
                    <Link
                      to={`/topics/${h.keyId ?? ''}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 11,
                        color: 'var(--text2)',
                        fontFamily: 'var(--font-ui)',
                        marginBottom: 6,
                        fontWeight: 600,
                      }}
                    >
                      <svg width="11" height="11" viewBox="0 0 16 16" aria-hidden>
                        <path d="M3 13 L3 5 L8 2 L13 5 L13 13 L9 13 L9 9 L7 9 L7 13 Z" stroke="currentColor" strokeWidth={1.3} fill="none" strokeLinejoin="round" />
                      </svg>
                      <span className="mono" style={{ color: 'var(--accent-text)' }}>{h.key}</span>
                      <span style={{ color: 'var(--text2)' }}>·</span>
                      <span>{h.topic}</span>
                    </Link>
                    <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--text)' }}>{h.text}</p>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Opinion */}
          {tab === 'opinion' && (
            <div style={{ marginTop: 42 }}>
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: 1.6,
                  color: 'var(--text3)',
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  fontFamily: 'var(--font-ui)',
                  marginBottom: 14,
                }}
              >
                Opinion
              </div>
              <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 24, fontFamily: 'var(--font-ui)' }}>
                <strong style={{ color: 'var(--text)' }}>{(doc.byline ?? '') + ' '}</strong>
                {doc.intro}
              </div>

              {(doc.paragraphs ?? []).map((p, i) => (
                <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 18 }}>
                  <div
                    className="mono"
                    style={{ flexShrink: 0, width: 24, fontSize: 11, color: 'var(--text3)', textAlign: 'right', paddingTop: 4, fontVariantNumeric: 'tabular-nums' }}
                  >
                    ¶{p.num}
                  </div>
                  <div style={{ flex: 1, fontSize: 15, lineHeight: 1.7 }}>{renderSegs(p.segs)}</div>
                </div>
              ))}

              {/* Disposition */}
              {doc.disposition && (
                <div style={{ marginTop: 28, paddingTop: 18, borderTop: '1px solid var(--surface2)' }}>
                  <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7 }}>{renderSegs(doc.disposition)}</p>
                </div>
              )}
            </div>
          )}

          {/* Briefs tab */}
          {tab === 'briefs' && (
            <>
              <h2
                style={{
                  fontSize: 13,
                  letterSpacing: 1.6,
                  textTransform: 'uppercase',
                  color: 'var(--text3)',
                  borderBottom: '1px solid var(--surface2)',
                  paddingBottom: 8,
                  margin: '0 0 4px',
                  fontFamily: 'var(--font-ui)',
                  fontWeight: 700,
                }}
              >
                Briefs on file
              </h2>
              {(doc.briefs ?? []).map((b, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 0', borderBottom: '1px solid var(--surface2)' }}>
                  <div
                    style={{
                      flexShrink: 0,
                      width: 32,
                      height: 32,
                      background: 'rgba(244,63,94,0.14)',
                      color: 'var(--accent-text)',
                      borderRadius: 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <TabIcon d="M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>{b.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 3, fontFamily: 'var(--font-ui)' }}>
                      {b.meta ??
                        [b.filedDate && `Filed ${b.filedDate}`, b.attorney, b.firm, b.pageCount && `${b.pageCount} pp.`]
                          .filter(Boolean)
                          .join(' · ')}
                    </div>
                  </div>
                  <button
                    className="text-link"
                    style={{ flexShrink: 0, fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-ui)' }}
                    onClick={() => showToast('Opening document — available when connected to document store')}
                  >
                    Open PDF →
                  </button>
                </div>
              ))}
              {(doc.briefs?.length ?? 0) === 0 && (
                <div style={{ padding: '24px 0', color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--font-ui)' }}>
                  No briefs of record for this document.
                </div>
              )}
            </>
          )}

          {/* Filings tab */}
          {tab === 'filings' && (
            <>
              <h2
                style={{
                  fontSize: 13,
                  letterSpacing: 1.6,
                  textTransform: 'uppercase',
                  color: 'var(--text3)',
                  borderBottom: '1px solid var(--surface2)',
                  paddingBottom: 8,
                  margin: '0 0 4px',
                  fontFamily: 'var(--font-ui)',
                  fontWeight: 700,
                }}
              >
                Docket filings
              </h2>
              {filings.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 16, padding: '13px 0', borderBottom: '1px solid var(--surface2)', fontFamily: 'var(--font-ui)' }}>
                  <div style={{ flexShrink: 0, width: 96, fontSize: 12, color: 'var(--text3)', fontWeight: 600, paddingTop: 1 }}>{f.date}</div>
                  <div style={{ flex: 1 }}>
                    <div className="serif" style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', lineHeight: 1.35 }}>{f.title}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 2 }}>{f.who}</div>
                  </div>
                </div>
              ))}
              {filings.length === 0 && (
                <div style={{ padding: '24px 0', color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--font-ui)' }}>
                  No filings loaded for this document.
                </div>
              )}
              <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text2)', fontFamily: 'var(--font-ui)' }}>
                For the full proceeding across all tribunals, open the{' '}
                <Link to={`/docket/${docketTarget}`} className="text-link" style={{ fontWeight: 600 }}>
                  Docket View flowchart →
                </Link>
              </div>
            </>
          )}
        </article>

        {/* Sidebar */}
        <aside className="doc-aside">
          {/* Quick links */}
          <div style={{ marginBottom: 24 }}>
            <h3 className="doc-aside-h" style={{ marginBottom: 10 }}>
              Jump to
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {(
                [
                  ['Editorial summary', 'opinion'],
                  [`Headnotes (${doc.headnotes?.length ?? 0})`, 'headnotes'],
                  ['Opinion', 'opinion'],
                  ['Briefs & filings', 'briefs'],
                ] as [string, DocTab][]
              ).map(([label, target], i) => (
                <button
                  key={i}
                  onClick={() => setTab(target)}
                  style={{
                    textAlign: 'left',
                    padding: '5px 8px',
                    color: tab === target && label === 'Opinion' ? 'var(--accent-text)' : 'var(--text)',
                    borderLeft: tab === target && label === 'Opinion' ? '2px solid var(--brand-red)' : '2px solid transparent',
                    background: tab === target && label === 'Opinion' ? 'var(--surface)' : 'transparent',
                    fontWeight: tab === target && label === 'Opinion' ? 500 : 400,
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Docket View pill */}
          <Link
            to={`/docket/${docketTarget}`}
            className="card"
            style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', textAlign: 'left', padding: 14, marginBottom: 18 }}
          >
            <div style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--brand-red)', color: '#FFFFFF', borderRadius: 2 }}>
              <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
                <path d="M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5" stroke="currentColor" strokeWidth={1.6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div style={{ flex: 1, lineHeight: 1.2 }}>
              <div className="serif" style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>
                Docket View
              </div>
              <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 2 }}>
                {(doc.flow?.length ?? 0) > 0
                  ? `${doc.flow!.length} events · ${doc.docketDispositions ?? doc.flow!.length} dispositions`
                  : 'Stage-by-stage proceeding tracker'}
              </div>
            </div>
            <svg width="14" height="14" viewBox="0 0 16 16" style={{ color: 'var(--text3)' }} aria-hidden>
              <path d="M5 3 L11 8 L5 13" stroke="currentColor" strokeWidth={1.6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>

          {/* Metadata */}
          <div className="doc-aside-card">
            <h3 className="doc-aside-h">Case Information</h3>
            <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 12px', fontSize: 12.5 }}>
              {Object.entries(doc.meta ?? {}).map(([k, v]) => (
                <span key={k} style={{ display: 'contents' }}>
                  <dt style={{ color: 'var(--text3)' }}>{k}</dt>
                  <dd style={{ margin: 0, color: 'var(--text)' }}>{v}</dd>
                </span>
              ))}
            </dl>
          </div>

          {/* Counsel */}
          <div className="doc-aside-card">
            <h3 className="doc-aside-h">Counsel</h3>
            <div style={{ fontSize: 12.5, lineHeight: 1.55 }}>
              {(doc.counsel ?? []).map((c, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <strong style={{ color: 'var(--text)' }}>{c.role}:</strong>
                  <br />
                  {c.name}
                  {c.firm ? ', ' : ''}
                  {c.firm && <em style={{ fontStyle: 'italic' }}>{c.firm}</em>}
                </div>
              ))}
            </div>
          </div>

          {/* Citing references preview */}
          <div className="doc-aside-card">
            <h3 className="doc-aside-h" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Citing References</span>
              <Link to={`/citator/${entryId}`} style={{ fontSize: 10, color: 'var(--accent-text)' }}>
                View all {citingTotal} →
              </Link>
            </h3>
            {citingPreview.map((c, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--surface2)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: TREAT_COLOR[c.level ?? 'neutral'] ?? 'var(--text2)',
                    marginTop: 4,
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#FFFFFF',
                    fontSize: 8,
                    fontWeight: 700,
                  }}
                >
                  {TREAT_GLYPH[c.level ?? 'neutral']}
                </span>
                <div style={{ flex: 1, fontSize: 12, lineHeight: 1.4 }}>
                  {c.target ? (
                    <Link to={`/document/${c.target}`}>
                      <em style={{ fontStyle: 'italic', color: 'var(--text)' }}>{c.title}</em>
                    </Link>
                  ) : (
                    <em style={{ fontStyle: 'italic', color: 'var(--text)' }}>{c.title}</em>
                  )}
                  <br />
                  <span style={{ color: 'var(--text2)', fontSize: 11 }}>
                    {c.cite} · <strong style={{ color: TREAT_COLOR[c.level ?? 'neutral'] }}>{c.treat}</strong>
                  </span>
                </div>
              </div>
            ))}
            {citingPreview.length === 0 && <div style={{ fontSize: 12, color: 'var(--text3)' }}>No citing references of record.</div>}
          </div>
        </aside>
      </div>
    </section>
  );
}
