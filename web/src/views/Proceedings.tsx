/*
 * MY PROCEEDINGS LANDING (/proceedings) — hub cards (Alerts, History) plus
 * the list of tracked matters. From the comp's
 * <!-- MY PROCEEDINGS LANDING --> section. Fixture data: TRACKED_MATTERS
 * (a curated subset of the docket roll).
 */
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { SectionHead } from '../components/Shell';
import { TRACKED_MATTERS } from '../lib/fixtures';

export default function Proceedings() {
  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'My Proceedings' }]}
        title="My Proceedings"
        titleSize={26}
        sub="Your workspace — the matters you're tracking, the alerts watching them, and a running log of activity."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 1180 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 14, marginBottom: 32 }}>
            <Link to="/alerts" className="hub-card" style={{ padding: '18px 20px', gap: 16, alignItems: 'center' }}>
              <div className="hub-icon" style={{ width: 40, height: 40, position: 'relative' }}>
                <svg width="19" height="19" viewBox="0 0 16 16" aria-hidden>
                  <path d="M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11" stroke="currentColor" strokeWidth={1.3} fill="none" strokeLinejoin="round" />
                </svg>
                <span style={{ position: 'absolute', top: 6, right: 6, width: 7, height: 7, borderRadius: '50%', background: 'var(--brand-red)' }} />
              </div>
              <div style={{ flex: 1 }}>
                <div className="serif" style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)' }}>Alerts</div>
                <div style={{ fontSize: 12.5, color: 'var(--text2)', marginTop: 2 }}>3 active · docket watches, search alerts, and citation flags</div>
              </div>
              <span style={{ color: 'var(--text3)' }}>→</span>
            </Link>
            <Link to="/proceedings/history" className="hub-card" style={{ padding: '18px 20px', gap: 16, alignItems: 'center' }}>
              <div className="hub-icon neutral" style={{ width: 40, height: 40 }}>
                <svg width="19" height="19" viewBox="0 0 16 16" aria-hidden>
                  <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth={1.3} fill="none" />
                  <path d="M8 4 L8 8 L10.5 9.5" stroke="currentColor" strokeWidth={1.3} strokeLinecap="round" fill="none" />
                </svg>
              </div>
              <div style={{ flex: 1 }}>
                <div className="serif" style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)' }}>History</div>
                <div style={{ fontSize: 12.5, color: 'var(--text2)', marginTop: 2 }}>Orders, filings, status changes, and deadlines on your matters</div>
              </div>
              <span style={{ color: 'var(--text3)' }}>→</span>
            </Link>
          </div>

          <SectionHead title="Matters I'm tracking" right={<span>{TRACKED_MATTERS.length} matters</span>} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {TRACKED_MATTERS.map((m) => (
              <Link key={m.docketId} to={`/document/${m.caseId}`} className="hub-card" style={{ padding: '15px 18px', gap: 18, alignItems: 'center' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 3 }}>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--accent-text)', fontWeight: 600 }}>{m.num}</span>
                    <span className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>{m.name}</span>
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text2)' }}>{m.title}</div>
                </div>
                <div style={{ flexShrink: 0, textAlign: 'right', minWidth: 220 }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, fontWeight: 600, color: m.stageColor }}>
                    <span style={{ width: 7, height: 7, borderRadius: '50%', background: m.stageColor }} />
                    {m.stage}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--text3)', marginTop: 3 }}>{m.next}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
