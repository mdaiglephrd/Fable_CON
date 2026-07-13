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

export default function StatutesIndex() {
  const [kind, setKind] = useState<Kind>('all');
  const [liveOcga, setLiveOcga] = useState<IndexEntry[] | null>(null);
  const [liveRules, setLiveRules] = useState<IndexEntry[] | null>(null);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    api
      .getStatutes()
      .then((res) => {
        if (!alive) return;
        const toEntry = (s: import('../lib/types').StatuteListItem): IndexEntry => ({
          id: s.statuteId,
          num: s.citationLabel ?? s.statuteId,
          title: s.title ?? '',
        });
        setLiveOcga(res.items.filter((s) => s.kind === 'OCGA').map(toEntry));
        setLiveRules(res.items.filter((s) => s.kind !== 'OCGA').map(toEntry));
      })
      .catch(() => {
        /* fall back to the bundled index */
      });
    return () => {
      alive = false;
    };
  }, []);

  const ocga: IndexEntry[] =
    (!api.USE_FIXTURES && liveOcga) || STATUTE_TOC.map((s) => ({ id: s.id, num: s.num, title: s.title }));
  const rules: IndexEntry[] =
    (!api.USE_FIXTURES && liveRules) || RULE_LIST.map((r) => ({ id: r.id, num: r.num, title: r.title }));

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
      </div>
    </section>
  );
}
