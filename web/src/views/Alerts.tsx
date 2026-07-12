/*
 * ALERTS (/alerts) — saved-search / docket-watch management: filter tabs,
 * alert cards (type pill, latest activity, frequency), a New-alert create
 * form, and deactivate. Card styling from the comp's <!-- ALERTS --> section;
 * fixture mode keeps the list in memory (seeded with the comp's three
 * alerts), live mode uses the /alerts CRUD.
 */
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';

import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { renderSegs } from '../lib/segments';
import type { SavedAlert } from '../lib/types';

const ALERT_TYPES = [
  { id: 'Docket Watch', desc: 'Track any docket for new filings and decisions.', color: 'var(--accent-text)', bg: 'rgba(244,63,94,0.14)' },
  { id: 'Search Alert', desc: 'Notify when new decisions match a saved query.', color: '#F59E0B', bg: 'rgba(245,158,11,0.14)' },
  { id: 'Statute Watch', desc: 'Alert when a section or rule is amended.', color: '#3B82F6', bg: 'rgba(59,130,246,0.14)' },
  { id: 'Citation Alert', desc: 'New citing references, filtered by treatment.', color: '#10B981', bg: 'rgba(16,185,129,0.14)' },
];

const FREQUENCIES = ['Immediate', 'Daily digest', 'Weekly'];

function typeMeta(alertType?: string) {
  return ALERT_TYPES.find((t) => t.id === alertType) ?? ALERT_TYPES[1];
}

export default function Alerts() {
  const { showToast } = useToast();
  const [alerts, setAlerts] = useState<SavedAlert[] | null>(null);
  const [tab, setTab] = useState('all');
  const [creating, setCreating] = useState(false);
  const [newType, setNewType] = useState('Docket Watch');
  const [newName, setNewName] = useState('');
  const [newQuery, setNewQuery] = useState('');
  const [newFreq, setNewFreq] = useState('Immediate');

  const refresh = useCallback(() => {
    api
      .listAlerts()
      .then((res) => setAlerts(res.items))
      .catch(() => setAlerts([]));
  }, []);
  useEffect(refresh, [refresh]);

  const visible = useMemo(
    () => (alerts ?? []).filter((a) => tab === 'all' || (a.alertType ?? 'Search Alert') === tab),
    [alerts, tab],
  );
  const activeCount = (alerts ?? []).filter((a) => a.active !== false).length;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      showToast('Give the alert a name first');
      return;
    }
    const created = await api.createAlert({
      name: newName.trim(),
      query: newQuery.trim() || undefined,
      scope: 'all',
      frequency: newFreq,
    });
    // Fixture-mode presentation fields for the new card.
    created.alertType = newType;
    created.description = newQuery.trim() ? `Watching: ${newQuery.trim()}` : 'Watching for new activity.';
    showToast(`Alert "${newName.trim()}" created`, 'success');
    setCreating(false);
    setNewName('');
    setNewQuery('');
    refresh();
  };

  const deactivate = async (a: SavedAlert) => {
    await api.deleteAlert(a.alertId);
    showToast(`Alert "${a.name}" deactivated`);
    refresh();
  };

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'My Proceedings', to: '/proceedings' }, { label: 'Alerts' }]}
        title="Alerts"
        titleSize={22}
        sub="Track dockets, cases, search queries, and statute changes."
        right={
          <button className="btn-primary" onClick={() => setCreating((v) => !v)}>
            <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
              <path d="M8 3 L8 13 M3 8 L13 8" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
            </svg>
            {creating ? 'Close' : 'New alert'}
          </button>
        }
      >
        <div style={{ display: 'flex', gap: 4, marginTop: 16, flexWrap: 'wrap' }}>
          <button className={`line-tab${tab === 'all' ? ' active' : ''}`} onClick={() => setTab('all')} style={{ padding: '7px 14px', fontSize: 12.5 }}>
            All ({activeCount})
          </button>
          {ALERT_TYPES.map((t) => (
            <button key={t.id} className={`line-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)} style={{ padding: '7px 14px', fontSize: 12.5 }}>
              {t.id}s
            </button>
          ))}
        </div>
      </PageHeader>

      <div style={{ padding: '24px 32px 60px' }}>
        <div style={{ maxWidth: 960 }}>
          {/* Create form */}
          {creating && (
            <form onSubmit={submit} className="card" style={{ padding: '20px 22px', marginBottom: 18, borderLeft: '3px solid var(--brand-red)' }}>
              <div className="label-upper" style={{ color: 'var(--accent-text)', letterSpacing: 1.4, marginBottom: 14 }}>New alert</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10, marginBottom: 16 }}>
                {ALERT_TYPES.map((t) => {
                  const selected = newType === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setNewType(t.id)}
                      style={{
                        textAlign: 'left',
                        padding: '12px 14px',
                        borderRadius: 2,
                        background: selected ? t.bg : 'var(--page-bg)',
                        boxShadow: selected ? `inset 0 0 0 1.5px ${t.color}` : 'inset 0 0 0 1px var(--surface2)',
                      }}
                    >
                      <div style={{ fontSize: 12.5, fontWeight: 700, color: selected ? t.color : 'var(--text)', marginBottom: 3 }}>{t.id}</div>
                      <div style={{ fontSize: 11, color: 'var(--text2)', lineHeight: 1.4 }}>{t.desc}</div>
                    </button>
                  );
                })}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr', gap: 14, marginBottom: 16 }}>
                <div>
                  <label className="field-label">Alert name</label>
                  <input className="field-input" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Riverstone Imaging remand watch" />
                </div>
                <div>
                  <label className="field-label">Docket / query / section</label>
                  <input className="field-input" value={newQuery} onChange={(e) => setNewQuery(e.target.value)} placeholder='e.g. CON 2026007 — or — "MRI need methodology"' />
                </div>
                <div>
                  <label className="field-label">Frequency</label>
                  <select className="field-select" value={newFreq} onChange={(e) => setNewFreq(e.target.value)}>
                    {FREQUENCIES.map((f) => (
                      <option key={f}>{f}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 14, borderTop: '1px solid var(--surface2)' }}>
                <button type="button" className="btn-outline" onClick={() => setCreating(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create alert
                </button>
              </div>
            </form>
          )}

          {/* Alert cards */}
          {alerts === null && <div style={{ padding: 40, color: 'var(--text3)', fontSize: 13 }}>Loading alerts…</div>}
          {visible.map((a) => {
            const meta = typeMeta(a.alertType);
            const inactive = a.active === false;
            return (
              <div key={a.alertId} className="card" style={{ padding: '18px 22px', marginBottom: 12, opacity: inactive ? 0.55 : 1 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
                      <span
                        style={{
                          fontSize: 9,
                          fontWeight: 700,
                          letterSpacing: 1.2,
                          textTransform: 'uppercase',
                          color: meta.color,
                          background: meta.bg,
                          padding: '3px 7px',
                          borderRadius: 1,
                        }}
                      >
                        {a.alertType ?? 'Alert'}
                      </span>
                      {!!a.newCount && !inactive && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 600, color: 'var(--accent-text)' }}>
                          <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--brand-red)', display: 'inline-block' }} />
                          {a.newCount} new
                        </span>
                      )}
                      {inactive && <span className="label-upper" style={{ fontSize: 9.5 }}>Inactive</span>}
                    </div>
                    <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 4, lineHeight: 1.3 }}>{a.name}</div>
                    {a.description && <div style={{ fontSize: 12.5, color: 'var(--text2)', marginBottom: 10 }}>{a.description}</div>}
                    {a.latest && !inactive && (
                      <div
                        style={{
                          padding: '10px 14px',
                          background: 'var(--page-bg)',
                          border: '1px solid var(--surface2)',
                          borderLeft: `3px solid ${meta.color}`,
                          borderRadius: 2,
                          fontSize: 12.5,
                          lineHeight: 1.45,
                          color: 'var(--text2)',
                        }}
                      >
                        <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1, marginBottom: 4 }}>Latest activity</div>
                        {renderSegs(a.latest)}
                      </div>
                    )}
                  </div>
                  <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
                    <div style={{ fontSize: 11, color: 'var(--text3)' }}>{a.frequency ?? '—'}</div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn-outline" style={{ padding: '5px 10px', fontSize: 11.5 }} onClick={() => showToast('Opening alert editor…')}>
                        Edit
                      </button>
                      {!inactive && (
                        <button className="btn-outline" style={{ padding: '5px 10px', fontSize: 11.5 }} onClick={() => void deactivate(a)}>
                          Deactivate
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {alerts !== null && visible.length === 0 && (
            <div className="card" style={{ padding: '48px 20px', textAlign: 'center', fontSize: 13, color: 'var(--text3)' }}>
              No {tab === 'all' ? '' : `${tab.toLowerCase()} `}alerts yet — create one with “New alert”.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
