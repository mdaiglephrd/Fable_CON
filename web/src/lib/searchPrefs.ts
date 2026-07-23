/*
 * Default search scope preference, persisted to localStorage — mirrors
 * lib/theme.ts's STORAGE_KEY/read-write pattern. Consumed by
 * views/Settings.tsx (the control that writes it) and views/NewSearch.tsx
 * (which reads it as the initial scope for a run search).
 */
const STORAGE_KEY = 'phrd-default-scope';

export function readDefaultScope(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  } catch {
    /* storage unavailable */
  }
  return 'all';
}

export function writeDefaultScope(scope: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, scope);
  } catch {
    /* storage unavailable */
  }
}
