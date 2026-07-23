/*
 * Signed-in user, sourced from the Static Web Apps built-in Entra ID auth
 * endpoint (GET /.auth/me). See web/staticwebapp.config.json — every route
 * requires the "authenticated" role, so in production clientPrincipal should
 * always be populated; a null principal there means the session lapsed and
 * the caller should treat it as signed-out. In local dev (no SWA auth
 * emulator) the endpoint 404s / clientPrincipal is null, so we fall back to
 * a placeholder user so the shell renders standalone.
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

// Module-level cache + in-flight promise so multiple useUser() consumers
// share a single /.auth/me fetch.
let cached: AppUser | null = null;
let inflight: Promise<AppUser> | null = null;
const listeners = new Set<(user: AppUser) => void>();

async function loadUser(): Promise<AppUser> {
  try {
    const res = await fetch('/.auth/me', { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`/.auth/me responded ${res.status}`);
    const body = (await res.json()) as AuthMeResponse;
    if (body.clientPrincipal) return fromPrincipal(body.clientPrincipal);
    return USE_FIXTURES ? DEV_FALLBACK_USER : SIGNED_OUT_USER;
  } catch {
    return USE_FIXTURES ? DEV_FALLBACK_USER : SIGNED_OUT_USER;
  }
}

function getUser(): { user: AppUser | null; loading: boolean } {
  if (cached) return { user: cached, loading: false };
  if (!inflight) {
    inflight = loadUser().then((user) => {
      cached = user;
      inflight = null;
      listeners.forEach((l) => l(user));
      return user;
    });
  }
  return { user: null, loading: true };
}

/** Signed-in user, derived from /.auth/me. `user` is null while loading. */
export function useUser(): { user: AppUser | null; loading: boolean } {
  const [, forceRender] = useState(0);

  useEffect(() => {
    if (cached) return;
    const listener = () => forceRender((n) => n + 1);
    listeners.add(listener);
    getUser();
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return getUser();
}
