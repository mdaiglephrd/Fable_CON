/*
 * ANALYTICS & TOOLS LANDING (/tools) — KPI strip + hub cards linking Stats,
 * Calculator, Map, Reports. From the comp's
 * <!-- ANALYTICS & TOOLS LANDING --> section.
 */
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';

const KPIS = [
  { value: '12,847', label: 'Sources indexed', color: 'var(--text)' },
  { value: '61%', label: 'Approval rate', color: '#10B981' },
  { value: '218', label: 'Active dockets', color: 'var(--text)' },
  { value: '34%', label: 'Reversed on appeal', color: '#F59E0B' },
];

const CARDS = [
  {
    to: '/stats',
    accent: '#8E1B1F',
    icon: 'M3 13 L3 3 M3 13 L13 13 M5 11 L5 7 M8 11 L8 5 M11 11 L11 9',
    accentIcon: true,
    title: 'Outcome Statistics',
    desc: 'Grant/deny rates by service, forum, year, and docket type — with appeal reversal trends.',
  },
  {
    to: '/calculator',
    accent: '#F59E0B',
    icon: 'M4 2 L12 2 L12 14 L4 14 Z M6 5 L10 5 M6 8 L6 8 M8 8 L8 8 M6 11 L6 11 M8 11 L8 11',
    accentIcon: false,
    iconColor: '#10B981',
    iconBg: 'rgba(245,158,11,0.14)',
    title: 'Deadline Calculator',
    desc: 'Project every downstream date from a triggering event under §§ 31-6-44 and 44.1.',
  },
  {
    to: '/compare',
    accent: '#3B82F6',
    icon: 'M4 3 L4 13 L8 11 L12 13 L12 3 Z',
    accentIcon: false,
    iconColor: '#3B82F6',
    iconBg: 'rgba(59,130,246,0.14)',
    title: 'Compare Decisions',
    desc: 'Side-by-side comparison of two determinations across caption, outcome, and treatment.',
  },
  {
    to: '/map',
    accent: '#8B5CF6',
    icon: 'M2 4 L6 2 L10 4 L14 2 L14 12 L10 14 L6 12 L2 14 Z M6 2 L6 12 M10 4 L10 14',
    accentIcon: false,
    iconColor: '#8B5CF6',
    iconBg: 'rgba(245,158,11,0.10)',
    title: 'Service-Area Map',
    desc: 'Filings and outcomes mapped by county and planning-service area.',
  },
  {
    to: '/reports',
    accent: '#8E1B1F',
    icon: 'M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4 M5 7 L11 7 M5 10 L11 10',
    accentIcon: true,
    title: 'Weekly Reports',
    desc: "The week's new filings, issued determinations, upcoming deadlines, and citator alerts.",
  },
];

export default function Tools() {
  const navigate = useNavigate();
  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools' }]}
        title="Analytics & Tools"
        titleSize={26}
        sub="Outcome analytics, practice utilities, and workflow tools built on the full Georgia CON corpus."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 1180 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 30 }}>
            {KPIS.map((k) => (
              <div key={k.label} className="card" style={{ padding: '16px 18px' }}>
                <div className="serif" style={{ fontSize: 26, fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
                <div className="label-upper" style={{ marginTop: 4, letterSpacing: 1 }}>{k.label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 14 }}>
            {CARDS.map((c) => (
              <button
                key={c.to}
                className="hub-card"
                onClick={() => navigate(c.to)}
                style={{ borderTop: `3px solid ${c.accent}`, borderRadius: '0 0 2px 2px', padding: 20, flexDirection: 'column', gap: 9, minHeight: 148, alignItems: 'flex-start' }}
              >
                <div className={`hub-icon${c.accentIcon ? '' : ' neutral'}`} style={{ width: 36, height: 36, ...(c.iconColor ? { color: c.iconColor } : {}), ...(c.iconBg ? { background: c.iconBg } : {}) }}>
                  <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden>
                    <path d={c.icon} stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>{c.title}</div>
                <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.45 }}>{c.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
