/*
 * APPLICATIONS (/applications) — the live docket tracker: status summary
 * cards (click to filter), docket-type tabs, and the table of the active
 * docket roll with per-row compact mini progress (docketEngine build().compact)
 * linking into the Docket View. From the comp's <!-- APPLICATIONS --> section.
 *
 * Fixture mode reads the bundled RECENT_DOCKETS roll; live mode folds
 * GET /matters into the same row shape.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';
import { build, type DocketRecord } from '../lib/docketEngine';
import { findingColor, RECENT_DOCKETS } from '../lib/fixtures';

type StatusKey = 'all' | 'pending' | 'granted' | 'denied';

const TYPE_TABS: [string, string][] = [
  ['all', 'All'],
  ['CON', 'CON'],
  ['DET', 'DET'],
  ['DET-EQT', 'DET·EQT'],
  ['DET-ASC', 'DET·ASC'],
  ['LNR-EQT', 'LNR·EQT'],
  ['LNR-ASC', 'LNR·ASC'],
];

function statusOf(finding: string | null | undefined): StatusKey | 'other' {
  if (finding === 'Approved' || finding === 'Issued') return 'granted';
  if (finding === 'Denied') return 'denied';
  if (finding === 'Pending') return 'pending';
  return 'other';
}

/** Comp's buildCompactMini — dot colors from the proceeding's compact steps. */
function compactMini(rec: DocketRecord): string[] {
  const proceeding = build(rec);
  if (!proceeding) return [];
  return proceeding.compact.map((c) =>
    c.status === 'complete' ? '#10B981' : c.status === 'active' ? '#F59E0B' : 'var(--border2)',
  );
}

/** Fold GET /matters rows into DocketRecord shape (live mode). */
function liveMattersToRecords(items: Record<string, unknown>[]): DocketRecord[] {
  return items.map((m) => ({
    type: String(m.docket_family ?? m.docketFamily ?? 'CON'),
    num: String(m.docket_id ?? m.docketId ?? ''),
    facility: (m.facility as string) ?? (m.applicant as string) ?? null,
    title: (m.project_description as string) ?? (m.matter_type as string) ?? null,
    received: (m.date_filed as string) ?? null,
    date: (m.final_decision_date as string) ?? null,
    finding: (m.final_outcome as string) ?? 'Pending',
    county: (m.county as string) ?? null,
    contact: null,
  }));
}

export default function Applications() {
  const navigate = useNavigate();
  const [typeTab, setTypeTab] = useState('all');
  const [status, setStatus] = useState<StatusKey>('all');
  const [liveRecords, setLiveRecords] = useState<DocketRecord[] | null>(null);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    api
      .searchMatters({ limit: 100 })
      .then((res) => alive && setLiveRecords(liveMattersToRecords(res.items)))
      .catch(() => alive && setLiveRecords(null));
    return () => {
      alive = false;
    };
  }, []);

  const records = (!api.USE_FIXTURES && liveRecords) || RECENT_DOCKETS;

  const filtered = useMemo(
    () =>
      records.filter(
        (d) => (typeTab === 'all' || d.type === typeTab) && (status === 'all' || statusOf(d.finding) === status),
      ),
    [records, typeTab, status],
  );

  const countStatus = (s: StatusKey) =>
    s === 'all' ? records.length : records.filter((d) => statusOf(d.finding) === s).length;

  const statusCards: { key: StatusKey; label: string; color: string }[] = [
    { key: 'all', label: 'Total', color: 'var(--text)' },
    { key: 'pending', label: 'Pending', color: '#F59E0B' },
    { key: 'granted', label: 'Granted', color: '#10B981' },
    { key: 'denied', label: 'Denied', color: 'var(--accent-text)' },
  ];

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Knowledge Base', to: '/kb' }, { label: 'Applications' }]}
        title="Applications & Requests"
        sub="Live docket tracker — CON applications, determinations of reviewability, and nonreviewability requests before the DCH Planning Section"
        right={
          <Link to="/submit" className="btn-primary" style={{ fontSize: 12.5, padding: '8px 14px' }}>
            <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
              <path d="M8 3 L8 13 M3 8 L13 8" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
            </svg>
            Add application
          </Link>
        }
      >
        {/* Status summary cards (click to filter) */}
        <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
          {statusCards.map((s) => {
            const active = status === s.key;
            return (
              <button
                key={s.key}
                onClick={() => setStatus(s.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 16px',
                  background: active ? 'rgba(244,63,94,0.14)' : 'var(--page-bg)',
                  border: `1px solid ${active ? 'var(--brand-red)' : 'var(--surface2)'}`,
                  borderRadius: 2,
                }}
              >
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: s.color }} />
                <span className="serif" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
                  {countStatus(s.key)}
                </span>
                <span className="label-upper" style={{ color: 'var(--text2)', letterSpacing: 1 }}>{s.label}</span>
              </button>
            );
          })}
        </div>
      </PageHeader>

      <div style={{ padding: '22px 32px 60px' }}>
        {/* Type filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <span className="label-upper" style={{ letterSpacing: 1, marginRight: 2 }}>Type</span>
          {TYPE_TABS.map(([id, label]) => (
            <button key={id} className={`chip-tab${typeTab === id ? ' active' : ''}`} onClick={() => setTypeTab(id)}>
              {label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="list-card" style={{ overflow: 'hidden' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '96px 1.6fr 130px 110px 110px 110px',
              padding: '10px 18px',
              background: 'var(--page-bg)',
              borderBottom: '2px solid var(--border2)',
              fontSize: 10,
              fontWeight: 700,
              color: 'var(--text3)',
              textTransform: 'uppercase',
              letterSpacing: 1.2,
            }}
          >
            <div>Type</div>
            <div>Facility &amp; project</div>
            <div>Docket No.</div>
            <div>Received</div>
            <div>Decided</div>
            <div>Finding</div>
          </div>
          {filtered.map((d) => (
            <button
              key={d.num}
              className="list-row row-hover"
              onClick={() => navigate(`/docket/${d.num}`)}
              style={{
                display: 'grid',
                gridTemplateColumns: '96px 1.6fr 130px 110px 110px 110px',
                width: '100%',
                textAlign: 'left',
                padding: '12px 18px',
                alignItems: 'center',
                background: 'var(--surface)',
              }}
            >
              <div>
                <DktBadge type={d.type} size="lg" />
              </div>
              <div style={{ minWidth: 0, paddingRight: 12 }}>
                <div className="serif" style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>{d.facility}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 1 }}>
                  {d.title}
                  {d.county ? ` · ${d.county} Co.` : ''}
                </div>
                {/* Compact mini progress */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 3, marginTop: 6 }}>
                  {compactMini(d).map((color, i) => (
                    <span key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
                  ))}
                  <span style={{ fontSize: 9.5, color: 'var(--text2)', marginLeft: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Docket view →
                  </span>
                </div>
              </div>
              <div className="mono" style={{ fontSize: 11.5, color: 'var(--text)' }}>{d.num}</div>
              <div style={{ fontSize: 12, color: 'var(--text2)' }}>{String(d.received ?? '—')}</div>
              <div style={{ fontSize: 12, color: 'var(--text2)' }}>{d.date ? String(d.date) : '—'}</div>
              <div>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11.5, fontWeight: 600, color: findingColor(d.finding) }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: findingColor(d.finding) }} />
                  {d.finding}
                </span>
              </div>
            </button>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: '48px 20px', textAlign: 'center', fontSize: 12.5, color: 'var(--text3)' }}>
              No dockets match this type/status combination.
            </div>
          )}
        </div>
        <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text2)' }}>
          Showing <strong style={{ color: 'var(--text)' }}>{filtered.length}</strong> of the active docket roll · drawn from the published
          DCH project lists. Click a row to open its Docket View.
        </div>
      </div>
    </section>
  );
}
