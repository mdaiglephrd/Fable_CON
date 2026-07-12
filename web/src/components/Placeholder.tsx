import { Breadcrumb, type Crumb } from './Breadcrumb';

/**
 * Clean "coming in phase 2" page — keeps navigation complete for the views
 * that are not part of phase 1's core five screens.
 */
export function Placeholder({ title, crumbs, blurb }: { title: string; crumbs: Crumb[]; blurb?: string }) {
  return (
    <section>
      <div className="view-header">
        <Breadcrumb items={crumbs} />
        <h1
          className="serif"
          style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}
        >
          {title}
        </h1>
      </div>
      <div className="placeholder-wrap">
        <div className="placeholder-card">
          <div
            className="label-upper"
            style={{ color: 'var(--accent-text)', letterSpacing: 2, marginBottom: 14 }}
          >
            Coming in phase 2
          </div>
          <div className="serif" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', marginBottom: 10 }}>
            {title}
          </div>
          <p style={{ fontSize: 13, color: 'var(--text2)', margin: 0, lineHeight: 1.55 }}>
            {blurb ??
              'This view is scaffolded and routed; the full experience ships in the next phase of the console build-out.'}
          </p>
        </div>
      </div>
    </section>
  );
}
