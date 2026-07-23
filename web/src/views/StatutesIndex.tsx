/*
 * STATUTES & RULES INDEX (/statutes) — browsable O.C.G.A. Title 31 Ch. 6
 * sections and Ga. Comp. R. & Regs. 111-2-2 rules, with kind tabs
 * (All / O.C.G.A. / DCH Rules). Layout from the comp's STATUTES & RULES
 * INDEX section; live mode reads GET /statutes?kind=.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import * as api from '../lib/api';
import { RULE_LIST, STATUTE_TOC } from '../lib/statutesData';

type Kind = 'all' | 'OCGA' | 'RULE';

interface IndexEntry {
  id: string;
  num: string;
  title: string;
}

const KIND_TABS: { id: Kind; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'OCGA', label: 'O.C.G.A.' },
  { id: 'RULE', label: 'DCH Rules' },
];

/** Explicit tri-state for GET /statutes — loading and error must never be
 * silently rendered as the bundled STATUTE_TOC/RULE_LIST fixture index. */
type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; ocga: IndexEntry[]; rules: IndexEntry[] };

export default function StatutesIndex() {
  const [kind, setKind] = useState<Kind>('all');
  const [liveState, setLiveState] = useState<LoadState>({ status: 'loading' });
  const [retryTick, setRetryTick] = useState(0);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    setLiveState({ status: 'loading' });
    api
      .getStatutes()
      .then((res) => {
        if (!alive) return;
        const toEntry = (s: import('../lib/types').StatuteListItem): IndexEntry => ({
          id: s.statuteId,
          num: s.citationLabel ?? s.statuteId,
          title: s.title ?? '',
        });
        setLiveState({
          status: 'ok',
          ocga: res.items.filter((s) => s.kind === 'OCGA').map(toEntry),
          rules: res.items.filter((s) => s.kind !== 'OCGA').map(toEntry),
        });
      })
      .catch((err: Error) => {
        if (alive) setLiveState({ status: 'error', message: err.message });
      });
    return () => {
      alive = false;
    };
  }, [retryTick]);

  const retry = () => setRetryTick((t) => t + 1);

  const ocga: IndexEntry[] = api.USE_FIXTURES
    ? STATUTE_TOC.map((s) => ({ id: s.id, num: s.num, title: s.title }))
    : liveState.status === 'ok'
      ? liveState.ocga
      : [];
  const rules: IndexEntry[] = api.USE_FIXTURES
    ? RULE_LIST.map((r) => ({ id: r.id, num: r.num, title: r.title }))
    : liveState.status === 'ok'
      ? liveState.rules
      : [];

  const showOcga = kind !== 'RULE';
  const showRules = kind !== 'OCGA';

  const column = (entries: IndexEntry[], mono: string) =>
    entries.map((s) => (
      <Link
        key={s.id}
        to={`/statute/${s.id}`}
        className="row-hover list-row"
        style={{ display: 'flex', alignItems: 'baseline', gap: 14, width: '100%', padding: '12px 22px' }}
      >
        <span className="mono" style={{ flexShrink: 0, width: 96, fontSize: 12.5, color: mono, fontWeight: 500 }}>
          {s.num}
        </span>
        <span style={{ flex: 1, fontSize: 13.5, color: 'var(--text)', lineHeight: 1.4 }}>{s.title}</span>
        <span style={{ flexShrink: 0, color: 'var(--text3)' }}>→</span>
      </Link>
    ));

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Knowledge Base', to: '/kb' }, { label: 'Statutes & Rules' }]}
        title="Statutes & Rules"
        titleSize={26}
        sub="The full statutory and regulatory framework for Georgia CON — O.C.G.A. Title 31, Chapter 6 and Ga. Comp. R. & Regs. Chapter 111-2-2. Select a section to open the annotated reader."
      >
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          {KIND_TABS.map((t) => (
            <button key={t.id} className={`chip-tab${kind === t.id ? ' active' : ''}`} onClick={() => setKind(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </PageHeader>

      <div style={{ padding: '28px 32px 60px' }}>
        {!api.USE_FIXTURES && liveState.status === 'loading' && (
          <div style={{ maxWidth: 1120, fontSize: 13, color: 'var(--text3)', padding: '20px 0' }}>Loading statutes &amp; rules…</div>
        )}
        {!api.USE_FIXTURES && liveState.status === 'error' && (
          <div className="card" style={{ maxWidth: 1120, padding: '18px 20px', marginBottom: 20 }}>
            <div style={{ fontSize: 13.5, color: 'var(--text)', marginBottom: 10 }}>
              Statutes &amp; rules unavailable — {liveState.message}
            </div>
            <button className="btn-outline" onClick={retry}>
              Retry
            </button>
          </div>
        )}
        {(api.USE_FIXTURES || liveState.status === 'ok') && (
        <div
          style={{
            maxWidth: 1120,
            display: 'grid',
            gridTemplateColumns: showOcga && showRules ? '1fr 1fr' : 'minmax(0, 560px)',
            gap: 24,
          }}
        >
          {showOcga && (
            <div className="list-card" style={{ overflow: 'hidden' }}>
              <div style={{ padding: '16px 22px', borderBottom: '1px solid var(--surface2)' }}>
                <div className="label-upper" style={{ color: 'var(--text2)', letterSpacing: 1.4, marginBottom: 2 }}>
                  O.C.G.A. Title 31 · Chapter 6
                </div>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
                  State Health Planning — Certificate of Need
                </div>
              </div>
              {column(ocga, 'var(--accent-text)')}
            </div>
          )}
          {showRules && (
            <div className="list-card" style={{ overflow: 'hidden', alignSelf: 'start' }}>
              <div style={{ padding: '16px 22px', borderBottom: '1px solid var(--surface2)', background: '#3B82F6' }}>
                <div className="label-upper" style={{ color: '#E4ECF1', letterSpacing: 1.4, marginBottom: 2 }}>
                  Ga. Comp. R. &amp; Regs. Chapter 111-2-2
                </div>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: '#FFFFFF' }}>
                  Rules of the Department of Community Health
                </div>
              </div>
              {column(rules, '#3B82F6')}
            </div>
          )}
        </div>
        )}
      </div>
    </section>
  );
}
