/*
 * Signed-in user, sourced from the Static Web Apps built-in Entra ID auth
 * endpoint (GET /.auth/me). See web/staticwebapp.config.json — every route
 * requires the "authenticated" role, so in production clientPrincipal should
 * always be populated; a null principal there means the session lapsed and
 * the caller should treat it as signed-out. In local dev (no SWA auth
 * emulator) the endpoint 404s / clientPrincipal is null, so we fall back to
 * a placeholder user so the shell renders standalone.
 *
 * loadUser() distinguishes three outcomes:
 *   (a) confirmed signed-in  — clientPrincipal present
 *   (b) confirmed signed-out — fetch ok, clientPrincipal: null (a real,
 *       deliberate "not logged in")
 *   (c) indeterminate/error  — fetch threw, non-ok status, or bad JSON
 * Only (a) and (b) are ever cached. (c) is never cached, is logged via
 * console.error, gets one automatic retry after a short delay, and — if the
 * retry also fails — surfaces as `error` so the UI can offer a manual retry
 * via `refresh()` instead of permanently showing "Signed out".
 */
import { useEffect, useState } from 'react';

import { USE_FIXTURES } from './api';

export interface AppUser {
  name: string | null;
  email: string | null;
  initials: string;
  provider: string | null;
  roles: string[];
}

interface ClientPrincipalClaim {
  typ: string;
  val: string;
}

interface ClientPrincipal {
  identityProvider: string;
  userId: string;
  userDetails: string;
  userRoles?: string[];
  claims?: ClientPrincipalClaim[];
}

interface AuthMeResponse {
  clientPrincipal: ClientPrincipal | null;
}

const DEV_FALLBACK_USER: AppUser = {
  name: 'Local Dev',
  email: 'dev@localhost',
  initials: 'LD',
  provider: null,
  roles: [],
};

const SIGNED_OUT_USER: AppUser = {
  name: null,
  email: null,
  initials: '',
  provider: null,
  roles: [],
};

const RETRY_DELAY_MS = 1500;

function claim(claims: ClientPrincipalClaim[] | undefined, typ: string): string | undefined {
  return claims?.find((c) => c.typ === typ)?.val;
}

function initialsFor(name: string | null, email: string | null): string {
  if (name) {
    const words = name.trim().split(/\s+/).filter(Boolean).slice(0, 2);
    const chars = words.map((w) => w[0]).join('');
    if (chars) return chars.toUpperCase();
  }
  if (email) return email.slice(0, 2).toUpperCase();
  return '';
}

function fromPrincipal(cp: ClientPrincipal): AppUser {
  const claims = cp.claims;
  const name = claim(claims, 'name') ?? cp.userDetails ?? null;
  const email = cp.userDetails ?? claim(claims, 'preferred_username') ?? claim(claims, 'email') ?? null;
  return {
    name,
    email,
    initials: initialsFor(name, email),
    provider: cp.identityProvider ?? null,
    roles: cp.userRoles ?? [],
  };
}

type FetchResult = { ok: true; user: AppUser } | { ok: false; reason: string };

/** Single attempt at GET /.auth/me. Never throws — failures come back as { ok: false }. */
async function fetchOnce(): Promise<FetchResult> {
  let res: Response;
  try {
    res = await fetch('/.auth/me', { headers: { Accept: 'application/json' } });
  } catch (err) {
    return { ok: false, reason: `network error (${(err as Error).message ?? err})` };
  }
  if (!res.ok) return { ok: false, reason: `responded ${res.status}` };
  let body: AuthMeResponse;
  try {
    body = (await res.json()) as AuthMeResponse;
  } catch (err) {
    return { ok: false, reason: `invalid JSON (${(err as Error).message ?? err})` };
  }
  if (body.clientPrincipal) return { ok: true, user: fromPrincipal(body.clientPrincipal) };
  return { ok: true, user: USE_FIXTURES ? DEV_FALLBACK_USER : SIGNED_OUT_USER };
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Module-level cache + in-flight promise so multiple useUser() consumers
// share a single /.auth/me fetch (and a single retry).
let cached: AppUser | null = null;
let cachedError: string | null = null;
let inflight: Promise<void> | null = null;
const listeners = new Set<() => void>();

async function loadUser(): Promise<void> {
  const first = await fetchOnce();
  if (first.ok) {
    cached = first.user;
    cachedError = null;
    return;
  }
  // eslint-disable-next-line no-console
  console.error(`[useUser] /.auth/me failed (${first.reason}); retrying in ${RETRY_DELAY_MS}ms`);
  await delay(RETRY_DELAY_MS);
  const second = await fetchOnce();
  if (second.ok) {
    cached = second.user;
    cachedError = null;
    return;
  }
  // eslint-disable-next-line no-console
  console.error(`[useUser] /.auth/me failed again after retry (${second.reason}); giving up until refresh()`);
  cached = null;
  cachedError = second.reason;
}

function startLoad(): void {
  if (inflight) return;
  inflight = loadUser().then(() => {
    inflight = null;
    listeners.forEach((l) => l());
  });
}

/** Forces a fresh /.auth/me fetch, bypassing any cached error (or result). */
function refresh(): void {
  if (inflight) return;
  cached = null;
  cachedError = null;
  startLoad();
  listeners.forEach((l) => l());
}

function snapshot(): { user: AppUser | null; loading: boolean; error: string | null } {
  if (cached) return { user: cached, loading: false, error: null };
  if (inflight) return { user: null, loading: true, error: null };
  if (cachedError) return { user: null, loading: false, error: cachedError };
  return { user: null, loading: true, error: null };
}

export interface UseUserResult {
  user: AppUser | null;
  loading: boolean;
  /** Set only for indeterminate/error outcomes — never for a genuine signed-out state. */
  error: string | null;
  /** Bypasses cache and re-runs the /.auth/me fetch (with its own retry). */
  refresh: () => void;
}

/** Signed-in user, derived from /.auth/me. `user` is null while loading or on error. */
export function useUser(): UseUserResult {
  const [, forceRender] = useState(0);

  useEffect(() => {
    const listener = () => forceRender((n) => n + 1);
    listeners.add(listener);
    if (!cached && !cachedError && !inflight) startLoad();
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const { user, loading, error } = snapshot();
  return { user, loading, error, refresh };
}
