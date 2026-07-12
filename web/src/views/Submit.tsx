/*
 * SUBMIT DOCUMENT (/submit) — the 3-step submission wizard: docket details
 * → metadata (doc_type/phase/decision_level/outcome, from common/vocab.py)
 * → review & publish. From the comp's <!-- SUBMIT --> section.
 *
 * There is no live "create decision" endpoint in api/routers yet — saving is
 * UI-complete only (a toast + navigate home), matching the task brief's
 * "no-op" note for both fixture and live mode.
 */
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { useToast } from '../components/Toast';
import { DECISION_LEVELS, DOC_TYPES, OUTCOMES, PHASES } from '../lib/vocab';
import { DOCKET_TYPES } from '../lib/fixtures';

interface FormState {
  docketType: string;
  docketNumber: string;
  stage: string;
  decisionDate: string;
  applicant: string;
  county: string;
  finding: string;
  description: string;
  docType: string;
  phase: string;
  decisionLevel: number;
  outcome: string;
  fileName: string;
  notes: string;
  confirmed: boolean;
}

const INITIAL: FormState = {
  docketType: '',
  docketNumber: '',
  stage: '',
  decisionDate: '',
  applicant: '',
  county: '',
  finding: '',
  description: '',
  docType: DOC_TYPES[0],
  phase: PHASES[0],
  decisionLevel: DECISION_LEVELS[0].level,
  outcome: OUTCOMES[0],
  fileName: '',
  notes: '',
  confirmed: false,
};

const STEP_LABELS = ['Docket & identifiers', 'Metadata & document', 'Review & publish'];

export default function Submit() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormState>(INITIAL);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));

  const next = (e?: FormEvent) => {
    e?.preventDefault();
    setStep((s) => Math.min(3, s + 1));
  };
  const back = () => setStep((s) => Math.max(1, s - 1));

  const publish = () => {
    // No-op save: no live "create decision" endpoint exists yet in
    // api/routers/*.py. This is UI-complete only, per the phase-2 brief.
    showToast(`${form.docketNumber || 'Document'} queued for editorial review and corpus indexing`, 'success');
    navigate('/applications');
  };

  const reviewRows: [string, string][] = [
    ['Docket Type', form.docketType ? `${form.docketType} — ${DOCKET_TYPES[form.docketType]?.full ?? ''}` : '—'],
    ['Docket Number', form.docketNumber || '—'],
    ['Proceeding Stage', form.stage || '—'],
    ['Decision Date', form.decisionDate || '—'],
    ['Applicant', form.applicant || '—'],
    ['County', form.county || '—'],
    ['Finding', form.finding || '—'],
    ['Document Type', form.docType],
    ['Phase', form.phase],
    ['Decision Level', DECISION_LEVELS.find((d) => d.level === form.decisionLevel)?.label ?? ''],
    ['Outcome', form.outcome],
    ['Document', form.fileName || 'No file attached'],
  ];

  return (
    <section>
      <div className="view-header">
        <Breadcrumb items={[{ label: 'Home', to: '/' }, { label: 'Upload', to: '/upload' }, { label: 'Submit Document' }]} />
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <h1 className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}>
            Submit a Decision or Order
          </h1>
          <span style={{ fontSize: 13, color: 'var(--text3)' }}>Add a new determination, decision, or order to the corpus</span>
        </div>
      </div>

      <div style={{ padding: '32px 64px 80px' }}>
        <div style={{ maxWidth: 820 }}>
          {/* Step indicator */}
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 32 }}>
            {STEP_LABELS.map((label, i) => {
              const num = i + 1;
              const active = step === num;
              const done = step > num;
              return (
                <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: '50%',
                        background: active ? 'var(--brand-red)' : done ? '#10B981' : 'var(--border2)',
                        color: '#FFFFFF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 12,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {done ? '✓' : num}
                    </div>
                    <span style={{ fontSize: 13, fontWeight: active ? 600 : 400, color: active ? 'var(--text)' : done ? '#10B981' : 'var(--text3)' }}>
                      {label}
                    </span>
                  </div>
                  {num < 3 && <div style={{ width: 32, height: 2, background: 'var(--surface2)', margin: '0 8px', flexShrink: 0 }} />}
                </div>
              );
            })}
          </div>

          <div className="card" style={{ padding: '32px 36px' }}>
            {step === 1 && (
              <form onSubmit={next}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', margin: '0 0 22px' }}>Docket type &amp; identifiers</h2>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                  <div>
                    <label className="field-label">Docket Type <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                    <select className="field-select" required value={form.docketType} onChange={(e) => set('docketType', e.target.value)}>
                      <option value="">— Select —</option>
                      {Object.entries(DOCKET_TYPES).map(([id, meta]) => (
                        <option key={id} value={id}>
                          {id} — {meta.full}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Docket / Project Number <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                    <input
                      className="field-input mono"
                      required
                      value={form.docketNumber}
                      onChange={(e) => set('docketNumber', e.target.value)}
                      placeholder="e.g. CON 2026-0118 or DET-EQT2026063"
                    />
                  </div>
                  <div>
                    <label className="field-label">Proceeding Stage <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                    <select className="field-select" required value={form.stage} onChange={(e) => set('stage', e.target.value)}>
                      <option value="">— Select —</option>
                      <option>DCH Planning — Initial Decision</option>
                      <option>OSAH — Hearing Officer Initial Decision</option>
                      <option>DCH Commissioner — Final Order</option>
                      <option>Superior Court — Order</option>
                      <option>Court of Appeals — Opinion</option>
                      <option>Supreme Court of Georgia — Opinion / Cert</option>
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Decision Date <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                    <input className="field-input" required type="date" value={form.decisionDate} onChange={(e) => set('decisionDate', e.target.value)} />
                  </div>
                </div>
                <div style={{ marginBottom: 20 }}>
                  <label className="field-label">Applicant / Facility Name <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                  <input
                    className="field-input"
                    required
                    value={form.applicant}
                    onChange={(e) => set('applicant', e.target.value)}
                    placeholder="e.g. Emory Saint Joseph's Hospital — or — Riverstone Imaging, LLC"
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                  <div>
                    <label className="field-label">County</label>
                    <input className="field-input" value={form.county} onChange={(e) => set('county', e.target.value)} placeholder="e.g. Fulton" />
                  </div>
                  <div>
                    <label className="field-label">Finding / Disposition <span style={{ color: 'var(--accent-text)' }}>*</span></label>
                    <select className="field-select" required value={form.finding} onChange={(e) => set('finding', e.target.value)}>
                      <option value="">— Select —</option>
                      <option>Approved</option>
                      <option>Denied</option>
                      <option>Issued (LNR)</option>
                      <option>Reversed and Remanded</option>
                      <option>Affirmed</option>
                      <option>Withdrawn</option>
                      <option>Cert. Denied</option>
                      <option>Pending</option>
                    </select>
                  </div>
                </div>
                <div style={{ marginBottom: 20 }}>
                  <label className="field-label">Project Description / Title</label>
                  <input
                    className="field-input"
                    value={form.description}
                    onChange={(e) => set('description', e.target.value)}
                    placeholder="e.g. Establishment of Fixed 1.5T MRI — Bartow County"
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 12, paddingTop: 16, borderTop: '1px solid var(--surface2)' }}>
                  <button type="button" className="btn-outline" onClick={() => navigate('/')}>Cancel</button>
                  <button type="submit" className="btn-primary">Continue →</button>
                </div>
              </form>
            )}

            {step === 2 && (
              <form onSubmit={next}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', margin: '0 0 22px' }}>Metadata &amp; document upload</h2>

                <div style={{ border: '2px dashed var(--border2)', borderRadius: 2, padding: 36, textAlign: 'center', background: 'var(--page-bg)', marginBottom: 20 }}>
                  <svg width="32" height="32" viewBox="0 0 32 32" style={{ color: 'var(--text3)', margin: '0 auto 12px', display: 'block' }} aria-hidden>
                    <path d="M16 4 L16 22 M8 14 L16 22 L24 14 M6 26 L26 26" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <div style={{ fontSize: 15, color: 'var(--text)', fontWeight: 500, marginBottom: 4 }}>Drag and drop the decision document</div>
                  <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 14 }}>
                    PDF, Word, or plain text — max 25 MB. We&rsquo;ll OCR and auto-extract headnotes.
                  </div>
                  <button
                    type="button"
                    className="btn-outline"
                    onClick={() => set('fileName', form.fileName || `${form.docketNumber || 'Decision'}.pdf`)}
                  >
                    Browse file…
                  </button>
                </div>

                {form.fileName && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', border: '1px solid var(--surface2)', borderRadius: 2, marginBottom: 20, background: 'var(--surface)' }}>
                    <div style={{ width: 34, height: 34, background: 'rgba(244,63,94,0.14)', color: 'var(--accent-text)', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
                        <path d="M3 2 L11 2 L13 4 L13 14 L3 14 Z M11 2 L11 4 L13 4" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)' }}>{form.fileName}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text2)' }}>Attached · headnotes will be extracted on publish</div>
                    </div>
                    <button type="button" onClick={() => set('fileName', '')} style={{ fontSize: 12, color: 'var(--accent-text)' }}>
                      Remove
                    </button>
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                  <div>
                    <label className="field-label">Document Type</label>
                    <select className="field-select" value={form.docType} onChange={(e) => set('docType', e.target.value)}>
                      {DOC_TYPES.map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Phase</label>
                    <select className="field-select" value={form.phase} onChange={(e) => set('phase', e.target.value)}>
                      {PHASES.map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Decision Level</label>
                    <select className="field-select" value={form.decisionLevel} onChange={(e) => set('decisionLevel', Number(e.target.value))}>
                      {DECISION_LEVELS.map((d) => (
                        <option key={d.level} value={d.level}>
                          {d.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Outcome</label>
                    <select className="field-select" value={form.outcome} onChange={(e) => set('outcome', e.target.value)}>
                      {OUTCOMES.map((o) => (
                        <option key={o}>{o}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ marginBottom: 20 }}>
                  <label className="field-label">Notes / Annotations (optional)</label>
                  <textarea
                    className="field-textarea"
                    value={form.notes}
                    onChange={(e) => set('notes', e.target.value)}
                    placeholder="Key holdings, procedural posture notes, related dockets…"
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, paddingTop: 16, borderTop: '1px solid var(--surface2)' }}>
                  <button type="button" onClick={back} style={{ fontSize: 13, color: 'var(--text2)' }}>← Back</button>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <button type="button" className="btn-outline" onClick={() => navigate('/')}>Cancel</button>
                    <button type="submit" className="btn-primary">Review →</button>
                  </div>
                </div>
              </form>
            )}

            {step === 3 && (
              <div>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', margin: '0 0 8px' }}>Review &amp; publish</h2>
                <p style={{ fontSize: 13, color: 'var(--text2)', margin: '0 0 22px' }}>
                  Confirm the metadata below. Once published, the decision is searchable and citator-linked across the corpus.
                </p>
                <div className="card" style={{ overflow: 'hidden', marginBottom: 20 }}>
                  {reviewRows.map(([label, value], i) => (
                    <div
                      key={label}
                      style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16, padding: '11px 18px', borderBottom: i === reviewRows.length - 1 ? 'none' : '1px solid var(--surface2)', background: i % 2 ? 'var(--surface2)' : 'transparent' }}
                    >
                      <div className="label-upper" style={{ letterSpacing: 0.8 }}>{label}</div>
                      <div style={{ fontSize: 13.5, color: 'var(--text)' }}>{value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 16px', background: 'rgba(245,158,11,0.14)', border: '1px solid #E5C97A', borderRadius: 2, marginBottom: 20 }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" style={{ color: '#10B981', flexShrink: 0, marginTop: 1 }} aria-hidden>
                    <path d="M8 2 L8 10 M8 13 L8 13.5" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
                  </svg>
                  <div style={{ fontSize: 12.5, color: '#7A5B0E', lineHeight: 1.5 }}>
                    This decision will be added to the corpus and indexed for search, Direct History, and Trace™ citator linking. Editorial
                    review may adjust headnote assignments.
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--text)', cursor: 'pointer', marginBottom: 22 }}>
                  <input type="checkbox" checked={form.confirmed} onChange={(e) => set('confirmed', e.target.checked)} style={{ width: 15, height: 15, accentColor: '#8E1B1F' }} />
                  I confirm this is a true and complete copy of the decision or order.
                </label>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, paddingTop: 16, borderTop: '1px solid var(--surface2)' }}>
                  <button type="button" onClick={back} style={{ fontSize: 13, color: 'var(--text2)' }}>← Back</button>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <button type="button" className="btn-outline" onClick={() => navigate('/')}>Cancel</button>
                    <button type="button" className="btn-primary" disabled={!form.confirmed} onClick={publish}>
                      Publish to corpus ✓
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
