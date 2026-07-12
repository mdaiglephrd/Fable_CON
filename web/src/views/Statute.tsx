/*
 * STATUTE (/statute/:statuteId) — the annotated reader for one O.C.G.A.
 * section or DCH rule: TOC rail (Statute / Rules tabs), full text with
 * cross-linked subsections, history/authority note, and the citing-case
 * annotations rail. Structure from the comp's <!-- STATUTE --> section.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import * as api from '../lib/api';
import { renderSegs } from '../lib/segments';
import {
  ruleContentFor,
  RULES_TOC,
  STATUTE_ANNOTATIONS,
  STATUTE_TOC,
  statuteContentFor,
  type StatuteSubsection,
} from '../lib/statutesData';
import type { StatuteDetail } from '../lib/types';

type Tab = 'statute' | 'rules';

export default function Statute() {
  const { statuteId = '31-6-43' } = useParams();
  const navigate = useNavigate();

  const isRule = statuteId.startsWith('rule-');
  const [tab, setTab] = useState<Tab>(isRule ? 'rules' : 'statute');
  const [live, setLive] = useState<StatuteDetail | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);

  // Keep the tab in sync when a cross-link jumps between statute and rule.
  useEffect(() => {
    setTab(statuteId.startsWith('rule-') ? 'rules' : 'statute');
  }, [statuteId]);

  useEffect(() => {
    if (api.USE_FIXTURES) return;
    let alive = true;
    setLive(null);
    setLiveError(null);
    api
      .getStatute(statuteId)
      .then((s) => alive && setLive(s))
      .catch((e: Error) => alive && setLiveError(e.message));
    return () => {
      alive = false;
    };
  }, [statuteId]);

  const statuteContent = useMemo(() => statuteContentFor(isRule ? '31-6-43' : statuteId), [statuteId, isRule]);
  const ruleContent = useMemo(() => ruleContentFor(isRule ? statuteId : 'rule-111-2-2-.40'), [statuteId, isRule]);

  // Live mode fallback: render full_text / subsections best-effort.
  const liveSubs: StatuteSubsection[] | null = useMemo(() => {
    if (api.USE_FIXTURES || !live) return null;
    if (Array.isArray(live.subsections)) {
      return (live.subsections as { num?: string; text?: string }[]).map((s, i) => ({
        num: s.num ?? `(${i + 1})`,
        segs: [s.text ?? ''],
      }));
    }
    if (live.fullText) {
      return live.fullText
        .split(/\n\n+/)
        .filter(Boolean)
        .map((p, i) => ({ num: i === 0 ? '' : `¶${i}`, segs: [p] }));
    }
    return null;
  }, [live]);

  const headerNum = isRule
    ? (RULES_TOC.find((r) => r.id === statuteId)?.label ?? statuteId.replace(/^rule-/, ''))
    : (STATUTE_TOC.find((s) => s.id === statuteId)?.num ?? `§ ${statuteId}`);
  const headerTitle = live?.title ?? (tab === 'rules' ? ruleContent.title.split('— ')[1] ?? ruleContent.title : statuteContent.title);

  const annotations = useMemo(() => {
    if (!api.USE_FIXTURES && live?.citingCases?.length) {
      return live.citingCases.map((c) => ({
        subsection: c.pinpoint ?? '',
        label: c.treat ?? 'Citing',
        borderColor:
          c.level === 'positive' ? '#10B981' : c.level === 'negative' ? 'var(--accent-text)' : c.level === 'caution' ? '#F59E0B' : 'var(--text3)',
        title: c.title ?? '',
        cite: c.cite ?? '',
        holding: c.snippet ?? '',
        caseId: c.target != null ? String(c.target) : null,
      }));
    }
    return STATUTE_ANNOTATIONS;
  }, [live]);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
      {/* Header */}
      <div className="view-header">
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: 'Statutes & Rules', to: '/statutes' },
            {
              label: isRule
                ? 'Ga. Comp. R. & Regs. 111-2-2 (Certificate of Need)'
                : 'O.C.G.A. Title 31 · Chapter 6 (State Health Planning)',
            },
          ]}
        />
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <h1 className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}>
            {headerNum} — {headerTitle}
          </h1>
          <span style={{ fontSize: 12, color: 'var(--text3)' }}>
            Currency: <strong style={{ color: 'var(--text)' }}>2026 Reg. Sess. · Effective Jul. 1, 2024</strong>
          </span>
        </div>
        {liveError && (
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--status-denied)' }}>
            Live statute unavailable ({liveError}) — showing the bundled text.
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px minmax(0,1fr) 320px', flex: 1, background: 'var(--page-bg)' }}>
        {/* ===== TOC ===== */}
        <aside style={{ background: 'var(--surface)', borderRight: '1px solid var(--surface2)', padding: '16px 0', overflowY: 'auto', fontSize: 12.5 }}>
          <div style={{ padding: '0 16px 10px', borderBottom: '1px solid var(--surface2)' }}>
            <div className="label-upper" style={{ letterSpacing: 1.4, marginBottom: 6 }}>Table of Contents</div>
            <div style={{ display: 'flex', gap: 4, background: 'var(--page-bg)', padding: 3, borderRadius: 2 }}>
              {(['statute', 'rules'] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1,
                    padding: '5px 8px',
                    background: tab === t ? 'var(--surface2)' : 'transparent',
                    fontSize: 11,
                    fontWeight: tab === t ? 600 : 400,
                    borderRadius: 2,
                    color: tab === t ? 'var(--text)' : 'var(--text2)',
                  }}
                >
                  {t === 'statute' ? 'Statute' : 'Rules'}
                </button>
              ))}
            </div>
          </div>
          {(tab === 'statute' ? STATUTE_TOC : RULES_TOC).map((s) => {
            const id = s.id;
            const active = id === statuteId || (tab === 'rules' && isRule && id === statuteId);
            const num = 'num' in s ? s.num : s.label;
            return (
              <button
                key={id}
                onClick={() => navigate(`/statute/${id}`)}
                className={active ? '' : 'row-hover'}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  width: '100%',
                  textAlign: 'left',
                  padding: '7px 16px',
                  color: active ? 'var(--accent-text)' : 'var(--text2)',
                  background: active ? 'rgba(244,63,94,0.14)' : 'transparent',
                  borderLeft: `3px solid ${active ? 'var(--brand-red)' : 'transparent'}`,
                  fontWeight: active ? 600 : 400,
                }}
              >
                <span className="mono" style={{ fontSize: 11, color: active ? 'var(--accent-text)' : 'var(--text3)', fontWeight: 600, flexShrink: 0, width: 78 }}>
                  {num}
                </span>
                <span style={{ flex: 1, lineHeight: 1.3 }}>{s.title}</span>
              </button>
            );
          })}
        </aside>

        {/* ===== Text ===== */}
        <article className="serif" style={{ background: 'var(--surface)', padding: '36px 48px 80px', color: 'var(--text)', lineHeight: 1.65 }}>
          {tab === 'statute' ? (
            <>
              <div className="label-upper" style={{ color: 'var(--accent-text)', letterSpacing: 1.6, marginBottom: 8, fontFamily: 'var(--font-ui)' }}>
                {live?.citationLabel ?? statuteContent.cite}
              </div>
              <h2 className="serif" style={{ fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
                {live?.title ?? statuteContent.title}
              </h2>
              <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 24, fontFamily: 'var(--font-ui)' }}>{statuteContent.subtitle}</div>
              {(liveSubs ?? statuteContent.subs).map((ss, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, marginBottom: 18, paddingTop: 4 }}>
                  <div className="serif" style={{ flexShrink: 0, width: 36, fontWeight: 600, color: 'var(--accent-text)', fontSize: 15, paddingTop: 2 }}>
                    {ss.num}
                  </div>
                  <div style={{ flex: 1, fontSize: 15, lineHeight: 1.7 }}>{renderSegs(ss.segs)}</div>
                </div>
              ))}
              <div className="card" style={{ marginTop: 32, padding: '14px 16px', background: 'var(--page-bg)', fontFamily: 'var(--font-ui)', fontSize: 12.5, color: 'var(--text2)' }}>
                <strong style={{ color: 'var(--text)' }}>History:</strong> {statuteContent.history}
              </div>
            </>
          ) : (
            <>
              <div className="label-upper" style={{ color: 'var(--accent-text)', letterSpacing: 1.6, marginBottom: 8, fontFamily: 'var(--font-ui)' }}>
                Ga. Comp. R. &amp; Regs. 111-2-2
              </div>
              <h2 className="serif" style={{ fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: '0 0 6px', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
                {ruleContent.title}
              </h2>
              <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 24, fontFamily: 'var(--font-ui)' }}>
                Ga. Comp. R. &amp; Regs. 111-2-2 — Chapter on Certificate of Need
              </div>
              {ruleContent.subs.map((rs, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, marginBottom: 18, paddingTop: 4 }}>
                  <div className="mono" style={{ flexShrink: 0, width: 52, fontWeight: 600, color: 'var(--accent-text)', fontSize: 12, paddingTop: 4 }}>
                    {rs.num}
                  </div>
                  <div style={{ flex: 1, fontSize: 15, lineHeight: 1.7 }}>{renderSegs(rs.segs)}</div>
                </div>
              ))}
              <div className="card" style={{ marginTop: 32, padding: '14px 16px', background: 'var(--page-bg)', fontFamily: 'var(--font-ui)', fontSize: 12.5, color: 'var(--text2)' }}>
                <strong style={{ color: 'var(--text)' }}>Authority:</strong> {ruleContent.authority}
              </div>
            </>
          )}
        </article>

        {/* ===== Annotations ===== */}
        <aside style={{ background: 'var(--page-bg)', borderLeft: '1px solid var(--surface2)', padding: '24px 22px 60px', overflowY: 'auto' }}>
          <h3 className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="13" height="13" viewBox="0 0 16 16" style={{ color: 'var(--accent-text)' }} aria-hidden>
              <path d="M4 2 L12 2 L12 14 L4 14 Z M4 5 L12 5 M4 9 L12 9" stroke="currentColor" strokeWidth={1.4} fill="none" />
            </svg>
            Annotations
            <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text2)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
              412 cases citing
            </span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {annotations.map((a, i) => (
              <div key={i} className="card" style={{ borderLeft: `3px solid ${a.borderColor}`, padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
                  {a.subsection && (
                    <span className="mono" style={{ fontSize: 10, color: 'var(--accent-text)', fontWeight: 600, background: 'rgba(244,63,94,0.14)', padding: '2px 6px', borderRadius: 1 }}>
                      {a.subsection}
                    </span>
                  )}
                  <span className="label-upper" style={{ fontSize: 10, letterSpacing: 1 }}>{a.label}</span>
                </div>
                {a.caseId ? (
                  <Link to={`/document/${a.caseId}`}>
                    <div
                      className="serif"
                      style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                    >
                      <em style={{ fontStyle: 'italic' }}>{a.title}</em>
                    </div>
                  </Link>
                ) : (
                  <div className="serif" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, fontStyle: 'italic' }}>{a.title}</div>
                )}
                <div className="mono" style={{ fontSize: 11, color: 'var(--text2)', marginTop: 3 }}>{a.cite}</div>
                {a.holding && <p style={{ margin: '7px 0 0', fontSize: 12, lineHeight: 1.45, color: 'var(--text2)' }}>{a.holding}</p>}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
