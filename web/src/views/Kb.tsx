/*
 * KNOWLEDGE BASE LANDING (/kb) — hub cards into the CON Wiki, Statutes &
 * Rules, Topics & Key Numbers, and Active Proceedings, plus featured wiki
 * articles. From the comp's <!-- KNOWLEDGE BASE LANDING --> section.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { SectionHead } from '../components/Shell';
import * as api from '../lib/api';
import type { WikiIndexArticle } from '../lib/types';

function HubIcon({ d, color, bg }: { d: string; color?: string; bg?: string }) {
  return (
    <div className="hub-icon" style={{ width: 42, height: 42, ...(bg ? { background: bg } : {}), ...(color ? { color } : {}) }}>
      <svg width="20" height="20" viewBox="0 0 16 16" aria-hidden>
        <path d={d} stroke="currentColor" strokeWidth={1.3} fill="none" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    </div>
  );
}

const HUBS = [
  {
    to: '/wiki',
    accent: '#8E1B1F',
    icon: 'M8 3 C6 2 3.5 2 2.5 2.6 L2.5 12.6 C3.5 12 6 12 8 13 C10 12 12.5 12 13.5 12.6 L13.5 2.6 C12.5 2 10 2 8 3 Z M8 3 L8 13',
    title: 'CON Wiki',
    desc: "A practitioner's encyclopedia — process, substantive review, adjudication, and recent reform, with cross-links to statutes and leading decisions.",
    foot: '10 articles · 5 topics',
  },
  {
    to: '/statutes',
    accent: '#8E1B1F',
    icon: 'M4 2 L4 14 M4 5 L12 5 L13 7 L12 9 L4 9',
    title: 'Statutes & Rules',
    desc: 'O.C.G.A. Title 31, Chapter 6 and Ga. Comp. R. & Regs. 111-2-2, annotated section-by-section with citing cases.',
    foot: 'Updated Jun 14, 2026',
  },
  {
    to: '/topics',
    accent: '#F59E0B',
    icon: 'M3 3 L13 3 M3 6 L13 6 M3 9 L9 9 M3 12 L11 12',
    iconColor: '#F59E0B',
    iconBg: 'rgba(245,158,11,0.14)',
    title: 'Topics & Key Numbers',
    desc: 'The CON-specific taxonomy — drill from six major topics into key numbers and headnoted determinations and opinions.',
    foot: '6 topics · 142 keys',
  },
  {
    to: '/applications',
    accent: '#3B82F6',
    icon: 'M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4 M5 8 L11 8 M5 11 L9 11',
    iconColor: '#3B82F6',
    iconBg: 'rgba(59,130,246,0.14)',
    title: 'Active Proceedings',
    desc: 'The live docket — pending CON applications, determinations, and nonreviewability requests before the DCH Planning Section.',
    foot: '218 active dockets',
  },
];

export default function Kb() {
  const navigate = useNavigate();
  const [featured, setFeatured] = useState<WikiIndexArticle[]>([]);

  useEffect(() => {
    let alive = true;
    api
      .listWiki()
      .then((idx) => {
        if (!alive) return;
        const all = idx.groups.flatMap((g) => g.articles);
        const pick = ['overview', 'cycle', 'judicial']
          .map((id) => all.find((a) => a.id === id))
          .filter((a): a is WikiIndexArticle => !!a);
        setFeatured(pick.length ? pick : all.slice(0, 3));
      })
      .catch(() => alive && setFeatured([]));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Knowledge Base' }]}
        title="Knowledge Base"
        titleSize={26}
        sub="The authoritative reference layer — an editorial wiki of Georgia CON law, the annotated statutes and rules, and the CON-specific topic taxonomy, all cross-linked."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 1180 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 16, marginBottom: 34 }}>
            {HUBS.map((h) => (
              <button
                key={h.to}
                className="hub-card"
                onClick={() => navigate(h.to)}
                style={{ borderTop: `3px solid ${h.accent}`, borderRadius: '0 0 2px 2px', padding: '22px 24px', gap: 16 }}
              >
                <HubIcon d={h.icon} color={h.iconColor} bg={h.iconBg} />
                <div style={{ flex: 1 }}>
                  <div className="serif" style={{ fontSize: 19, fontWeight: 600, color: 'var(--text)', marginBottom: 5 }}>{h.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>{h.desc}</div>
                  <div className="label-upper" style={{ marginTop: 10, letterSpacing: 1 }}>{h.foot}</div>
                </div>
              </button>
            ))}
          </div>

          <SectionHead title="Featured wiki articles" right={<Link to="/wiki" className="text-link">Browse all →</Link>} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14 }}>
            {featured.map((a) => (
              <button
                key={a.id}
                className="hub-card"
                onClick={() => navigate(`/wiki/${a.id}`)}
                style={{ padding: '18px 18px 20px', flexDirection: 'column', gap: 9, minHeight: 150, alignItems: 'flex-start' }}
              >
                <span
                  style={{
                    fontSize: 9.5,
                    letterSpacing: 1,
                    textTransform: 'uppercase',
                    fontWeight: 700,
                    color: 'var(--accent-text)',
                    background: 'rgba(244,63,94,0.14)',
                    padding: '3px 8px',
                    borderRadius: 1,
                  }}
                >
                  CON Wiki
                </span>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>{a.title}</div>
                {a.lead && <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.5, flex: 1 }}>{a.lead}</div>}
                {a.readTime && <div style={{ fontSize: 11, color: 'var(--text3)' }}>{a.readTime} read</div>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
