/*
 * PROCEEDINGS · HISTORY (/proceedings/history) — a running log of orders,
 * filings, alerts, status changes, and deadlines across the tracked
 * matters, filterable by kind. From the comp's
 * <!-- MY PROCEEDINGS · HISTORY --> section.
 */
import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { MATTER_HISTORY_GROUPS, type MatterHistItem } from '../lib/fixtures';

const TABS: { id: MatterHistItem['kind'] | 'all'; label: string }[] = [
  { id: 'all', label: 'All activity' },
  { id: 'order', label: 'Orders' },
  { id: 'filing', label: 'Filings' },
  { id: 'alert', label: 'Alerts' },
  { id: 'deadline', label: 'Deadlines' },
];

export default function MatterHistory() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<string>('all');

  const groups = useMemo(
    () =>
      MATTER_HISTORY_GROUPS.map((g) => ({ ...g, items: g.items.filter((it) => tab === 'all' || it.kind === tab) })).filter(
        (g) => g.items.length > 0,
      ),
    [tab],
  );

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'My Proceedings', to: '/proceedings' }, { label: 'History' }]}
        title="Proceedings Activity"
        titleSize={26}
        sub="A running log of orders, filings, status changes, and deadlines on the matters you track."
        right={
          <div style={{ display: 'flex', gap: 0, border: '1px solid var(--border2)', borderRadius: 2, overflow: 'hidden' }}>
            {TABS.map((t, i) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  padding: '7px 14px',
                  fontSize: 12.5,
                  fontWeight: tab === t.id ? 600 : 400,
                  background: tab === t.id ? 'var(--brand-red)' : 'var(--surface2)',
                  color: tab === t.id ? '#FFFFFF' : 'var(--text2)',
                  borderLeft: i === 0 ? 'none' : '1px solid var(--border2)',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        }
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 900 }}>
          {groups.map((g) => (
            <div key={g.day} style={{ marginBottom: 26 }}>
              <div className="day-label">{g.day}</div>
              <div className="list-card" style={{ overflow: 'hidden' }}>
                {g.items.map((it, i) => (
                  <button
                    key={i}
                    className="list-row row-hover"
                    onClick={() => navigate(it.to)}
                    style={{ display: 'flex', alignItems: 'flex-start', gap: 14, width: '100%', textAlign: 'left', padding: '14px 18px' }}
                  >
                    <span
                      style={{
                        flexShrink: 0,
                        marginTop: 1,
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '3px 9px',
                        fontSize: 10,
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: 0.5,
                        color: '#FFFFFF',
                        background: it.tagColor,
                        borderRadius: 1,
                        minWidth: 64,
                        justifyContent: 'center',
                      }}
                    >
                      {it.tag}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13.5, color: 'var(--text)', lineHeight: 1.45 }}>{it.text}</div>
                      <div style={{ fontSize: 12, color: 'var(--accent-text)', fontWeight: 500, marginTop: 3 }}>{it.matter}</div>
                    </div>
                    <span style={{ flexShrink: 0, fontSize: 11.5, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums' }}>{it.time}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
          {groups.length === 0 && (
            <div style={{ padding: '48px 20px', textAlign: 'center', fontSize: 13, color: 'var(--text3)' }}>
              No {tab === 'all' ? '' : `${tab} `}activity recorded.
            </div>
          )}
          <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 8 }}>
            See also <Link to="/proceedings" className="text-link">My Proceedings</Link> for the tracked-matter list.
          </div>
        </div>
      </div>
    </section>
  );
}
