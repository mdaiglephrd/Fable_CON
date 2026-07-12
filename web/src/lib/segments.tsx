/*
 * Renderer for the tagged-tuple rich-text segment format used across the
 * corpus (see con-corpus.js header):
 *   "plain string" | ["i",t] | ["b",t] | ["case",t,id] | ["stat",t,id] | ["topic",t,id]
 * Cross-link kinds map to router links: case -> /document/:id,
 * stat -> /statute/:id, topic -> /topics/:id.
 */
import type { CSSProperties, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import type { Seg } from './types';

const caseStyle: CSSProperties = { fontStyle: 'italic' };
const statStyle: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: '0.92em',
};

export function renderSegs(segs: Seg[] | string | undefined | null): ReactNode {
  if (segs == null) return null;
  if (typeof segs === 'string') return segs;
  return segs.map((p, i) => {
    if (typeof p === 'string') return p;
    const [kind, text, ref] = p as [string, string, string?];
    switch (kind) {
      case 'i':
        return (
          <em key={i} style={{ fontStyle: 'italic' }}>
            {text}
          </em>
        );
      case 'b':
        return (
          <strong key={i} style={{ color: 'var(--text)' }}>
            {text}
          </strong>
        );
      case 'case':
        return (
          <Link key={i} className="seg-link" style={caseStyle} to={`/document/${ref}`}>
            {text}
          </Link>
        );
      case 'stat':
        return (
          <Link key={i} className="seg-link" style={statStyle} to={`/statute/${ref}`}>
            {text}
          </Link>
        );
      case 'topic':
        return (
          <Link key={i} className="seg-link" to={`/topics/${ref}`}>
            {text}
          </Link>
        );
      case 'hl':
        // Search-term highlight (used by the Results snippets, comp's hl()).
        return (
          <mark key={i} className="hl-mark">
            {text}
          </mark>
        );
      default:
        return text;
    }
  });
}

/** Flatten segments to plain text (for breadcrumbs, citations, titles). */
export function flatText(segs: Seg[] | string | undefined | null): string {
  if (segs == null) return '';
  if (typeof segs === 'string') return segs;
  return segs.map((p) => (typeof p === 'string' ? p : p[1])).join('');
}
