/*
 * RESEARCH PROJECT DETAIL (/projects/:projectId) — saved (relevant) and
 * flagged (irrelevant) dockets, with resume/complete actions. From the
 * comp's <!-- PROJECT DETAIL --> section.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { RECENT_DOCKETS } from '../lib/fixtures';
import type { ResearchProject } from '../lib/types';

function docketLabel(docketId: string): string {
  const rec = RECENT_DOCKETS.find((d) => d.num === docketId);
  return rec ? `${rec.facility} — ${rec.title}` : docketId;
}

export default function ProjectDetail() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [project, setProject] = useState<ResearchProject | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api
      .getProject(projectId)
      .then(setProject)
      .catch((e: Error) => setError(e.message));
  };
  useEffect(load, [projectId]);

  const complete = async () => {
    await api.completeProject(projectId);
    showToast(`"${project?.name}" marked complete`, 'success');
    load();
  };

  if (error) {
    return (
      <section>
        <div className="view-header">
          <Breadcrumb items={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'Research Library', to: '/library' }, { label: 'Project' }]} />
        </div>
        <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Project unavailable — {error}</div>
      </section>
    );
  }
  if (!project) {
    return <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading project…</div>;
  }

  const items = project.items ?? [];
  const saved = items.filter((i) => !i.flagged);
  const flagged = items.filter((i) => i.flagged);
  const isOpen = project.status !== 'complete';

  return (
    <section>
      <div className="view-header">
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: 'Research', to: '/research' },
            { label: 'Research Library', to: '/library' },
            { label: project.name ?? projectId },
          ]}
        />
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <h1 className="serif" style={{ fontSize: 24, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}>
            {project.name}
          </h1>
          {isOpen && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-outline" style={{ borderColor: 'var(--brand-red)', color: 'var(--accent-text)' }} onClick={() => navigate('/search/new')}>
                Resume reviewing
              </button>
              <button
                onClick={() => void complete()}
                style={{ padding: '8px 14px', background: '#10B981', color: '#052E1F', borderRadius: 2, fontSize: 12.5, fontWeight: 600 }}
              >
                Mark complete
              </button>
            </div>
          )}
        </div>
        {project.description && <div style={{ fontSize: 13, color: 'var(--text2)', marginTop: 6 }}>{project.description}</div>}
        {(project.tags?.length ?? 0) > 0 && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
            {project.tags!.map((t) => (
              <span key={t} style={{ fontSize: 10.5, padding: '3px 8px', borderRadius: 10, background: 'var(--surface2)', color: 'var(--text2)' }}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '24px 32px 60px' }}>
        <div style={{ maxWidth: 760 }}>
          <div className="label-upper" style={{ letterSpacing: 1.2, marginBottom: 10 }}>
            Relevant dockets ({saved.length}) · {flagged.length} flagged as irrelevant
          </div>
          {saved.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {saved.map((it) => (
                <div key={it.itemId} className="card" style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text)' }}>
                  {it.docketId ? (
                    <Link to={`/docket/${it.docketId}`} className="text-link">
                      {docketLabel(it.docketId)}
                    </Link>
                  ) : it.entryId != null ? (
                    <Link to={`/document/${it.entryId}`} className="text-link">
                      Document #{it.entryId}
                    </Link>
                  ) : (
                    <span>Untitled item</span>
                  )}
                  {it.note && <div style={{ fontSize: 11.5, color: 'var(--text2)', marginTop: 4 }}>{it.note}</div>}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text3)', fontSize: 13, padding: '30px 0', textAlign: 'center' }}>No dockets marked relevant yet.</div>
          )}
        </div>
      </div>
    </section>
  );
}
