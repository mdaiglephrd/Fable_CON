/*
 * COMPARE (/compare) — side-by-side comparison of two decisions from the
 * corpus: caption, tribunal, outcome, treatment, stages-mini (docket-engine
 * compact progress), lead headnote, citing references. Layout from the
 * comp's <!-- COMPARE --> section.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { DktBadge } from '../components/DktBadge';
import { CASE_TO_NUM, CASES, fixtureGetProceeding } from '../lib/fixtures';
import { flatText, renderSegs } from '../lib/segments';
import type { CaseReader } from '../lib/types';

const OUTCOME_COLOR: Record<string, string> = {
  gray: 'var(--text2)',
  red: '#8E1B1F',
  gold: '#F59E0B',
  green: '#10B981',
};

const TREAT_WORD: Record<string, string> = {
  positive: 'Positive',
  negative: 'Negative',
  caution: 'Caution',
  neutral: 'No negative history',
};

const TREAT_COLOR: Record<string, string> = {
  positive: '#10B981',
  negative: '#8E1B1F',
  caution: '#F59E0B',
  neutral: 'var(--text2)',
};

function CompareColumn({ id, onChange, options }: { id: string; onChange: (next: string) => void; options: { id: string; label: string }[] }) {
  const c: CaseReader | undefined = CASES[id];
  const proceeding = useMemo(() => fixtureGetProceeding(CASE_TO_NUM[id] ?? id), [id]);
  if (!c) return null;

  const rev = [...(c.flow ?? [])].reverse();
  const lastDecided = rev.find((st) => !!st.outcome && st.oc != null && st.oc !== 'gray') ?? rev.find((st) => !!st.outcome);
  const outcome = lastDecided?.outcome ?? '—';
  const outcomeColor = OUTCOME_COLOR[lastDecided?.oc ?? 'gray'] ?? 'var(--text2)';
  const level = (c.treatment?.level as string) ?? 'neutral';
  const headnote = c.headnotes?.[0];
  const citing = c.citator?.flags?.[0]?.count ?? 0;

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--surface2)', background: 'var(--page-bg)' }}>
        <select className="field-select" style={{ fontSize: 13, fontWeight: 600, padding: '8px 10px' }} value={id} onChange={(e) => onChange(e.target.value)} aria-label="Choose decision">
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <div style={{ padding: 20 }}>
        <div style={{ marginBottom: 6 }}>
          <DktBadge type={c.badge ?? 'CON'} size="lg" />
        </div>
        <Link to={`/document/${id}`}>
          <div
            className="serif"
            style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', lineHeight: 1.25 }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
          >
            {renderSegs(c.captionParts)}
          </div>
        </Link>
        <div className="mono" style={{ fontSize: 12, color: 'var(--text2)', marginTop: 6 }}>{c.citations?.[0] ?? c.dktNum ?? ''}</div>

        <div style={{ display: 'flex', flexDirection: 'column', marginTop: 18 }}>
          {/* Stages mini */}
          {proceeding && (
            <div style={{ padding: '11px 0', borderTop: '1px solid var(--surface2)' }}>
              <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.2, marginBottom: 8 }}>Proceeding progress</div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                {proceeding.compact.map((step, i) => {
                  const isComplete = step.status === 'complete';
                  const isActive = step.status === 'active';
                  const color = isComplete ? '#10B981' : isActive ? '#F59E0B' : 'var(--border2)';
                  return (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5, flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 8, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.4, whiteSpace: 'nowrap' }}>
                        {step.code}
                      </span>
                      <span
                        style={{
                          width: 14,
                          height: 14,
                          borderRadius: '50%',
                          background: isComplete ? color : isActive ? 'rgba(245,158,11,0.14)' : 'var(--surface)',
                          boxShadow: isActive ? 'inset 0 0 0 2px #F59E0B' : `inset 0 0 0 1px ${isComplete ? color : 'var(--border2)'}`,
                        }}
                      />
                      {step.tag && (
                        <span style={{ fontSize: 8.5, fontWeight: 700, color: step.tag === 'Denied' ? 'var(--status-denied)' : '#F59E0B', whiteSpace: 'nowrap' }}>
                          {step.tag}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <Link to={`/docket/${CASE_TO_NUM[id] ?? id}`} className="text-link" style={{ fontSize: 11, display: 'inline-block', marginTop: 8 }}>
                Open Docket View →
              </Link>
            </div>
          )}

          {(
            [
              ['Tribunal', <span key="t">{c.tribunalLine ?? '—'}</span>],
              ['Decided', <span key="d">{c.decided ?? '—'}</span>],
              ['Outcome', <span key="o" style={{ fontWeight: 600, color: outcomeColor }}>{outcome}</span>],
              ['Treatment', <span key="tr" style={{ fontWeight: 600, color: TREAT_COLOR[level] ?? 'var(--text2)' }}>{TREAT_WORD[level] ?? level}</span>],
            ] as [string, JSX.Element][]
          ).map(([label, value]) => (
            <div key={label} style={{ padding: '11px 0', borderTop: '1px solid var(--surface2)' }}>
              <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.2, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 13.5, color: 'var(--text)', lineHeight: 1.5 }}>{value}</div>
            </div>
          ))}

          {/* Key headnote */}
          <div style={{ padding: '11px 0', borderTop: '1px solid var(--surface2)' }}>
            <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.2, marginBottom: 4 }}>Lead holding</div>
            {headnote ? (
              <div style={{ fontSize: 13.5, color: 'var(--text)', lineHeight: 1.55 }}>
                {headnote.keyId && (
                  <Link to={`/topics/${headnote.keyId}`} className="key-chip" style={{ marginBottom: 6, marginRight: 8 }}>
                    <span className="key-num">{headnote.key}</span>
                    {headnote.topic}
                  </Link>
                )}
                <div style={{ marginTop: 6 }}>{headnote.text}</div>
              </div>
            ) : (
              <div style={{ fontSize: 13.5, color: 'var(--text2)', lineHeight: 1.55 }}>{c.editorial ?? '—'}</div>
            )}
          </div>

          <div style={{ padding: '11px 0', borderTop: '1px solid var(--surface2)' }}>
            <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.2, marginBottom: 4 }}>Citing references</div>
            <div style={{ fontSize: 13.5, color: 'var(--text)' }}>
              <Link to={`/citator/${id}`} className="text-link">
                {citing} decisions — Trace™ report →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Compare() {
  const options = useMemo(
    () => Object.keys(CASES).map((id) => ({ id, label: flatText(CASES[id].captionParts) })),
    [],
  );
  const [left, setLeft] = useState('riverstone-imaging');
  const [right, setRight] = useState('three-rivers');

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Compare Decisions' }]}
        title="Side-by-Side Comparison"
        sub="Compare two determinations across caption, outcome, proceeding posture, holdings, and treatment"
      />
      <div style={{ padding: '24px 32px 60px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, maxWidth: 1280 }}>
          <CompareColumn id={left} onChange={setLeft} options={options} />
          <CompareColumn id={right} onChange={setRight} options={options} />
        </div>
      </div>
    </section>
  );
}
