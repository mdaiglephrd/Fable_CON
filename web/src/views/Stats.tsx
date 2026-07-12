/*
 * OUTCOME STATISTICS (/stats) — KPI cards, grant/deny/withdraw bars by
 * service category, filing volume by year (pure-CSS bar chart), volume by
 * docket type (horizontal bars), and the appeal panel, with all/3yr/1yr
 * range tabs. Numbers from the comp's stats block in fixture mode; live
 * mode maps GET /stats?range= onto the same panels.
 */
import { useEffect, useMemo, useState } from 'react';

import { PageHeader } from '../components/PageHeader';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';

type Range = 'all' | '3yr' | '1yr';

const RANGE_TABS: { id: Range; label: string }[] = [
  { id: 'all', label: 'All years' },
  { id: '3yr', label: 'Last 3 yrs' },
  { id: '1yr', label: 'Last 12 mo' },
];

interface StatsShape {
  kpis: { label: string; value: string; accent: string; delta: string; deltaColor: string }[];
  byService: { label: string; total: number; grantPct: number; denyPct: number; wdPct: number }[];
  byYear: { year: string; count: number }[];
  byType: [string, number, string][];
  appeal: { label: string; value: string; sub: string; color: string }[];
}

/** Fixture aggregates (the comp's ANALYTICS block, scaled by range). */
function fixtureStats(range: Range): StatsShape {
  const mult = range === 'all' ? 1 : range === '3yr' ? 0.42 : 0.16;
  const ri = (n: number) => Math.round(n * mult);
  return {
    kpis: [
      { label: 'Total dockets', value: ri(12847).toLocaleString(), accent: 'var(--border2)', delta: '+312 vs. prior period', deltaColor: '#10B981' },
      { label: 'CON grant rate', value: '58%', accent: '#10B981', delta: '1,128 granted / 1,930 decided', deltaColor: 'var(--text2)' },
      { label: 'Denial rate', value: '24%', accent: '#8E1B1F', delta: '802 denied applications', deltaColor: 'var(--text2)' },
      { label: 'Reversal on review', value: '31%', accent: '#F59E0B', delta: '70 of 224 appeals reversed', deltaColor: 'var(--text2)' },
    ],
    byService: [
      { label: 'Imaging — MRI / CT / PET', total: ri(418), grantPct: 52, denyPct: 33, wdPct: 15 },
      { label: 'Hospital Beds', total: ri(362), grantPct: 61, denyPct: 28, wdPct: 11 },
      { label: 'Ambulatory Surgery (ASC)', total: ri(301), grantPct: 67, denyPct: 22, wdPct: 11 },
      { label: 'Cardiac Catheterization', total: ri(188), grantPct: 48, denyPct: 42, wdPct: 10 },
      { label: 'Skilled Nursing / LTC', total: ri(322), grantPct: 55, denyPct: 34, wdPct: 11 },
      { label: 'Psychiatric / Behavioral', total: ri(184), grantPct: 44, denyPct: 46, wdPct: 10 },
    ],
    byYear: [
      { year: '2021', count: 188 },
      { year: '2022', count: 214 },
      { year: '2023', count: 241 },
      { year: '2024', count: 256 },
      { year: '2025', count: 233 },
      { year: '2026', count: 96 },
    ],
    byType: [
      ['CON', ri(4128), '#8E1B1F'],
      ['DET', ri(4028), '#F59E0B'],
      ['DET-EQT', ri(801), '#8B5CF6'],
      ['LNR-EQT', ri(651), '#8B5CF6'],
      ['LNR-ASC', ri(364), '#3B82F6'],
      ['DET-ASC', ri(124), '#10B981'],
    ],
    appeal: [
      { label: 'Appeal rate', value: '18%', sub: 'of final decisions taken to superior court', color: 'var(--text)' },
      { label: 'Reversal rate', value: '31%', sub: 'of appeals reversed or remanded', color: '#F59E0B' },
      { label: 'Affirmance', value: '69%', sub: 'agency decision upheld on review', color: '#10B981' },
    ],
  };
}

/** Map GET /stats onto the panel shape (live mode, best-effort). */
function liveToShape(raw: Record<string, unknown>): StatsShape {
  const kpis = (raw.kpis ?? {}) as Record<string, number>;
  const appeal = (raw.appeal ?? {}) as Record<string, number>;
  const byService = ((raw.byService ?? []) as { serviceType?: string; total?: number; approved?: number; denied?: number }[]).map(
    (s) => {
      const total = s.total ?? 0;
      const grant = total ? Math.round(((s.approved ?? 0) / total) * 100) : 0;
      const deny = total ? Math.round(((s.denied ?? 0) / total) * 100) : 0;
      return { label: s.serviceType ?? '—', total, grantPct: grant, denyPct: deny, wdPct: Math.max(0, 100 - grant - deny) };
    },
  );
  const typeColor: Record<string, string> = {
    CON: '#8E1B1F',
    DET: '#F59E0B',
    'DET-EQT': '#8B5CF6',
    'LNR-EQT': '#8B5CF6',
    'LNR-ASC': '#3B82F6',
    'DET-ASC': '#10B981',
  };
  return {
    kpis: [
      { label: 'Total dockets', value: (kpis.totalDockets ?? 0).toLocaleString(), accent: 'var(--border2)', delta: '', deltaColor: 'var(--text2)' },
      { label: 'Grant rate', value: `${kpis.grantRate ?? 0}%`, accent: '#10B981', delta: '', deltaColor: 'var(--text2)' },
      { label: 'Denial rate', value: `${kpis.denialRate ?? 0}%`, accent: '#8E1B1F', delta: '', deltaColor: 'var(--text2)' },
      { label: 'Reversal on review', value: `${kpis.reversalRate ?? 0}%`, accent: '#F59E0B', delta: '', deltaColor: 'var(--text2)' },
    ],
    byService: byService.slice(0, 8),
    byYear: ((raw.byYear ?? []) as { year?: number | string; total?: number }[]).map((y) => ({
      year: String(y.year ?? ''),
      count: y.total ?? 0,
    })),
    byType: ((raw.byFamily ?? []) as { family?: string; total?: number }[]).map((f) => [
      f.family ?? '—',
      f.total ?? 0,
      typeColor[f.family ?? ''] ?? '#94A3B8',
    ]),
    appeal: [
      { label: 'Appeal rate', value: `${appeal.appealedPct ?? 0}%`, sub: 'of final decisions taken to superior court', color: 'var(--text)' },
      { label: 'Reversal rate', value: `${appeal.reversalPct ?? 0}%`, sub: 'of appeals reversed or remanded', color: '#F59E0B' },
      { label: 'Affirmance', value: `${appeal.affirmancePct ?? 0}%`, sub: 'agency decision upheld on review', color: '#10B981' },
    ],
  };
}

export default function Stats() {
  const [range, setRange] = useState<Range>('all');
  const [live, setLive] = useState<StatsShape | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    setLive(null);
    api
      .getStats(range)
      .then((raw) => alive && setLive(liveToShape(raw)))
      .catch((e: Error) => alive && setLiveError(e.message));
    return () => {
      alive = false;
    };
  }, [range]);

  const stats = useMemo(() => (!api.USE_FIXTURES && live) || fixtureStats(range), [live, range]);
  const maxYear = Math.max(1, ...stats.byYear.map((y) => y.count));
  const maxType = Math.max(1, ...stats.byType.map((t) => t[1]));

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Outcome Statistics' }]}
        title="CON Outcome Statistics"
        sub="Grant, denial, and withdrawal patterns across the DCH project corpus · 2020 – 2026"
        right={
          <div style={{ display: 'flex', gap: 8 }}>
            {RANGE_TABS.map((t) => (
              <button key={t.id} className={`chip-tab${range === t.id ? ' active' : ''}`} onClick={() => setRange(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
        }
      />

      <div style={{ padding: '28px 32px 60px' }}>
        {liveError && (
          <div style={{ maxWidth: 1280, marginBottom: 14, fontSize: 12, color: 'var(--status-denied)' }}>
            Live stats unavailable ({liveError}) — showing bundled corpus figures.
          </div>
        )}

        {/* KPI cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, maxWidth: 1280, marginBottom: 28 }}>
          {stats.kpis.map((k) => (
            <div key={k.label} className="card" style={{ borderTop: `3px solid ${k.accent}`, borderRadius: '0 0 2px 2px', padding: '18px 20px' }}>
              <div className="label-upper" style={{ letterSpacing: 1.2 }}>{k.label}</div>
              <div className="serif" style={{ fontSize: 34, fontWeight: 600, color: 'var(--text)', marginTop: 8, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                {k.value}
              </div>
              {k.delta && <div style={{ fontSize: 12, color: k.deltaColor, marginTop: 6 }}>{k.delta}</div>}
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 24, maxWidth: 1280 }}>
          {/* Outcomes by service */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: '0 0 4px' }}>Outcomes by service category</h2>
            <div style={{ fontSize: 11.5, color: 'var(--text2)', marginBottom: 18 }}>Share of applications granted vs. denied/withdrawn</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {stats.byService.map((s) => (
                <div key={s.label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 4 }}>
                    <span style={{ color: 'var(--text)', fontWeight: 500 }}>{s.label}</span>
                    <span style={{ color: 'var(--text2)', fontVariantNumeric: 'tabular-nums' }}>
                      {s.total.toLocaleString()} dockets · <strong style={{ color: '#10B981' }}>{s.grantPct}%</strong>
                    </span>
                  </div>
                  <div style={{ display: 'flex', height: 18, borderRadius: 2, overflow: 'hidden', background: 'var(--surface2)' }}>
                    <div style={{ width: `${s.grantPct}%`, background: '#10B981' }} title={`Granted ${s.grantPct}%`} />
                    <div style={{ width: `${s.denyPct}%`, background: '#8E1B1F' }} title={`Denied ${s.denyPct}%`} />
                    <div style={{ width: `${s.wdPct}%`, background: '#F59E0B' }} title={`Withdrawn ${s.wdPct}%`} />
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 18, marginTop: 18, fontSize: 11, color: 'var(--text2)' }}>
              {(
                [
                  ['Granted', '#10B981'],
                  ['Denied', '#8E1B1F'],
                  ['Withdrawn', '#F59E0B'],
                ] as const
              ).map(([label, color]) => (
                <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 10, background: color, borderRadius: 2 }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {/* Filings by year */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: '0 0 4px' }}>Filing volume by year</h2>
            <div style={{ fontSize: 11.5, color: 'var(--text2)', marginBottom: 18 }}>New dockets received per calendar year</div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 180, paddingTop: 10 }}>
              {stats.byYear.map((y) => (
                <div key={y.year} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, height: '100%', justifyContent: 'flex-end' }}>
                  <span style={{ fontSize: 11, color: 'var(--text)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{y.count}</span>
                  <div
                    title={`${y.count} dockets`}
                    style={{ width: '100%', background: '#8E1B1F', borderRadius: '2px 2px 0 0', height: `${Math.round((y.count / maxYear) * 100)}%` }}
                  />
                  <span style={{ fontSize: 10.5, color: 'var(--text3)' }}>{y.year}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* By docket type + appeal panel */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, maxWidth: 1280, marginTop: 24 }}>
          <div className="card" style={{ padding: '20px 22px' }}>
            <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: '0 0 16px' }}>Volume by docket type</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
              {stats.byType.map(([type, count, color]) => (
                <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 78, flexShrink: 0 }}>
                    <DktBadge type={type} size="lg" />
                  </div>
                  <div style={{ flex: 1, height: 14, background: 'var(--surface2)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.round((count / maxType) * 100)}%`, background: color }} />
                  </div>
                  <span style={{ width: 52, textAlign: 'right', fontSize: 12, color: 'var(--text)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                    {count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="card" style={{ padding: '20px 22px' }}>
            <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: '0 0 4px' }}>Appeal &amp; reversal rates</h2>
            <div style={{ fontSize: 11.5, color: 'var(--text2)', marginBottom: 16 }}>Of decisions taken to judicial review</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {stats.appeal.map((a) => (
                <div key={a.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', background: 'var(--page-bg)', border: '1px solid var(--surface2)', borderRadius: 2 }}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600 }}>{a.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 2 }}>{a.sub}</div>
                  </div>
                  <div className="serif" style={{ fontSize: 26, fontWeight: 600, color: a.color, fontVariantNumeric: 'tabular-nums' }}>{a.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ maxWidth: 1280, marginTop: 18, fontSize: 11, color: 'var(--text3)', fontStyle: 'italic' }}>
          Figures derived from the published DCH Planning Section project lists and sample corpus. Live aggregates replace these when
          connected to the docket database.
        </div>
      </div>
    </section>
  );
}
