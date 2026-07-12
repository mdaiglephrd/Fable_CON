/*
 * NEW RESEARCH PROJECT (/projects/new) — name / description / topic-tag
 * form; creating navigates into the project detail with a toast. From the
 * comp's <!-- NEW RESEARCH PROJECT --> section. POST /projects when live;
 * in-memory in fixture mode.
 */
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';

export const PROJECT_TAGS = [
  'I. Jurisdiction & Reviewability',
  'II. Application Process',
  'III. Substantive Review',
  'IV. Imaging (MRI/CT/PET)',
  'V. Adjudication',
  'VI. Appellate Review',
];

export default function NewProject() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const toggleTag = (t: string) => setTags((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]));

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      showToast('Name the project first');
      return;
    }
    setSaving(true);
    try {
      const project = await api.createProject({ name: name.trim(), description: desc.trim() || undefined, tags });
      showToast(`Research project "${project.name}" created`, 'success');
      navigate(`/projects/${project.projectId}`);
    } catch (err) {
      showToast(`Could not create project — ${(err as Error).message}`);
      setSaving(false);
    }
  };

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'New Research Project' }]}
        title="New Research Project"
        titleSize={26}
        sub="As you review dockets, mark each relevant or irrelevant — relevant ones save to the project, irrelevant ones are flagged so you won't see them again this project."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <form className="card" onSubmit={create} style={{ maxWidth: 640, padding: '30px 34px' }}>
          <label className="field-label" style={{ marginBottom: 8 }}>Project name</label>
          <input
            className="field-input"
            style={{ marginBottom: 20 }}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Cardiac cath denials — Bartow PSA"
          />
          <label className="field-label" style={{ marginBottom: 8 }}>
            Description <span style={{ textTransform: 'none', fontWeight: 400, color: 'var(--text3)' }}>(optional)</span>
          </label>
          <textarea
            className="field-textarea"
            style={{ marginBottom: 20, minHeight: 80, fontSize: 13.5 }}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="What are you researching?"
          />
          <label className="field-label" style={{ marginBottom: 10 }}>Topic &amp; key number tags</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 26 }}>
            {PROJECT_TAGS.map((t) => {
              const on = tags.includes(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => toggleTag(t)}
                  style={{
                    padding: '7px 13px',
                    borderRadius: 14,
                    fontSize: 12.5,
                    fontWeight: 500,
                    boxShadow: on ? 'inset 0 0 0 1px var(--brand-red)' : 'none',
                    background: on ? 'rgba(142,27,31,0.14)' : 'var(--surface2)',
                    color: on ? 'var(--accent-text)' : 'var(--text2)',
                  }}
                >
                  {t}
                </button>
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 20, borderTop: '1px solid var(--surface2)' }}>
            <button type="button" onClick={() => navigate('/research')} style={{ padding: '10px 18px', color: 'var(--text2)', fontSize: 13.5 }}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving} style={{ padding: '10px 22px', fontSize: 13.5 }}>
              Create &amp; start reviewing →
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
