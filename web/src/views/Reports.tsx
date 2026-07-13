/*
 * WEEKLY REPORTS (/reports) — a periodic digest: KPI strip, new filings,
 * determinations & orders issued, upcoming hearings/deadlines, and citator
 * alerts, with week tabs. From the comp's <!-- WEEKLY REPORTS --> section.
 *
 * Fixture mode renders three bundled weekly digests (comp's WEEKLY_REPORTS);
 * live mode groups GET /reports/events by section (common/vocab.py
 * REPORT_SECTIONS) into the same panels.
 */
import { useEffect, useState } from 'react';

import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';
import { findingColor } from '../lib/fixtures';
import { REPORT_SECTION_LABELS } from '../lib/vocab';
import type { ReportEvent } from '../lib/types';

interface FiledRow {
  badge: string;
  num: string;
  facility: string;
  title: string;
  date: string;
}
interface IssuedRow extends FiledRow {
  finding: string;
}
interface DeadlineRow {
  text: string;
  date: string;
  urgent: boolean;
}
interface AlertRow {
  text: string;
  color: string;
}
interface WeeklyReport {
  label: string;
  range: string;
  kpis: { filed: number; issued: number; hearings: number; alerts: number };
  filed: FiledRow[];
  issued: IssuedRow[];
  deadlines: DeadlineRow[];
  alerts: AlertRow[];
}

const WEEKLY_REPORTS: WeeklyReport[] = [
  {
    label: 'This week',
    range: 'Jun 22 – Jun 28, 2026',
    kpis: { filed: 6, issued: 4, hearings: 3, alerts: 2 },
    filed: [
      { badge: 'DET-EQT', num: 'DET-EQT2026062', facility: "Emory Saint Joseph's Hospital", title: 'Replacement of da Vinci Robot', date: 'Jun 24' },
      { badge: 'CON', num: '2026007', facility: 'Riverstone Imaging, LLC', title: 'Fixed 1.5T MRI — Bartow County (on remand)', date: 'Jun 23' },
      { badge: 'DET', num: 'DET2026006', facility: 'Piedmont Healthcare / Encompass Health', title: 'Joint Venture — Acute Rehab Hospital', date: 'Jun 23' },
      { badge: 'LNR-ASC', num: 'LNR-ASC2026003', facility: 'Atlanta South Gastroenterology, PC', title: 'Single Specialty ASC — Endoscopy', date: 'Jun 22' },
    ],
    issued: [
      { badge: 'CON', num: '2026002', facility: 'Three Rivers Imaging, LLC', title: 'Fixed MRI — Bartow County', finding: 'Approved', date: 'Jun 24' },
      { badge: 'CON', num: '2026004', facility: 'Magnolia Behavioral Health, LLC', title: '48 Psychiatric Beds', finding: 'Denied', date: 'Jun 23' },
      { badge: 'LNR-EQT', num: 'LNR-EQT2026008', facility: 'The Longstreet Clinic, PC', title: 'CT Scanner', finding: 'Issued', date: 'Jun 22' },
    ],
    deadlines: [
      { text: 'Riverstone — prehearing statement due', date: 'Jul 9, 2026', urgent: true },
      { text: 'Northridge — appellee brief due', date: 'Jul 21, 2026', urgent: false },
      { text: 'Magnolia — Commissioner review record due', date: 'Jul 14, 2026', urgent: false },
    ],
    alerts: [
      { text: 'Northridge Cardiac — new distinguishing citation flagged', color: '#F59E0B' },
      { text: '§ 31-6-44.1 substantial-evidence line — negative treatment', color: 'var(--accent-text)' },
    ],
  },
  {
    label: 'Last week',
    range: 'Jun 15 – Jun 21, 2026',
    kpis: { filed: 5, issued: 6, hearings: 2, alerts: 1 },
    filed: [
      { badge: 'DET-EQT', num: 'DET-EQT2026061', facility: 'Piedmont Mountainside Hospital', title: 'Single-Plane Vascular X-Ray System', date: 'Jun 18' },
      { badge: 'DET-EQT', num: 'DET-EQT2026060', facility: 'Piedmont Henry Hospital', title: 'Acquisition of Mobile MRI', date: 'Jun 17' },
      { badge: 'DET', num: 'DET2026005', facility: 'Emory University Hospital', title: 'Bed Reconfiguration — Neuro ICU', date: 'Jun 16' },
    ],
    issued: [
      { badge: 'DET', num: 'DET2026004', facility: 'Wellstar Douglas Hospital', title: 'Replacement of Cath Lab Suite', finding: 'Approved', date: 'Jun 20' },
      { badge: 'DET-ASC', num: 'DET-ASC2025007', facility: 'Hughston Surgical Center of Valdosta', title: 'Physician-Owned Multispecialty ASC', finding: 'Approved', date: 'Jun 18' },
    ],
    deadlines: [{ text: 'Riverstone — remand docketed at OSAH', date: 'Jun 26, 2026', urgent: false }],
    alerts: [{ text: 'Coastal Empire line — new citing opinion (followed)', color: '#10B981' }],
  },
  {
    label: 'Jun 8 – Jun 14',
    range: 'Jun 8 – Jun 14, 2026',
    kpis: { filed: 4, issued: 3, hearings: 1, alerts: 0 },
    filed: [
      { badge: 'DET-EQT', num: 'DET-EQT2026059', facility: 'Emory Hospital Warner Robins', title: 'MRI and CT Acquisition', date: 'Jun 12' },
      { badge: 'CON', num: '2026009', facility: 'Lakeview Psychiatric Pavilion, LLC', title: '40 Psychiatric Beds — Gwinnett', date: 'Jun 10' },
    ],
    issued: [{ badge: 'LNR-ASC', num: 'LNR-ASC2025014', facility: 'Center for Spine & Pain Medicine, PC', title: 'Single Specialty ASC — Pain Mgmt', finding: 'Issued', date: 'Jun 13' }],
    deadlines: [{ text: 'Statutes & Rules corpus updated', date: 'Jun 14, 2026', urgent: false }],
    alerts: [],
  },
];

function eventsToReport(events: ReportEvent[]): WeeklyReport {
  const bySection = new Map<string, ReportEvent[]>();
  for (const e of events) {
    const list = bySection.get(e.section ?? 'OTHER') ?? [];
    list.push(e);
    bySection.set(e.section ?? 'OTHER', list);
  }
  const filed = (bySection.get('NEW_APPLICATION') ?? []).map((e) => ({
    badge: 'CON',
    num: e.docketId ?? '',
    facility: e.facility ?? e.description ?? '',
    title: e.sectionHeading ?? e.description ?? '',
    date: e.reportDate ?? '',
  }));
  const issued = [...(bySection.get('APPROVED') ?? []), ...(bySection.get('DENIED') ?? [])].map((e) => ({
    badge: 'CON',
    num: e.docketId ?? '',
    facility: e.facility ?? e.description ?? '',
    title: e.sectionHeading ?? e.description ?? '',
    finding: e.section === 'DENIED' ? 'Denied' : 'Approved',
    date: e.reportDate ?? '',
  }));
  return {
    label: 'Live',
    range: 'Latest reported events',
    kpis: { filed: filed.length, issued: issued.length, hearings: 0, alerts: 0 },
    filed,
    issued,
    deadlines: [],
    alerts: [],
  };
}

export default function Reports() {
  const { showToast } = useToast();
  const [week, setWeek] = useState(0);
  const [live, setLive] = useState<WeeklyReport | null>(null);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    api
      .reportEvents({ limit: 100 })
      .then((res) => alive && setLive(eventsToReport(res.items)))
      .catch(() => alive && setLive(null));
    return () => {
      alive = false;
    };
  }, []);

  const tabs = api.USE_FIXTURES ? WEEKLY_REPORTS : live ? [live] : [];
  const report = tabs[Math.min(week, tabs.length - 1)];

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Weekly Reports' }]}
        title="Weekly Reports"
        titleSize={26}
        sub={report ? <>Digest for <strong style={{ color: 'var(--text)' }}>{report.range}</strong> — CON activity across the DCH Planning Section and the courts.</> : 'Loading digest…'}
        right={
          <button className="btn-outline" onClick={() => showToast('Exporting report as PDF… (connects to your firm system)')}>
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden>
              <path d="M4 6 L4 2 L12 2 L12 6 M4 11 L2 11 L2 6 L14 6 L14 11 L12 11 M4 9 L12 9 L12 14 L4 14 Z" stroke="currentColor" strokeWidth={1.3} fill="none" strokeLinejoin="round" />
            </svg>
            Export PDF
          </button>
        }
      >
        {tabs.length > 1 && (
          <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
            {tabs.map((w, i) => (
              <button
                key={w.label}
                onClick={() => setWeek(i)}
                style={{
                  textAlign: 'left',
                  padding: '8px 16px',
                  border: `1.5px solid ${week === i ? 'var(--brand-red)' : 'var(--border2)'}`,
                  borderRadius: 2,
                  background: week === i ? 'rgba(244,63,94,0.14)' : 'var(--surface2)',
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 600, color: week === i ? 'var(--accent-text)' : 'var(--text)' }}>{w.label}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{w.range}</div>
              </button>
            ))}
          </div>
        )}
      </PageHeader>

      <div style={{ padding: '26px 32px 60px' }}>
        {!report && <div style={{ padding: 40, color: 'var(--text3)', fontSize: 13 }}>No report events available.</div>}
        {report && (
          <div style={{ maxWidth: 1180 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 26 }}>
              {(
                [
                  ['New filings', report.kpis.filed, '#F59E0B'],
                  ['Determinations issued', report.kpis.issued, '#10B981'],
                  ['Hearings & deadlines', report.kpis.hearings, '#3B82F6'],
                  ['Citator alerts', report.kpis.alerts, '#8E1B1F'],
                ] as [string, number, string][]
              ).map(([label, value, color]) => (
                <div key={label} className="card" style={{ borderLeft: `3px solid ${color}`, padding: '16px 18px' }}>
                  <div className="serif" style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>{value}</div>
                  <div className="label-upper" style={{ marginTop: 4, letterSpacing: 1 }}>{label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <div className="card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '12px 18px', borderBottom: '2px solid #F59E0B', background: 'rgba(245,158,11,0.08)' }}>
                  <h2 className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: 0 }}>New filings this week</h2>
                </div>
                {report.filed.map((f) => (
                  <div key={f.num} className="list-row" style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 18px' }}>
                    <div style={{ flexShrink: 0, width: 70 }}>
                      <DktBadge type={f.badge} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600, lineHeight: 1.3 }}>{f.facility}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 1 }}>{f.title}</div>
                    </div>
                    <span style={{ flexShrink: 0, fontSize: 11, color: 'var(--text3)' }}>{f.date}</span>
                  </div>
                ))}
                {report.filed.length === 0 && <div style={{ padding: '20px 18px', fontSize: 12, color: 'var(--text3)' }}>No new filings.</div>}
              </div>

              <div className="card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '12px 18px', borderBottom: '2px solid #10B981', background: 'rgba(16,185,129,0.14)' }}>
                  <h2 className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: 0 }}>Determinations &amp; orders issued</h2>
                </div>
                {report.issued.map((d) => (
                  <div key={d.num} className="list-row" style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 18px' }}>
                    <div style={{ flexShrink: 0, width: 70 }}>
                      <DktBadge type={d.badge} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600, lineHeight: 1.3 }}>{d.facility}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 1 }}>{d.title}</div>
                    </div>
                    <div style={{ flexShrink: 0, textAlign: 'right' }}>
                      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: findingColor(d.finding) }}>{d.finding}</div>
                      <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{d.date}</div>
                    </div>
                  </div>
                ))}
                {report.issued.length === 0 && <div style={{ padding: '20px 18px', fontSize: 12, color: 'var(--text3)' }}>No determinations issued.</div>}
              </div>

              <div className="card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '12px 18px', borderBottom: '2px solid #3B82F6', background: 'rgba(59,130,246,0.14)' }}>
                  <h2 className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: 0 }}>Upcoming hearings &amp; deadlines</h2>
                </div>
                {report.deadlines.map((dl, i) => (
                  <div key={i} className="list-row" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 18px' }}>
                    <span style={{ flexShrink: 0, width: 9, height: 9, borderRadius: '50%', background: dl.urgent ? 'var(--brand-red)' : '#C9C0AD' }} />
                    <div style={{ flex: 1, fontSize: 13, color: 'var(--text)', lineHeight: 1.4 }}>{dl.text}</div>
                    <span style={{ flexShrink: 0, fontSize: 11.5, color: 'var(--text2)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{dl.date}</span>
                  </div>
                ))}
                {report.deadlines.length === 0 && <div style={{ padding: '20px 18px', fontSize: 12, color: 'var(--text3)' }}>No deadlines this week.</div>}
              </div>

              <div className="card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '12px 18px', borderBottom: '2px solid #8E1B1F', background: 'rgba(244,63,94,0.14)' }}>
                  <h2 className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: 0 }}>Citator alerts</h2>
                </div>
                {report.alerts.length > 0 ? (
                  report.alerts.map((al, i) => (
                    <div key={i} className="list-row" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 18px' }}>
                      <span style={{ flexShrink: 0, width: 9, height: 9, borderRadius: '50%', background: al.color }} />
                      <div style={{ flex: 1, fontSize: 13, color: 'var(--text)', lineHeight: 1.4 }}>{al.text}</div>
                      <span style={{ flexShrink: 0, color: 'var(--text3)' }}>→</span>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '24px 18px', textAlign: 'center', fontSize: 12.5, color: 'var(--text3)' }}>No citator alerts this week.</div>
                )}
              </div>
            </div>
            <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text3)' }}>
              Section codes follow {Object.keys(REPORT_SECTION_LABELS).length} lifecycle categories from the weekly CON Tracking Report.
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
