/*
 * UPLOAD LANDING (/upload) — entry point into Submit Document. From the
 * comp's <!-- UPLOAD LANDING --> section.
 */
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';

export default function Upload() {
  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Upload' }]}
        title="Upload"
        titleSize={26}
        sub="Contribute determinations, orders, and dockets to the corpus — one at a time or in bulk."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 460 }}>
          <Link
            to="/submit"
            className="hub-card"
            style={{ borderTop: '3px solid var(--brand-red)', borderRadius: '0 0 2px 2px', padding: '22px 24px', flexDirection: 'column', gap: 10, minHeight: 170, width: '100%', alignItems: 'flex-start' }}
          >
            <div className="hub-icon" style={{ width: 40, height: 40 }}>
              <svg width="19" height="19" viewBox="0 0 16 16" aria-hidden>
                <path d="M8 2 L8 12 M4 8 L8 12 L12 8 M3 14 L13 14" stroke="currentColor" strokeWidth={1.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>Submit Document</div>
            <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>
              Add a single determination, decision, or order to the corpus with docket type, identifiers, and disposition.
            </div>
          </Link>
        </div>
      </div>
    </section>
  );
}
