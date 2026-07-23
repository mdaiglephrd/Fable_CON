/*
 * Recent-search history, tracked client-side in localStorage — following the
 * same idiom as theme.ts. There is no backend concept of "recent searches"
 * (see api/routers/*.py), so this is derived purely from genuine searches the
 * user actually runs (recorded from Results.tsx when a query resolves),
 * rather than fabricated demo entries.
 */

export interface RecentSearchEntry {
  q: string;
  scope: string;
  at: string; // ISO timestamp
}

const STORAGE_KEY = 'phrd-recent-searches';
const MAX_ENTRIES = 10;

export function getRecentSearches(): RecentSearchEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e): e is RecentSearchEntry =>
        !!e && typeof e === 'object' && typeof (e as RecentSearchEntry).q === 'string',
    );
  } catch {
    return [];
  }
}

/** Record a search the user actually ran, most-recent-first, capped at MAX_ENTRIES. */
export function recordRecentSearch(q: string, scope = 'all'): void {
  const query = q.trim();
  if (!query) return;
  try {
    const existing = getRecentSearches().filter((e) => !(e.q === query && e.scope === scope));
    const next: RecentSearchEntry[] = [
      { q: query, scope, at: new Date().toISOString() },
      ...existing,
    ].slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable */
  }
}

/** Relative "time ago" label for the recent-searches list. */
export function timeAgo(iso: string): string {
  const then = Date.parse(iso);
  if (isNaN(then)) return '';
  const diffMs = Date.now() - then;
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}
