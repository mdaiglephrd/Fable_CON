/*
 * RESEARCH LIBRARY (/library) — project cards tabbed Open vs. Saved
 * (complete), each with saved/flagged counts and tag chips. From the comp's
 * <!-- RESEARCH LIBRARY --> section. GET /projects when live; in-memory
 * seed (api.ts memProjects) in fixture mode.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import * as api from '../lib/api';
import type { ResearchProject } from '../lib/types';

type Tab = 'open' | 'saved';

function counts(p: ResearchProject): { saved: number; flagged: number } {
  const items = p.items ?? [];
  return {
    saved: items.filter((i) => !i.flagged).length,
    flagged: items.filter((i) => i.flagged).length,
  };
}

export default function Library() {
  const [tab, setTab] = useState<Tab>('open');
  const [projects, setProjects] = useState<ResearchProject[] | null>(null);

  useEffect(() => {
    api
      .listProjects()
      .then((res) => setProjects(res.items))
      .catch(() => setProjects([]));
  }, []);

  const open = (projects ?? []).filter((p) => p.status !== 'complete');
  const saved = (projects ?? []).filter((p) => p.status === 'complete');
  const list = tab === 'open' ? open : saved;

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'Research Library' }]}
        title="Research Library"
        titleSize={26}
        sub="Your saved and in-progress research projects."
      >
        <div style={{ display: 'flex', gap: 2, marginTop: 18, borderBottom: '1px solid var(--surface2)' }}>
          <button className={`line-tab${tab === 'open' ? ' active' : ''}`} onClick={() => setTab('open')}>
            Open Research Projects <span style={{ color: 'var(--text3)', fontWeight: 400 }}>({open.length})</span>
          </button>
          <button className={`line-tab${tab === 'saved' ? ' active' : ''}`} onClick={() => setTab('saved')}>
            Saved Projects <span style={{ color: 'var(--text3)', fontWeight: 400 }}>({saved.length})</span>
          </button>
        </div>
      </PageHeader>

      <div style={{ padding: '24px 32px 60px' }}>
        <div style={{ maxWidth: 880 }}>
          {projects === null && <div style={{ padding: 40, color: 'var(--text3)', fontSize: 13 }}>Loading projects…</div>}
          {projects !== null && list.length === 0 && (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text3)' }}>
              <div className="serif" style={{ fontSize: 15, color: 'var(--text2)', marginBottom: 6 }}>
                {tab === 'open' ? 'No open research projects' : 'No completed research projects yet'}
              </div>
              {tab === 'open' && (
                <Link to="/projects/new" className="text-link" style={{ fontSize: 12.5 }}>
                  Start a new research project →
                </Link>
              )}
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {list.map((p) => {
              const c = counts(p);
              return (
                <div key={p.projectId} className="card" style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Link to={`/projects/${p.projectId}`}>
                      <div
                        className="serif"
                        style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text)')}
                      >
                        {p.name}
                      </div>
                    </Link>
                    <div style={{ fontSize: 11.5, color: 'var(--text3)', marginTop: 4 }}>
                      {tab === 'open' ? `Created ${p.createdAt ?? '—'}` : 'Completed'} ·{' '}
                      <strong style={{ color: '#10B981' }}>{c.saved}</strong> relevant ·{' '}
                      <strong style={{ color: 'var(--text3)' }}>{c.flagged}</strong> flagged
                    </div>
                    {(p.tags?.length ?? 0) > 0 && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                        {p.tags!.map((t) => (
                          <span key={t} style={{ fontSize: 10.5, padding: '3px 8px', borderRadius: 10, background: 'var(--surface2)', color: 'var(--text2)' }}>
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  {tab === 'open' ? (
                    <>
                      <Link to={`/projects/${p.projectId}`} className="btn-outline" style={{ borderColor: 'var(--brand-red)', color: 'var(--accent-text)', flexShrink: 0 }}>
                        Resume →
                      </Link>
                      <Link to={`/projects/${p.projectId}`} style={{ flexShrink: 0, padding: '8px 12px', color: 'var(--text2)', fontSize: 12.5 }}>
                        View
                      </Link>
                    </>
                  ) : (
                    <Link to={`/projects/${p.projectId}`} className="btn-outline" style={{ flexShrink: 0 }}>
                      View →
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
