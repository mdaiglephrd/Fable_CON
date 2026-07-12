/*
 * DOCKET (/docket/:docketId) — the dark "case console". 3-way display toggle
 * (flowchart / timeline / table) over the SAME stage data from getProceeding
 * (docketEngine.build over fixture records in dev). Status pills from STATUS,
 * substep hover tooltips (tip rows + statute), outcome forks, terminal
 * outcomes, regime notes, deadline callouts, compact mini progress bar, and
 * the precedent signal. Flowchart structure from the comp's <!-- DOCKET -->.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { caseIdForDocket } from '../lib/fixtures';
import { statusMeta, type Fork, type Stage, type TerminalOutcome } from '../lib/docketEngine';

type DocketMode = 'flowchart' | 'timeline' | 'table';

function StatusPill({ status, small }: { status: string; small?: boolean }) {
  const meta = statusMeta(status);
  return (
    <span className={`status-pill${small ? ' sm' : ''}`} style={{ background: meta.bg, color: meta.color }}>
      {meta.label}
    </span>
  );
}

function ForkCards({ forks, stageN }: { forks: Fork[]; stageN: string }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 13 }}>
      {forks.map((f, i) => {
        const taken = f.status === 'taken';
        return (
          <div
            key={`${stageN}-fork-${i}`}
            style={{
              flex: 1,
              minWidth: 210,
              padding: '11px 15px',
              borderRadius: 8,
              background: taken ? 'rgba(59,130,246,0.10)' : 'rgba(15,23,42,0.6)',
              boxShadow: taken ? 'inset 0 0 0 1px #3B82F6' : 'inset 0 0 0 1px var(--surface2)',
              opacity: taken ? 1 : 0.55,
            }}
          >
            <div style={{ fontSize: 12.5, fontWeight: 700, color: taken ? '#93C5FD' : 'var(--text3)', marginBottom: 4 }}>{f.label}</div>
            <div style={{ fontSize: 11.5, color: 'var(--text3)', lineHeight: 1.4 }}>{f.title}</div>
          </div>
        );
      })}
    </div>
  );
}

function TerminalCards({ terminal, stageN }: { terminal: TerminalOutcome[]; stageN: string }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 13 }}>
      {terminal.map((t, i) => {
        const taken = t.status === 'taken';
        return (
          <div
            key={`${stageN}-term-${i}`}
            style={{
              flex: 1,
              minWidth: 150,
              textAlign: 'center',
              padding: 13,
              borderRadius: 8,
              background: taken ? 'rgba(245,158,11,0.12)' : 'rgba(15,23,42,0.5)',
              boxShadow: taken ? 'inset 0 0 0 1px #F59E0B' : 'inset 0 0 0 1px var(--surface2)',
              opacity: taken ? 1 : 0.45,
            }}
          >
            <div style={{ fontSize: 12.5, fontWeight: 700, color: taken ? '#FBBF24' : 'var(--text3)' }}>{t.label}</div>
          </div>
        );
      })}
    </div>
  );
}

function DeadlineBox({ items }: { items: string[] }) {
  return (
    <div
      style={{
        marginTop: 13,
        padding: '15px 17px',
        borderRadius: 8,
        background: 'rgba(245,158,11,0.08)',
        boxShadow: 'inset 0 0 0 1px #F59E0B',
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, color: '#FBBF24', marginBottom: 9 }}>⬛ UPCOMING DEADLINES</div>
      {items.map((d, i) => (
        <div key={i} style={{ fontSize: 12.5, color: '#FDE68A', lineHeight: 1.7 }}>
          ▪ {d}
        </div>
      ))}
    </div>
  );
}

export default function Docket() {
  const { docketId = '' } = useParams();
  const { showToast } = useToast();
  const [data, setData] = useState<api.ProceedingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<DocketMode>('flowchart');
  const [hoveredTip, setHoveredTip] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    api
      .getProceeding(docketId)
      .then((p) => alive && setData(p))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [docketId]);

  const caseId = caseIdForDocket(docketId);

  if (error) {
    return (
      <section style={{ background: 'var(--page-bg)', minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 80, color: 'var(--text3)', fontSize: 13 }}>
          Docket record unavailable — {error}
        </div>
      </section>
    );
  }
  if (!data) {
    return <div style={{ padding: '60px 40px', color: 'var(--text3)', fontSize: 13 }}>Loading docket…</div>;
  }

  const onRemand = !!data.onRemand;
  const statusWord = onRemand ? 'ON REMAND' : data.isClosed ? 'CLOSED' : 'ACTIVE';
  const statusColor = onRemand ? '#F59E0B' : data.isClosed ? 'var(--text2)' : '#10B981';
  const statusBg = onRemand ? 'rgba(245,158,11,0.14)' : data.isClosed ? 'rgba(148,163,184,0.14)' : 'rgba(16,185,129,0.14)';
  const metaLine = data.filedLine + (data.closedLine ? ` · ${data.closedLine} · Duration ${data.durationLine}` : '');
  const activeDeadlineStage = !data.isClosed ? (data.stages ?? []).find((s) => s.deadline) : undefined;
  const closedFooter = data.closedLine ? `Record closed ${data.closedLine.replace('Closed ', '')} · Duration ${data.durationLine}` : null;
  const headerNum = data.headerNum ?? data.docketId ?? docketId;
  const facilityLine = [data.facility, data.projectTitle].filter(Boolean).join(' — ');

  return (
    <section style={{ background: 'var(--page-bg)', minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar */}
      <div
        style={{
          background: 'var(--surface)',
          boxShadow: 'inset 0 -1px 0 var(--surface2)',
          padding: '14px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <Breadcrumb items={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'Docket View' }]} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 3-way display toggle */}
          <div className="docket-toggle">
            {(['flowchart', 'timeline', 'table'] as DocketMode[]).map((m) => (
              <button key={m} className={mode === m ? 'active' : ''} onClick={() => setMode(m)}>
                {m === 'flowchart' ? 'Flowchart' : m === 'timeline' ? 'Timeline' : 'Table'}
              </button>
            ))}
          </div>
          <button className="btn-outline" onClick={() => showToast('PDF export — available when connected to document store')}>
            <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
              <path d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Export PDF
          </button>
        </div>
      </div>

      <div style={{ flex: 1, padding: '32px 40px 90px', maxWidth: 1180, width: '100%', margin: '0 auto', fontFamily: 'var(--font-ui)' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', marginBottom: 22 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 9, flexWrap: 'wrap' }}>
              <span className="mono" style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px' }}>
                {headerNum}
              </span>
              <span className="status-pill" style={{ background: statusBg, color: statusColor }}>
                {statusWord}
              </span>
              <span className="status-pill" style={{ background: `${data.badge.color}26`, color: data.badge.color }}>
                {data.badge.label}
              </span>
              {data.subtypeLabel && (
                <span style={{ fontSize: 11, color: 'var(--text3)' }} title={data.subtypeSub}>
                  {data.subtypeSub}
                </span>
              )}
            </div>
            {facilityLine && <div style={{ fontSize: 15, color: 'var(--text2)', marginBottom: 5, fontWeight: 500 }}>{facilityLine}</div>}
            <div className="mono" style={{ fontSize: 12, color: 'var(--text3)' }}>
              {metaLine}
            </div>
            {caseId && (
              <div style={{ marginTop: 8, display: 'flex', gap: 14, fontSize: 12 }}>
                <Link to={`/document/${caseId}`} className="text-link">
                  Read the opinion →
                </Link>
                <Link to={`/citator/${caseId}`} className="text-link">
                  Trace™ Citator →
                </Link>
              </div>
            )}
          </div>
          {/* Precedent signal (closed dockets) */}
          {data.precedent && (
            <div
              style={{
                boxShadow: `inset 0 0 0 1px ${data.precedent.color}`,
                borderRadius: 8,
                padding: '12px 16px',
                minWidth: 260,
                maxWidth: 340,
                background: 'rgba(2,6,23,0.5)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, fontWeight: 700, color: data.precedent.color, marginBottom: 5, letterSpacing: 0.3 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: data.precedent.color }} />
                {data.precedent.label}
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--text2)', lineHeight: 1.45 }}>{data.precedent.detail}</div>
            </div>
          )}
        </div>

        {/* Upcoming deadlines (active dockets only) */}
        {activeDeadlineStage?.deadline && (
          <div
            style={{
              background: 'rgba(245,158,11,0.08)',
              borderRadius: 8,
              padding: '15px 20px',
              marginBottom: 10,
              boxShadow: 'inset 0 0 0 1px rgba(245,158,11,0.35)',
            }}
          >
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, color: '#FBBF24', marginBottom: 9 }}>⬛ UPCOMING DEADLINES</div>
            {activeDeadlineStage.deadline.items.map((d, i) => (
              <div key={i} style={{ fontSize: 12.5, color: '#FDE68A', lineHeight: 1.7 }}>
                ▪ {d}
              </div>
            ))}
          </div>
        )}

        {/* Compact mini stepper */}
        <div style={{ background: 'var(--surface2)', borderRadius: 8, padding: '18px 28px', marginBottom: 10, boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 4 }}>
            {(data.compact ?? []).map((c, i) => {
              const isComplete = c.status === 'complete';
              const isActive = c.status === 'active';
              const color = isComplete ? '#10B981' : isActive ? '#F59E0B' : 'var(--border2)';
              return (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7, flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 9, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, whiteSpace: 'nowrap' }}>
                    {c.code}
                  </span>
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: isComplete ? color : isActive ? 'rgba(245,158,11,0.14)' : 'var(--surface)',
                      boxShadow: isActive ? 'inset 0 0 0 2px #F59E0B' : isComplete ? 'none' : 'inset 0 0 0 1px var(--border2)',
                      flexShrink: 0,
                    }}
                  >
                    {isComplete && <span style={{ color: 'var(--page-bg)', fontSize: 11, fontWeight: 900 }}>✓</span>}
                  </div>
                  {c.tag && (
                    <span style={{ fontSize: 9, fontWeight: 700, color: c.tag === 'Denied' ? '#F43F5E' : '#F59E0B', whiteSpace: 'nowrap' }}>{c.tag}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Final disposition banner */}
        {data.finalDisposition && (
          <div
            style={{
              background: 'var(--surface2)',
              borderRadius: 8,
              padding: '14px 20px',
              marginBottom: 10,
              fontSize: 13,
              color: 'var(--text)',
              fontWeight: 500,
              boxShadow: 'inset 3px 0 0 #F59E0B',
            }}
          >
            {data.finalDisposition}
          </div>
        )}

        {/* ===== Stage renderings — same data, three modes ===== */}
        {mode === 'flowchart' && (
          <FlowchartStages stages={data.stages ?? []} hoveredTip={hoveredTip} setHoveredTip={setHoveredTip} />
        )}
        {mode === 'timeline' && <TimelineStages stages={data.stages ?? []} />}
        {mode === 'table' && <TableStages stages={data.stages ?? []} />}

        {closedFooter && (
          <div className="mono" style={{ textAlign: 'center', fontSize: 11.5, color: 'var(--text3)', marginTop: 26 }}>
            {closedFooter}
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Flowchart mode (the comp's rendering)
// ---------------------------------------------------------------------------

function FlowchartStages({
  stages,
  hoveredTip,
  setHoveredTip,
}: {
  stages: Stage[];
  hoveredTip: string | null;
  setHoveredTip: (k: string | null) => void;
}) {
  return (
    <>
      {stages.map((s) => {
        const meta = statusMeta(s.status);
        return (
          <div key={s.n} style={{ boxShadow: 'inset 0 1px 0 var(--surface2)', padding: '24px 0' }}>
            <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div style={{ flexShrink: 0, width: 190 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
                  <span className="mono" style={{ fontSize: 16, fontWeight: 700, color: meta.color }}>
                    {s.n}
                  </span>
                  <StatusPill status={s.status} small />
                </div>
                <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--text)', marginBottom: 5, lineHeight: 1.3 }}>{s.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.5 }}>{s.dateLine}</div>
              </div>
              <div style={{ flex: 1, minWidth: 300 }}>
                {/* Substep chips with hover tooltips */}
                {(s.substeps?.length ?? 0) > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                    {s.substeps!.map((sub, idx) => {
                      const key = `${s.n}-${sub.code}`;
                      const isHovered = hoveredTip === key;
                      const tipMeta = statusMeta(sub.tip.status);
                      return (
                        <div key={key} style={{ position: 'relative' }}>
                          <button
                            className={`substep-chip${isHovered ? ' hovered' : ''}`}
                            onMouseEnter={() => setHoveredTip(key)}
                            onMouseLeave={() => setHoveredTip(null)}
                            onClick={() => setHoveredTip(isHovered ? null : key)}
                          >
                            <span
                              className="mono"
                              style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', background: 'var(--surface2)', padding: '1px 5px', borderRadius: 3 }}
                            >
                              {sub.code}
                            </span>
                            <span style={{ fontSize: 12.5, color: 'var(--text2)' }}>{sub.label}</span>
                            <span style={{ color: 'var(--text3)', fontSize: 11 }}>→</span>
                          </button>
                          {isHovered && (
                            <div
                              className="substep-tip"
                              style={{
                                boxShadow: `inset 0 0 0 1px ${tipMeta.color}, 0px 10px 24px -6px rgba(0,0,0,0.5)`,
                                ...(idx >= 2 ? { right: 0 } : { left: 0 }),
                              }}
                              onMouseEnter={() => setHoveredTip(key)}
                              onMouseLeave={() => setHoveredTip(null)}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 9 }}>
                                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', lineHeight: 1.3 }}>{sub.tip.title}</span>
                                <span
                                  className="mono"
                                  style={{
                                    flexShrink: 0,
                                    fontSize: 9,
                                    fontWeight: 700,
                                    padding: '2px 6px',
                                    borderRadius: 4,
                                    background: tipMeta.bg,
                                    color: tipMeta.color,
                                  }}
                                >
                                  {tipMeta.label}
                                </span>
                              </div>
                              {sub.tip.rows.map((r, i) => (
                                <div key={i} style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.55, marginBottom: 6 }}>
                                  {r}
                                </div>
                              ))}
                              {sub.tip.statute && (
                                <div
                                  className="mono"
                                  style={{ fontSize: 10.5, color: 'var(--text3)', marginTop: 7, paddingTop: 9, boxShadow: 'inset 0 1px 0 var(--surface2)' }}
                                >
                                  {sub.tip.statute}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Outcome forks */}
                {(s.forks?.length ?? 0) > 0 && <ForkCards forks={s.forks!} stageN={s.n} />}

                {/* Terminal outcomes */}
                {(s.terminal?.length ?? 0) > 0 && <TerminalCards terminal={s.terminal!} stageN={s.n} />}

                {/* Regime note (current vs. legacy) */}
                {s.regimeNote && (
                  <div style={{ display: 'flex', gap: 14, marginTop: 10, flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 220, padding: '15px 17px', borderRadius: 8, background: 'rgba(59,130,246,0.07)', boxShadow: 'inset 0 0 0 1px #3B82F6' }}>
                      <span
                        className="mono"
                        style={{ display: 'inline-flex', fontSize: 9, fontWeight: 700, color: '#93C5FD', background: 'rgba(59,130,246,0.15)', padding: '2px 6px', borderRadius: 4, marginBottom: 7 }}
                      >
                        CURRENT
                      </span>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>{s.regimeNote.current.label}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text2)', lineHeight: 1.45 }}>{s.regimeNote.current.detail}</div>
                    </div>
                    <div
                      style={{
                        flex: 1,
                        minWidth: 220,
                        padding: '15px 17px',
                        borderRadius: 8,
                        background: 'rgba(15,23,42,0.5)',
                        boxShadow: 'inset 0 0 0 1px var(--surface2)',
                        opacity: 0.6,
                      }}
                    >
                      <span
                        className="mono"
                        style={{ display: 'inline-flex', fontSize: 9, fontWeight: 700, color: 'var(--text3)', background: 'var(--surface2)', padding: '2px 6px', borderRadius: 4, marginBottom: 7 }}
                      >
                        LEGACY
                      </span>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)', marginBottom: 4 }}>{s.regimeNote.legacy.label}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text3)', lineHeight: 1.45 }}>{s.regimeNote.legacy.detail}</div>
                    </div>
                  </div>
                )}

                {/* Stage-level deadline callout */}
                {s.deadline && <DeadlineBox items={s.deadline.items} />}
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Timeline mode — vertical rail over the same stages
// ---------------------------------------------------------------------------

function TimelineStages({ stages }: { stages: Stage[] }) {
  return (
    <div style={{ position: 'relative', paddingLeft: 8, marginTop: 8 }}>
      {stages.map((s, i) => {
        const meta = statusMeta(s.status);
        const last = i === stages.length - 1;
        return (
          <div key={s.n} style={{ display: 'flex', gap: 18, position: 'relative', paddingBottom: last ? 0 : 26 }}>
            {/* rail */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 24, flexShrink: 0 }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  background: s.status === 'complete' ? meta.color : meta.bg,
                  boxShadow: `inset 0 0 0 2px ${meta.color}`,
                  marginTop: 3,
                  flexShrink: 0,
                }}
              />
              {!last && <div style={{ width: 2, flex: 1, background: 'var(--surface2)', marginTop: 4 }} />}
            </div>
            <div style={{ flex: 1, minWidth: 0, paddingBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: meta.color }}>
                  Stage {s.n}
                </span>
                <StatusPill status={s.status} small />
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>{s.dateLine}</span>
              </div>
              <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--text)', margin: '6px 0 4px' }}>{s.title}</div>
              {(s.substeps?.length ?? 0) > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                  {s.substeps!.map((sub) => {
                    const subMeta = statusMeta(sub.tip.status);
                    return (
                      <span
                        key={sub.code}
                        title={sub.tip.rows.join(' ')}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '4px 9px',
                          borderRadius: 5,
                          background: 'var(--surface)',
                          boxShadow: 'inset 0 0 0 1px var(--surface2)',
                          fontSize: 11.5,
                          color: 'var(--text2)',
                        }}
                      >
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: subMeta.color }} />
                        <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, color: 'var(--text3)' }}>
                          {sub.code}
                        </span>
                        {sub.label}
                      </span>
                    );
                  })}
                </div>
              )}
              {(s.forks?.length ?? 0) > 0 && (
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text3)' }}>
                  {s.forks!
                    .filter((f) => f.status === 'taken')
                    .map((f) => (
                      <span key={f.key} style={{ color: '#93C5FD', fontWeight: 600, marginRight: 12 }}>
                        ⑂ {f.label}
                      </span>
                    ))}
                </div>
              )}
              {s.deadline && <DeadlineBox items={s.deadline.items} />}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table mode — same stages as a compact table
// ---------------------------------------------------------------------------

function TableStages({ stages }: { stages: Stage[] }) {
  return (
    <div className="card" style={{ borderRadius: 8, overflow: 'hidden', marginTop: 8 }}>
      <table className="docket-table">
        <thead>
          <tr>
            <th style={{ width: 40 }}>#</th>
            <th>Stage</th>
            <th style={{ width: 110 }}>Status</th>
            <th>Timing</th>
            <th>Substeps</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {stages.map((s) => {
            const meta = statusMeta(s.status);
            const takenFork = (s.forks ?? []).find((f) => f.status === 'taken');
            const takenTerminal = (s.terminal ?? []).find((t) => t.status === 'taken');
            return (
              <tr key={s.n}>
                <td className="mono" style={{ fontWeight: 700, color: meta.color }}>
                  {s.n}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--text)' }}>{s.title}</td>
                <td>
                  <StatusPill status={s.status} small />
                </td>
                <td style={{ color: 'var(--text3)', fontSize: 11.5 }}>{s.dateLine || '—'}</td>
                <td style={{ color: 'var(--text2)', fontSize: 11.5 }}>
                  {(s.substeps ?? []).map((sub) => sub.label).join(' · ') || (s.regimeNote ? 'Regime note' : '—')}
                </td>
                <td style={{ fontSize: 11.5, color: takenFork || takenTerminal ? '#93C5FD' : 'var(--text3)', fontWeight: takenFork || takenTerminal ? 600 : 400 }}>
                  {takenTerminal?.label ?? takenFork?.label ?? '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
