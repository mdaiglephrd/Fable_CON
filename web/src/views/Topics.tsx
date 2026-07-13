/*
 * TOPICS (/topics, /topics/:topicId) — the CON key-number taxonomy: an
 * expandable tree (left) and the active key's detail (authorities, sub-keys,
 * headnoted cases). Structure from the comp's <!-- TOPICS --> section.
 *
 * Fixture mode renders lib/taxonomy.ts; live mode folds GET /topics +
 * GET /topics/{id} into the same shapes.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import {
  keyDetail,
  resolveTopicParam,
  TAXONOMY,
  type KeyDetail,
  type TaxonomyTopic,
} from '../lib/taxonomy';

/** Fold the live GET /topics tree into the fixture taxonomy shape. */
function liveTreeToTaxonomy(nodes: import('../lib/types').TopicNode[]): TaxonomyTopic[] {
  return nodes.map((n) => ({
    id: n.topicId,
    numeral: n.keyNumber ?? n.topicId.toUpperCase(),
    title: n.title ?? n.topicId,
    count: n.children.length,
    keys: n.children.map((k) => ({
      id: k.topicId,
      num: k.keyNumber ?? k.topicId,
      label: k.title ?? k.topicId,
      count: k.children.length,
    })),
  }));
}

export default function Topics() {
  const { topicId } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const activeKeyId = resolveTopicParam(topicId);
  const [filter, setFilter] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ iii: true, iv: true });
  const [liveTree, setLiveTree] = useState<TaxonomyTopic[] | null>(null);
  const [liveDetail, setLiveDetail] = useState<KeyDetail | null>(null);

  // Live-API tree + detail (fixture mode is synchronous below).
  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    api
      .getTopics()
      .then((res) => alive && setLiveTree(liveTreeToTaxonomy(res.topics)))
      .catch(() => alive && setLiveTree(null));
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    api
      .getTopic(activeKeyId)
      .then((d) => {
        if (!alive) return;
        setLiveDetail({
          path: d.keyNumber ?? d.topicId,
          title: d.title ?? d.topicId,
          description: d.description ?? '',
          statutes: [],
          rules: [],
          subkeys: d.children.map((c) => ({ num: c.keyNumber ?? c.topicId, label: c.title ?? '', count: 0 })),
          caseCount: `${d.documents.length} headnoted documents`,
          cases: d.documents.map((doc) => ({
            caseId: doc.entryId != null ? String(doc.entryId) : null,
            title: doc.title ?? doc.facility ?? doc.docketId ?? '',
            cite: doc.docketId ?? '',
            court: doc.docType ?? '',
            date: doc.date ?? '',
            headnote: [doc.applicant, doc.facility].filter(Boolean).join(' — '),
            cited: 0,
            depth: '',
            flagBg: 'var(--surface2)',
            flagBorder: 'var(--border2)',
            flagTitle: '',
          })),
        });
      })
      .catch(() => alive && setLiveDetail(null));
    return () => {
      alive = false;
    };
  }, [activeKeyId]);

  const tree = (!api.USE_FIXTURES && liveTree) || TAXONOMY;
  const detail = (!api.USE_FIXTURES && liveDetail) || keyDetail(activeKeyId);

  const activeTopicId = activeKeyId.split('-')[0];

  const filteredTree = useMemo(() => {
    const q = filter.toLowerCase().trim();
    if (!q) return tree;
    return tree
      .map((t) => ({
        ...t,
        keys: t.keys.filter((k) => k.label.toLowerCase().includes(q) || k.num.toLowerCase().includes(q)),
      }))
      .filter((t) => t.title.toLowerCase().includes(q) || t.keys.length > 0);
  }, [tree, filter]);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
      <PageHeader
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Knowledge Base', to: '/kb' },
          { label: 'Topics & Key Numbers' },
        ]}
        title="Topic & Key Number System — Georgia CON"
        sub="6 major topics · 26 key numbers · 8,420 headnoted determinations"
        right={
          <button className="btn-outline" onClick={() => showToast('Taxonomy export queued — delivered to your firm inbox')}>
            <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden>
              <path d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Export taxonomy
          </button>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '340px minmax(0,1fr)', flex: 1, background: 'var(--page-bg)' }}>
        {/* ===== TREE ===== */}
        <aside style={{ background: 'var(--surface)', borderRight: '1px solid var(--surface2)', padding: '18px 0', overflowY: 'auto' }}>
          <div style={{ padding: '0 18px 10px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--surface2)', marginBottom: 8 }}>
            <svg width="13" height="13" viewBox="0 0 16 16" style={{ color: 'var(--text3)', flexShrink: 0 }} aria-hidden>
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.6} fill="none" />
              <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
            </svg>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter taxonomy…"
              style={{ flex: 1, border: 'none', outline: 'none', fontSize: 12, padding: '6px 0', background: 'transparent', color: 'var(--text)' }}
            />
          </div>
          {filteredTree.map((t) => {
            const open = !!filter || expanded[t.id] || t.id === activeTopicId;
            return (
              <div key={t.id}>
                <button
                  className="row-hover serif"
                  onClick={() => setExpanded((s) => ({ ...s, [t.id]: !open }))}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', padding: '9px 18px', fontSize: 13, color: 'var(--text)', fontWeight: 600 }}
                >
                  <span style={{ width: 10, color: 'var(--text3)', fontSize: 9 }}>{open ? '▾' : '▸'}</span>
                  <span
                    className="serif"
                    style={{
                      width: 22,
                      height: 22,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'rgba(244,63,94,0.14)',
                      color: 'var(--accent-text)',
                      borderRadius: 2,
                      fontSize: 10,
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {t.numeral}
                  </span>
                  <span style={{ flex: 1 }}>{t.title}</span>
                  <span style={{ fontSize: 11, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums', fontWeight: 400, fontFamily: 'var(--font-ui)' }}>
                    {t.count}
                  </span>
                </button>
                {open && (
                  <div style={{ padding: '2px 0 8px' }}>
                    {t.keys.map((k) => {
                      const active = k.id === activeKeyId;
                      return (
                        <button
                          key={k.id}
                          onClick={() => navigate(`/topics/${k.id}`)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            width: '100%',
                            textAlign: 'left',
                            padding: '6px 18px 6px 56px',
                            fontSize: 12.5,
                            color: active ? 'var(--accent-text)' : 'var(--text2)',
                            background: active ? 'rgba(244,63,94,0.14)' : 'transparent',
                            borderLeft: `3px solid ${active ? 'var(--brand-red)' : 'transparent'}`,
                            fontWeight: active ? 600 : 400,
                          }}
                        >
                          <span className="mono" style={{ fontSize: 11, color: active ? 'var(--accent-text)' : 'var(--text3)', fontWeight: 600, letterSpacing: 0.3, width: 60, flexShrink: 0 }}>
                            {k.num}
                          </span>
                          <span style={{ flex: 1, lineHeight: 1.3 }}>{k.label}</span>
                          <span style={{ fontSize: 10.5, color: 'var(--text3)', fontVariantNumeric: 'tabular-nums' }}>{k.count}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </aside>

        {/* ===== DETAIL ===== */}
        <div style={{ padding: '32px 40px 60px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span className="label-upper" style={{ letterSpacing: 1.4 }}>Key Number</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--accent-text)', fontWeight: 600, letterSpacing: 0.4 }}>{detail.path}</span>
          </div>
          <h2 className="serif" style={{ fontSize: 30, fontWeight: 600, color: 'var(--text)', margin: '0 0 10px', letterSpacing: '-0.4px', lineHeight: 1.15 }}>
            {detail.title}
          </h2>
          <p className="serif" style={{ fontSize: 14.5, lineHeight: 1.6, color: 'var(--text2)', maxWidth: 760, margin: '0 0 22px' }}>
            {detail.description}
          </p>

          {/* Authorities */}
          {(detail.statutes.length > 0 || detail.rules.length > 0) && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 30, maxWidth: 760 }}>
              {(
                [
                  ['Statutes', detail.statutes],
                  ['Rules', detail.rules],
                ] as const
              ).map(([label, list]) => (
                <div key={label} className="card" style={{ borderLeft: '3px solid var(--brand-red)', padding: '14px 16px' }}>
                  <div className="label-upper" style={{ letterSpacing: 1.4, marginBottom: 8 }}>{label}</div>
                  {list.map((s) => (
                    <Link key={s.statuteId} to={`/statute/${s.statuteId}`} className="mono" style={{ display: 'block', padding: '3px 0', fontSize: 12.5, color: 'var(--accent-text)' }}>
                      {s.label}
                    </Link>
                  ))}
                  {list.length === 0 && <div style={{ fontSize: 12, color: 'var(--text3)' }}>—</div>}
                </div>
              ))}
            </div>
          )}

          {/* Sub-keys */}
          {detail.subkeys.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <h3 className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, margin: '0 0 12px', paddingBottom: 8, borderBottom: '2px solid var(--border2)' }}>
                Sub-keys
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12, maxWidth: 760 }}>
                {detail.subkeys.map((sk) => (
                  <button
                    key={sk.num}
                    className="card row-hover"
                    onClick={() => showToast(`Sub-key ${detail.path} · ${sk.num} — filtered results land with the headnote index`)}
                    style={{ display: 'flex', alignItems: 'flex-start', gap: 12, textAlign: 'left', padding: '13px 14px' }}
                  >
                    <span className="mono" style={{ fontSize: 11, color: 'var(--accent-text)', fontWeight: 600, flexShrink: 0 }}>{sk.num}</span>
                    <span style={{ flex: 1, lineHeight: 1.3 }}>
                      <span className="serif" style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--text)' }}>{sk.label}</span>
                      {sk.count > 0 && <span style={{ display: 'block', fontSize: 11, color: 'var(--text2)', marginTop: 2 }}>{sk.count} cases</span>}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Headnoted cases */}
          <div style={{ maxWidth: 920 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderBottom: '2px solid var(--border2)', paddingBottom: 8, marginBottom: 8 }}>
              <h3 className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, margin: 0 }}>Headnoted Cases at this Key</h3>
              <div style={{ display: 'flex', gap: 14, fontSize: 12, color: 'var(--text2)' }}>
                <span>{detail.caseCount}</span>
                <Link to={`/results?q=${encodeURIComponent(detail.title)}&scope=all`} className="text-link">
                  View all →
                </Link>
              </div>
            </div>
            {detail.cases.length > 0 ? (
              <div className="list-card">
                {detail.cases.map((c, i) => (
                  <div key={i} className="list-row" style={{ display: 'flex', gap: 14, padding: '14px 18px', alignItems: 'flex-start' }}>
                    <span
                      title={c.flagTitle}
                      style={{ flexShrink: 0, width: 14, height: 14, borderRadius: '50%', background: c.flagBg, border: `1.5px solid ${c.flagBorder}`, marginTop: 4 }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {c.caseId ? (
                        <Link to={`/document/${c.caseId}`}>
                          <span
                            className="serif"
                            style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}
                            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                          >
                            <em style={{ fontStyle: 'italic' }}>{c.title}</em>
                          </span>
                        </Link>
                      ) : (
                        <span className="serif" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', fontStyle: 'italic' }}>{c.title}</span>
                      )}
                      <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 3, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="mono" style={{ color: 'var(--text)' }}>{c.cite}</span>
                        {c.court && (
                          <>
                            <span style={{ color: 'var(--border2)' }}>|</span>
                            <span>{c.court}</span>
                          </>
                        )}
                        {c.date && (
                          <>
                            <span style={{ color: 'var(--border2)' }}>|</span>
                            <span>{c.date}</span>
                          </>
                        )}
                      </div>
                      {c.headnote && (
                        <p style={{ margin: '7px 0 0', fontSize: 12.5, lineHeight: 1.5, color: 'var(--text2)' }}>{c.headnote}</p>
                      )}
                    </div>
                    <div style={{ flexShrink: 0, textAlign: 'right', fontSize: 11, color: 'var(--text2)', minWidth: 80, paddingTop: 2 }}>
                      {c.cited > 0 && (
                        <div style={{ fontWeight: 600, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{c.cited} cited</div>
                      )}
                      <div style={{ marginTop: 2 }}>{c.depth}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card" style={{ padding: '32px 20px', textAlign: 'center', fontSize: 12.5, color: 'var(--text3)' }}>
                Headnote assignments for this key are being back-filled from the corpus — run a{' '}
                <Link to={`/results?q=${encodeURIComponent(detail.title)}&scope=all`} className="text-link">
                  full-text search
                </Link>{' '}
                in the meantime.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
