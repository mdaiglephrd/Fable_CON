import type { ReactNode } from 'react';

import { Breadcrumb, type Crumb } from './Breadcrumb';

/**
 * Standard view header: surface band with breadcrumb, serif title, optional
 * subtitle, right-aligned actions, and trailing content (tab rows etc.) —
 * the comp's recurring `18px 32px` header block.
 */
export function PageHeader({
  crumbs,
  title,
  sub,
  right,
  children,
  titleSize = 24,
}: {
  crumbs: Crumb[];
  title: ReactNode;
  sub?: ReactNode;
  right?: ReactNode;
  children?: ReactNode;
  titleSize?: number;
}) {
  return (
    <div className="view-header">
      <Breadcrumb items={crumbs} />
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0 }}>
          <h1
            className="serif"
            style={{ fontSize: titleSize, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px', lineHeight: 1.2 }}
          >
            {title}
          </h1>
          {sub && (
            <div style={{ fontSize: 13, color: 'var(--text2)', marginTop: 5, maxWidth: 760, lineHeight: 1.5 }}>{sub}</div>
          )}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}
