import { DOCKET_TYPES } from '../lib/fixtures';

/** Docket-type pill (small / large) — colors from the comp's DOCKET_TYPES. */
export function DktBadge({ type, size }: { type?: string | null; size?: 'lg' }) {
  if (!type) return null;
  const meta = DOCKET_TYPES[type];
  const fill = meta?.fill ?? '#94A3B8';
  const label = meta?.label ?? type;
  return (
    <span
      className={`dkt-badge${size === 'lg' ? ' lg' : ''}`}
      title={meta?.full}
      style={{ background: fill }}
    >
      {label}
    </span>
  );
}
