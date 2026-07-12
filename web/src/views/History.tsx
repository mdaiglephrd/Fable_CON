/*
 * HISTORY (/history, /history/:docketId) — the chronological filing timeline
 * for one docket (GET /history/{docketId}), filterable by event type. Row
 * styling reuses the comp's HISTORY section (icon tile · kind · title ·
 * meta · right-aligned date). Without a docket in the URL the view opens on
 * the featured Riverstone docket and offers a picker over the docket roll.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import { DktBadge } from '../components/DktBadge';
import * as api from '../lib/api';
import { RECENT_DOCKETS } from '../lib/fixtures';
import { EVENT_TYPES } from '../lib/vocab';
import type { DocketEvent } from '../lib/types';

const DEFAULT_DOCKET = '2026007';

const TYPE_META: Record<string, { color: string; bg: string; d: string }> = {
  Filing: { color: '#3B82F6', bg: 'rgba(59,130,246,0.14)', d: 'M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4' },
  Brief: { color: 'var(--text2)', bg: 'var(--surface2)', d: 'M4 3 L4 13 L8 11 L12 13 L12 3 Z' },
  Order: { color: 'var(--accent-text)', bg: 'rgba(244,63,94,0.14)', d: 'M3 13 L3 3 M3 13 L13 13 M5 11 L7 8 L9 9 L12 5' },
  Opinion: { color: 'var(--accent-text)', bg: 'rgba(244,63,94,0.14)', d: 'M4 2 L4 14 M4 5 L12 5 L13 7 L12 9 L4 9' },
  Hearing: { color: '#F59E0B', bg: 'rgba(245,158,11,0.14)', d: 'M8 2 A6 6 0 1 0 8.01 2 M8 4 L8 8 L10.5 9.5' },
  Notice: { color: 'var(--text2)', bg: 'var(--surface2)', d: 'M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11' },
};

export default function History() {
  const { docketId } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const docket = docketId ?? DEFAULT_DOCKET;
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [events, setEvents] = useState<DocketEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setEvents(null);
    setError(null);
    api
      .getHistory(docket)
      .then((res) => alive && setEvents(res.items))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [docket]);

  const filtered = useMemo(
    () => (events ?? []).filter((e) => typeFilter === 'all' || e.type === typeFilter),
    [events, typeFilter],
  );

  const roll = RECENT_DOCKETS.find((d) => d.num === docket);
  const rollTitle = roll ? `${roll.facility} — ${roll.title}` : `Docket ${docket}`;

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'Docket History' }]}
        title="Docket History"
        titleSize={22}
        sub={
          <>
            Chronological filing timeline for{' '}
            <Link to={`/docket/${docket}`} className="text-link">
              {rollTitle}
            </Link>
            {roll?.county ? ` · ${roll.county} Co.` : ''}
          </>
        }
        right={
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              className="field-select"
              style={{ width: 'auto', padding: '7px 10px', fontSize: 12.5 }}
              value={RECENT_DOCKETS.some((d) => d.num === docket) ? docket : DEFAULT_DOCKET}
              onChange={(e) => navigate(`/history/${e.target.value}`)}
              aria-label="Choose docket"
            >
              {RECENT_DOCKETS.map((d) => (
                <option key={d.num} value={d.num ?? ''}>
                  {d.num} — {d.facility}
                </option>
              ))}
            </select>
            <button className="btn-outline" onClick={() => showToast('Exporting timeline as CSV… (connects to your firm system)')}>
              <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
                <path d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Export
            </button>
          </div>
        }
      >
        <div style={{ display: 'flex', gap: 2, marginTop: 16, border: '1px solid var(--border2)', borderRadius: 2, overflow: 'hidden', width: 'fit-content' }}>
          {['all', ...EVENT_TYPES].map((t, i) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              style={{
                padding: '6px 13px',
                fontSize: 11.5,
                fontWeight: typeFilter === t ? 600 : 400,
                background: typeFilter === t ? 'var(--border2)' : 'var(--surface2)',
                color: typeFilter === t ? 'var(--text)' : 'var(--text2)',
                borderLeft: i === 0 ? 'none' : '1px solid var(--border2)',
              }}
            >
              {t === 'all' ? 'All' : `${t}s`}
            </button>
          ))}
        </div>
      </PageHeader>

      <div style={{ padding: '24px 32px 60px' }}>
        <div style={{ maxWidth: 960 }}>
          {error && (
            <div className="card" style={{ padding: '40px 20px', textAlign: 'center', fontSize: 13, color: 'var(--text3)' }}>
              Timeline unavailable — {error}
            </div>
          )}
          {!error && events === null && <div style={{ padding: 40, color: 'var(--text3)', fontSize: 13 }}>Loading timeline…</div>}
          {events !== null && (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
                <div className="day-label" style={{ marginBottom: 0 }}>
                  {roll && <DktBadge type={roll.type} />} <span style={{ marginLeft: roll ? 6 : 0 }}>{filtered.length} events · newest first</span>
                </div>
                <Link to={`/docket/${docket}`} className="text-link" style={{ fontSize: 12 }}>
                  Open Docket View →
                </Link>
              </div>
              <div className="list-card">
                {filtered.map((e, i) => {
                  const meta = TYPE_META[e.type ?? ''] ?? TYPE_META.Notice;
                  return (
                    <div key={e.eventId ?? i} className="list-row row-hover" style={{ display: 'flex', alignItems: 'flex-start', gap: 14, padding: '13px 18px' }}>
                      <div
                        style={{
                          flexShrink: 0,
                          width: 34,
                          height: 34,
                          borderRadius: 2,
                          background: meta.bg,
                          color: meta.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          marginTop: 1,
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
                          <path d={meta.d} stroke="currentColor" strokeWidth={1.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                          <span style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: meta.color }}>
                            {e.type ?? 'Event'}
                          </span>
                          {e.court && <span style={{ fontSize: 10.5, color: 'var(--text3)' }}>· {e.court}</span>}
                        </div>
                        <div className="serif" style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
                          {e.description}
                        </div>
                        {e.actor && <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 3 }}>{e.actor}</div>}
                      </div>
                      <div style={{ flexShrink: 0, textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums' }}>{e.date}</span>
                        {e.entryId != null && (
                          <Link to={`/document/${e.entryId}`} className="text-link" style={{ fontSize: 11, fontWeight: 600 }}>
                            Open →
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
                {filtered.length === 0 && (
                  <div style={{ padding: '40px 20px', textAlign: 'center', fontSize: 12.5, color: 'var(--text3)' }}>
                    No {typeFilter === 'all' ? '' : `${typeFilter.toLowerCase()} `}events recorded on this docket.
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
