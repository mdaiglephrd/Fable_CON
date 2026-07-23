/*
 * Public landing / sign-in page — the one route reachable without an
 * authenticated Entra ID session (see web/staticwebapp.config.json). Mirrors
 * the topbar brand mark from Shell.tsx and the app's card/button idiom from
 * styles/app.css, and drives the SWA built-in auth endpoints directly.
 */
import { Link } from 'react-router-dom';

import { useTheme } from '../lib/theme';
import { useUser } from '../lib/useUser';

const SIGN_IN_URL = '/.auth/login/aad?post_login_redirect_uri=/';
const SIGN_OUT_URL = '/.auth/logout?post_logout_redirect_uri=/login';

function Brand() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 1, fontFamily: 'var(--font-serif)' }}>
        <span style={{ fontSize: 30, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.5px' }}>PH</span>
        <span style={{ fontSize: 30, fontWeight: 700, color: 'var(--accent-text)', letterSpacing: '-0.5px' }}>RD</span>
      </div>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          lineHeight: 1.1,
          borderLeft: '1px solid var(--border2)',
          paddingLeft: 12,
        }}
      >
        <span style={{ fontSize: 10, letterSpacing: 1.5, color: 'var(--text3)', textTransform: 'uppercase' }}>
          Research
        </span>
        <span style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', fontFamily: 'var(--font-serif)' }}>
          Georgia CON
        </span>
      </div>
    </div>
  );
}

export default function Login() {
  // /login sits outside <Shell/>, so it must apply the same data-theme
  // mechanism Shell relies on — otherwise a direct/unauthenticated visit
  // would render with no theme resolved.
  useTheme();
  const { user, loading } = useUser();
  const signedIn = !loading && !!user?.name;

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--page-bg)',
        padding: 24,
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: 420,
          padding: '36px 32px',
          borderTop: '3px solid var(--brand-red)',
          textAlign: 'center',
        }}
      >
        <Brand />
        <p style={{ marginTop: 18, marginBottom: 30, fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>
          The research console for Georgia Certificate of Need dockets, statutes, and precedent.
        </p>

        {loading && (
          <div style={{ padding: '10px 0', fontSize: 13, color: 'var(--text3)' }}>Checking sign-in status…</div>
        )}

        {!loading && !signedIn && (
          <a
            href={SIGN_IN_URL}
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '11px 18px', fontSize: 13.5 }}
            onClick={(e) => {
              e.preventDefault();
              window.location.href = SIGN_IN_URL;
            }}
          >
            Sign in with Microsoft
          </a>
        )}

        {!loading && signedIn && (
          <>
            <div
              style={{
                marginBottom: 22,
                padding: '10px 14px',
                borderRadius: 'var(--radius-xs)',
                background: 'var(--surface2)',
                fontSize: 12.5,
                color: 'var(--text)',
              }}
            >
              Signed in as <strong>{user?.name}</strong>
              {user?.email ? <> ({user.email})</> : null}
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <Link
                to="/"
                className="btn-primary"
                style={{ flex: 1, justifyContent: 'center', padding: '10px 16px', fontSize: 13 }}
              >
                Open console
              </Link>
              <a
                href={SIGN_OUT_URL}
                className="btn-outline"
                style={{ flex: 1, justifyContent: 'center', padding: '9px 16px', fontSize: 13 }}
                onClick={(e) => {
                  e.preventDefault();
                  window.location.href = SIGN_OUT_URL;
                }}
              >
                Sign out
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
