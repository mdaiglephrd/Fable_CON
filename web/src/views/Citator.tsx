/*
 * CITATOR (/citator/:entryId) — the Trace™ how-cited report. Treatment flag
 * summary, tabs (Citing Decisions / Docket View / Table of Authorities),
 * citing-case cards with treatment pill + depth bars, direct-history mini and
 * table of authorities sidebar. Structure from the comp's <!-- CITATOR -->.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';
import { flatText, renderSegs } from '../lib/segments';
import type { CaseReader, CitatorReport, ToaItem } from '../lib/types';

type CitatorTab = 'citing' | 'history' | 'toa';

// Treatment-level styling (comp's _tBorder/_tBg maps; caution text uses the
// gold token for legibility on the gold tint).
const T_BORDER: Record<string, string> = { positive: '#B7D6BE', negative: '#E5C0C0', caution: '#E5C97A', neutral: 'var(--border2)' };
const T_BG: Record<string, string> = {
  positive: 'rgba(16,185,129,0.14)',
  negative: 'rgba(244,63,94,0.14)',
  caution: 'rgba(245,158,11,0.14)',
  neutral: 'var(--surface2)',
};
const T_COLOR: Record<string, string> = { positive: '#10B981', negative: '#8E1B1F', caution: '#F59E0B', neutral: 'var(--text2)' };
const DEPTH_WORD = ['', 'Cited', 'Discussed', 'Analyzed', 'Examined in depth'];

// Flag-summary colors by label (fixture colors include near-black for Citing;
// resolve to tokens so both themes stay legible).
const FLAG_COLOR: Record<string, string> = {
  Citing: 'var(--text)',
  Positive: '#10B981',
  Cautionary: '#F59E0B',
  Negative: '#8E1B1F',
};

const OC_COLOR: Record<string, string> = { gray: 'var(--text2)', red: '#8E1B1F', gold: '#F59E0B', green: '#10B981' };
const MARK_COLOR: Record<string, string> = {
  open: 'var(--text3)',
  gray: 'var(--text3)',
  red: '#8E1B1F',
  gold: '#F59E0B',
  goldOpen: '#F59E0B',
  green: '#10B981',
};

function toaLink(a: ToaItem): string {
  if (a.kind === 'stat') return `/statute/${a.target}`;
  if (a.target != null) return `/document/${a.target}`;
  return '#';
}

export default function Citator() {
  const { entryId = '' } = useParams();
  const [report, setReport] = useState<CitatorReport | null>(null);
  const [doc, setDoc] = useState<CaseReader | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<CitatorTab>('citing');

  useEffect(() => {
    let alive = true;
    setReport(null);
    setDoc(null);
    setError(null);
    setTab('citing');
    api
      .getCitator(entryId)
      .then((r) => alive && setReport(r))
      .catch((e: Error) => alive && setError(e.message));
    api
      .getCase(entryId)
      .then((d) => alive && setDoc(d))
      .catch(() => alive && setDoc(null));
    return () => {
      alive = false;
    };
  }, [entryId]);

  if (error) {
    return (
      <div style={{ padding: '80px 32px', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
        Citator report unavailable — {error}
      </div>
    );
  }
  if (!report) {
    return <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading citator…</div>;
  }

  const shortName = doc ? flatText(doc.captionParts) : String(entryId);
  const citeLine = (doc?.citations ?? []).join(' · ');
  const subLine = doc?.tribunalLine ?? (doc?.decided ? `Decided ${doc.decided}` : '');
  const history = (doc?.flow ?? []).map((st) => ({
    stage: st.court ?? '',
    title: st.title ?? '',
    outcome: `${st.outcome ?? ''} — ${st.date ?? ''}`,
    outcomeColor: OC_COLOR[st.oc ?? 'gray'] ?? 'var(--text2)',
    dotColor: MARK_COLOR[st.marker ?? 'gray'] ?? 'var(--text3)',
  }));
  const docketTarget = doc?.docketId ?? String(entryId);

  const tabs: { id: CitatorTab; label: string }[] = [
    { id: 'citing', label: `Citing Decisions (${report.citingCases.length})` },
    { id: 'history', label: 'Docket View' },
    { id: 'toa', label: 'Table of Authorities' },
  ];
  const activeTabLabel =
    tab === 'citing' ? `Cases citing ${shortName}` : tab === 'history' ? 'Docket View' : 'Table of Authorities';

  return (
    <section style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="view-header">
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: shortName, to: `/document/${entryId}` },
            { label: 'Trace™ Citator' },
          ]}
        />
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <DktBadge type={doc?.badge ?? 'CON'} size="lg" />
              <span className="label-upper" style={{ letterSpacing: 1.4 }}>
                Trace™ Citator
              </span>
            </div>
            <h1 className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
              {doc ? renderSegs(doc.captionParts) : shortName}
            </h1>
            <div style={{ fontSize: 12.5, color: 'var(--text2)', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <span className="mono" style={{ color: 'var(--text)' }}>{citeLine}</span>
              {subLine && (
                <>
                  <span style={{ color: 'var(--border2)' }}>|</span>
                  <span>{subLine}</span>
                </>
              )}
            </div>
          </div>
          {/* Treatment flag summary */}
          <div
            style={{
              display: 'flex',
              alignItems: 'stretch',
              background: 'var(--page-bg)',
              border: '1px solid var(--surface2)',
              borderRadius: 2,
              padding: '14px 20px',
              gap: 24,
            }}
          >
            {report.flags.map((f) => (
              <div key={f.label} style={{ textAlign: 'center', minWidth: 52 }}>
                <div className="serif" style={{ fontSize: 28, fontWeight: 600, color: FLAG_COLOR[f.label] ?? f.color ?? 'var(--text)', lineHeight: 1 }}>
                  {f.count}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600, marginTop: 4 }}>
                  {f.label}
                </div>
              </div>
            ))}
          </div>
        </div>
        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, marginTop: 18 }}>
          {tabs.map((t) => (
            <button key={t.id} className={`citator-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 300px', background: 'var(--page-bg)' }}>
        <div style={{ padding: '24px 32px 60px' }}>
          {/* Active-tab heading */}
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
              {activeTabLabel}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
              <span style={{ color: 'var(--text3)' }}>Sort:</span>
              <button className="btn-outline" style={{ padding: '5px 9px', fontSize: 11 }}>
                Date (newest) ▾
              </button>
            </div>
          </div>

          {/* Citing decisions */}
          {tab === 'citing' && (
            <>
              {report.citingCases.map((c, i) => {
                const level = String(c.level ?? 'neutral');
                const color = T_COLOR[level] ?? 'var(--text2)';
                return (
                  <div
                    key={i}
                    className="card"
                    style={{ borderLeft: `4px solid ${T_BORDER[level] ?? 'var(--border2)'}`, padding: '16px 20px', marginBottom: 12 }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <DktBadge type={c.badge ?? 'CON'} size="lg" />
                          <span style={{ fontSize: 10.5, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600 }}>
                            {c.dktNum}
                          </span>
                        </div>
                        {c.target ? (
                          <Link to={`/document/${c.target}`} style={{ textAlign: 'left', display: 'block' }}>
                            <div
                              className="serif"
                              style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, letterSpacing: '-0.1px' }}
                              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                            >
                              <em>{c.title}</em>
                            </div>
                          </Link>
                        ) : (
                          <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
                            <em>{c.title}</em>
                          </div>
                        )}
                        <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 4, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                          <span className="mono" style={{ color: 'var(--text)' }}>{c.cite}</span>
                        </div>
                        <p className="serif" style={{ margin: '9px 0 0', fontSize: 13, lineHeight: 1.55, color: 'var(--text2)' }}>{c.snippet}</p>
                      </div>
                      <div style={{ flexShrink: 0, textAlign: 'right', minWidth: 120 }}>
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '5px 10px',
                            background: T_BG[level] ?? 'var(--surface2)',
                            color: color,
                            fontSize: 11,
                            fontWeight: 700,
                            borderRadius: 2,
                            textTransform: 'uppercase',
                            letterSpacing: 0.4,
                          }}
                        >
                          <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: color }} />
                          {c.treat}
                        </div>
                        <div style={{ fontSize: 10.5, color: 'var(--text3)', marginTop: 6 }}>{DEPTH_WORD[c.depth ?? 1] ?? 'Cited'}</div>
                        <div style={{ marginTop: 8 }}>
                          <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 3, textTransform: 'uppercase', letterSpacing: 0.8 }}>Depth</div>
                          <div style={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                            {Array.from({ length: 4 }, (_, b) => (
                              <div key={b} style={{ width: 14, height: 6, borderRadius: 1, background: b < (c.depth ?? 1) ? color : 'var(--surface2)' }} />
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                    {(c.keys?.length ?? 0) > 0 && (
                      <div style={{ display: 'flex', gap: 12, marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--surface2)', fontSize: 11.5 }}>
                        {c.keys!.map(([num, keyId]) => (
                          <Link key={keyId} to={`/topics/${keyId}`} className="key-chip" style={{ padding: '2px 7px' }}>
                            <span className="key-num" style={{ fontSize: 10.5 }}>
                              {num}
                            </span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {report.citingCases.length === 0 && (
                <div className="card" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
                  No citing decisions of record.
                </div>
              )}
            </>
          )}

          {/* Direct history (full) */}
          {tab === 'history' && (
            <div className="card" style={{ padding: '24px 28px' }}>
              {history.map((h, i) => (
                <div key={i} style={{ display: 'flex', gap: 16, alignItems: 'flex-start', padding: '14px 0', borderBottom: '1px solid var(--surface2)' }}>
                  <div
                    style={{
                      flexShrink: 0,
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: h.dotColor,
                      border: '2px solid var(--surface)',
                      boxShadow: `0 0 0 1.5px ${h.dotColor}`,
                      marginTop: 5,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600, marginBottom: 3 }}>
                      {h.stage}
                    </div>
                    <Link to={`/docket/${docketTarget}`} className="serif" style={{ textAlign: 'left', fontSize: 15, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, display: 'block' }}>
                      {h.title}
                    </Link>
                  </div>
                  <div style={{ flexShrink: 0, fontSize: 12.5, color: h.outcomeColor, fontWeight: 600, textAlign: 'right' }}>{h.outcome}</div>
                </div>
              ))}
              {history.length === 0 && <div style={{ color: 'var(--text3)', fontSize: 13 }}>No direct history loaded.</div>}
              <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text2)' }}>
                Open the full{' '}
                <Link to={`/docket/${docketTarget}`} className="text-link" style={{ fontWeight: 600 }}>
                  Docket View flowchart →
                </Link>{' '}
                for filings and stage detail.
              </div>
            </div>
          )}

          {/* Table of authorities (full) */}
          {tab === 'toa' && (
            <div className="card" style={{ padding: '8px 0' }}>
              {report.tableOfAuthorities.map((a, i) => (
                <div key={i} style={{ padding: '14px 24px', borderBottom: '1px solid var(--surface2)' }}>
                  <Link to={toaLink(a)} className="serif" style={{ textAlign: 'left', fontSize: 15, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, display: 'block' }}>
                    <em>{a.title}</em>
                  </Link>
                  <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 3, display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span className="mono" style={{ color: 'var(--text)' }}>{a.cite}</span>
                    <span style={{ color: 'var(--border2)' }}>|</span>
                    <span>Cited at {a.pinpoint}</span>
                  </div>
                </div>
              ))}
              {report.tableOfAuthorities.length === 0 && (
                <div style={{ padding: '24px', color: 'var(--text3)', fontSize: 13 }}>No authorities table of record.</div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar: direct history mini + table of authorities */}
        <aside style={{ background: 'var(--surface)', borderLeft: '1px solid var(--surface2)', padding: '24px 22px 60px', fontSize: 13 }}>
          <h3 className="doc-aside-h">Docket View</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0, position: 'relative', marginBottom: 24 }}>
            {history.map((h, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '9px 0', borderBottom: '1px solid var(--surface2)' }}>
                <div
                  style={{
                    flexShrink: 0,
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: h.dotColor,
                    border: '2px solid var(--surface)',
                    boxShadow: `0 0 0 1.5px ${h.dotColor}`,
                    marginTop: 4,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 0.8, fontWeight: 600, marginBottom: 2 }}>
                    {h.stage}
                  </div>
                  <Link to={`/docket/${docketTarget}`} className="serif" style={{ textAlign: 'left', fontSize: 12.5, fontWeight: 500, color: 'var(--text)', lineHeight: 1.3 }}>
                    {h.title}
                  </Link>
                  <div style={{ fontSize: 11, color: h.outcomeColor, fontWeight: 600, marginTop: 2 }}>{h.outcome}</div>
                </div>
              </div>
            ))}
            {history.length === 0 && <div style={{ color: 'var(--text3)', fontSize: 12 }}>No history loaded.</div>}
          </div>

          <h3 className="doc-aside-h" style={{ paddingTop: 12, borderTop: '1px solid var(--surface2)' }}>
            Table of Authorities
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {report.tableOfAuthorities.map((a, i) => (
              <div key={i} style={{ padding: '9px 0', borderBottom: '1px solid var(--surface2)' }}>
                <Link to={toaLink(a)} className="serif" style={{ textAlign: 'left', fontSize: 12.5, fontWeight: 500, color: 'var(--text)', lineHeight: 1.3, display: 'block' }}>
                  <em>{a.title}</em>
                </Link>
                <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 2, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--text3)' }}>{a.cite}</span>
                  <span style={{ color: 'var(--border2)' }}>|</span>
                  <span style={{ fontSize: 10.5 }}>{a.pinpoint}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
