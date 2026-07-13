/*
 * DEADLINE CALCULATOR (/calculator) — docket-family + trigger-event +
 * date inputs producing the computed regulatory deadlines. Layout from the
 * comp's <!-- DEADLINE CALCULATOR --> section. POST /deadlines/calculate
 * when live; fixture mode computes from lib/deadlineRules.ts (the local
 * port of common/deadline_rules.py).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import * as api from '../lib/api';
import { REFERENCE_NOW } from '../lib/docketEngine';
import { triggerEventsFor } from '../lib/deadlineRules';
import { DOCKET_FAMILIES } from '../lib/vocab';
import { DOCKET_TYPES } from '../lib/fixtures';
import type { ComputedDeadline } from '../lib/types';

const ACCENTS: Record<string, string> = {
  '31-6-44': '#8E1B1F',
  '31-6-44.1': '#8E1B1F',
  '31-6-2': '#F59E0B',
  '50-13-19': '#3B82F6',
};

function fmtLong(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default function Calculator() {
  const [family, setFamily] = useState<string>('CON');
  const triggers = useMemo(() => triggerEventsFor(family), [family]);
  const [trigger, setTrigger] = useState('Letter of determination');
  const [date, setDate] = useState('2026-06-01');
  const [deadlines, setDeadlines] = useState<ComputedDeadline[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Keep the trigger valid when the family changes the rule set.
  useEffect(() => {
    if (!triggers.includes(trigger)) setTrigger(triggers[0] ?? '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [family]);

  useEffect(() => {
    if (!trigger || !date) {
      setDeadlines(null);
      return;
    }
    let alive = true;
    setError(null);
    api
      .calculateDeadlines({ family, triggerEvent: trigger, date })
      .then((res) => alive && setDeadlines(res.deadlines))
      .catch((e: Error) => {
        if (alive) {
          setDeadlines(null);
          setError(e.message);
        }
      });
    return () => {
      alive = false;
    };
  }, [family, trigger, date]);

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Deadline Calculator' }]}
        title="CON Deadline & Appeal-Window Calculator"
        sub={
          <>
            Computes statutory windows under{' '}
            <Link to="/statute/31-6-43" className="text-link">O.C.G.A. § 31-6-43</Link>,{' '}
            <Link to="/statute/31-6-44" className="text-link">§ 31-6-44</Link>, and{' '}
            <Link to="/statute/31-6-44.1" className="text-link">§ 31-6-44.1</Link>
          </>
        }
      />

      <div style={{ padding: 32 }}>
        <div style={{ maxWidth: 980, display: 'grid', gridTemplateColumns: '300px 1fr', gap: 28 }}>
          {/* Inputs */}
          <div className="card" style={{ padding: 22, alignSelf: 'start' }}>
            <h2 className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, margin: '0 0 16px', paddingBottom: 10, borderBottom: '2px solid var(--border2)' }}>
              Trigger event
            </h2>
            <label className="field-label">Docket family</label>
            <select className="field-select" style={{ fontSize: 13, marginBottom: 18 }} value={family} onChange={(e) => setFamily(e.target.value)}>
              {DOCKET_FAMILIES.map((f) => (
                <option key={f} value={f}>
                  {f} — {DOCKET_TYPES[f]?.full ?? f}
                </option>
              ))}
            </select>
            <label className="field-label">Event type</label>
            <select className="field-select" style={{ fontSize: 13, marginBottom: 18 }} value={trigger} onChange={(e) => setTrigger(e.target.value)}>
              {triggers.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <label className="field-label">Event date</label>
            <input className="field-input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            <div style={{ marginTop: 18, padding: '12px 14px', background: 'var(--page-bg)', border: '1px solid var(--surface2)', borderRadius: 2, fontSize: 11.5, color: 'var(--text2)', lineHeight: 1.5 }}>
              Offsets follow the docket-engine copy of the statutory windows; DET subtypes (DET-EQT, DET-ASC, LNR-·) share the DET rules.
              Verify against the official record.
            </div>
          </div>

          {/* Output */}
          <div>
            {error && (
              <div className="card" style={{ padding: '18px 20px', fontSize: 12.5, color: 'var(--status-denied)' }}>
                Calculation unavailable — {error}
              </div>
            )}
            {!error && (deadlines?.length ?? 0) === 0 && (
              <div className="card" style={{ padding: '48px 20px', textAlign: 'center', fontSize: 13, color: 'var(--text3)' }}>
                {date ? 'No deadline rules attach to this trigger for the selected family.' : 'Pick an event date to project the downstream deadlines.'}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {(deadlines ?? []).map((d, i) => {
                const accent = ACCENTS[d.basisStatute ?? ''] ?? '#F59E0B';
                const due = new Date(`${d.dueDate}T00:00:00`);
                const diff = Math.round((due.getTime() - REFERENCE_NOW.getTime()) / 86400000);
                const daysText = diff < 0 ? `${Math.abs(diff)} days ago` : diff === 0 ? 'Today' : `${diff} days remaining`;
                const daysColor = diff < 0 ? '#8E1B1F' : diff <= 14 ? '#F59E0B' : '#10B981';
                return (
                  <div key={i} className="card" style={{ borderLeft: `4px solid ${accent}`, padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {d.basisStatute && (
                        <Link to={`/statute/${d.basisStatute}`} className="label-upper text-link" style={{ fontSize: 10, letterSpacing: 1.2, fontWeight: 700 }}>
                          O.C.G.A. § {d.basisStatute}
                        </Link>
                      )}
                      <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginTop: 3 }}>{d.label}</div>
                      {d.description && <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 3, lineHeight: 1.5 }}>{d.description}</div>}
                    </div>
                    <div style={{ flexShrink: 0, textAlign: 'right' }}>
                      <div className="serif" style={{ fontSize: 19, fontWeight: 600, color: accent, whiteSpace: 'nowrap' }}>{fmtLong(d.dueDate)}</div>
                      <div style={{ fontSize: 11, color: daysColor, marginTop: 3, fontWeight: 600 }}>{daysText}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            {(deadlines?.length ?? 0) > 0 && (
              <div style={{ marginTop: 16, fontSize: 11, color: 'var(--text3)', fontStyle: 'italic' }}>
                “Days remaining” is measured against the console’s reference date (Jun 25, 2026). Deadlines falling on weekends or state
                holidays roll per the applicable rule — confirm before filing.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
