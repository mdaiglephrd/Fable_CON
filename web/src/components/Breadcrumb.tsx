import { Fragment } from 'react';
import { Link } from 'react-router-dom';

export interface Crumb {
  label: string;
  to?: string;
}

/**
 * `Home › Section › Subsection` breadcrumb row (12px, --text2; links in
 * --accent-text with underline-on-hover; current page --text3).
 */
export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <div className="breadcrumb">
      {items.map((c, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="crumb-sep">›</span>}
          {c.to ? (
            <Link className="crumb-link" to={c.to}>
              {c.label}
            </Link>
          ) : (
            <span className="crumb-current">{c.label}</span>
          )}
        </Fragment>
      ))}
    </div>
  );
}
