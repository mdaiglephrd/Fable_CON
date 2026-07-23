/*
 * SETTINGS (/settings) — user-menu-only screen consolidating the former
 * "Settings" and "Personalization" stubs into one basic page: read-only
 * profile info, the theme toggle (mirrors the topbar's), a default search
 * scope preference, and sign out. From Shell.tsx's user menu.
 */
import { useState } from 'react';

import { PageHeader } from '../components/PageHeader';
import { SCOPE_DEFS } from '../lib/fixtures';
import { readDefaultScope, writeDefaultScope } from '../lib/searchPrefs';
import { useTheme } from '../lib/theme';
import { useUser } from '../lib/useUser';

const SIGN_OUT_URL = '/.auth/logout?post_logout_redirect_uri=/login';

export default function Settings() {
  const { user, loading, error, refresh } = useUser();
  const { theme, setTheme } = useTheme();
  const [defaultScope, setDefaultScope] = useState(readDefaultScope);

  const onScopeChange = (next: string) => {
    setDefaultScope(next);
    writeDefaultScope(next);
  };

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Settings' }]}
        title="Settings"
        titleSize={26}
        sub="Your profile, appearance, and search preferences for this browser."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div className="card" style={{ maxWidth: 640, padding: '30px 34px', display: 'flex', flexDirection: 'column', gap: 28 }}>
          {/* Profile */}
          <div>
            <div className="label-upper" style={{ marginBottom: 14 }}>Profile</div>
            {loading && <div style={{ fontSize: 13, color: 'var(--text3)' }}>Checking sign-in status…</div>}
            {!loading && error && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 13, color: 'var(--brand-red)' }}>Unable to verify sign-in.</span>
                <button type="button" className="btn-outline" onClick={refresh}>
                  Retry
                </button>
              </div>
            )}
            {!loading && !error && (
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
                <span style={{ color: 'var(--text3)' }}>Name</span>
                <span style={{ color: 'var(--text)' }}>{user?.name ?? 'Signed out'}</span>
                <span style={{ color: 'var(--text3)' }}>Email</span>
                <span style={{ color: 'var(--text)' }}>{user?.email ?? '—'}</span>
                <span style={{ color: 'var(--text3)' }}>Identity provider</span>
                <span style={{ color: 'var(--text)' }}>{user?.provider ?? '—'}</span>
              </div>
            )}
          </div>

          {/* Appearance */}
          <div style={{ paddingTop: 20, borderTop: '1px solid var(--surface2)' }}>
            <div className="label-upper" style={{ marginBottom: 14 }}>Appearance</div>
            <label className="field-label" style={{ marginBottom: 8 }}>Theme</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['light', 'dark'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t)}
                  className={theme === t ? 'btn-primary' : 'btn-outline'}
                  style={{ textTransform: 'capitalize', padding: '8px 20px' }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Search defaults */}
          <div style={{ paddingTop: 20, borderTop: '1px solid var(--surface2)' }}>
            <div className="label-upper" style={{ marginBottom: 14 }}>Search defaults</div>
            <label className="field-label" style={{ marginBottom: 8 }}>Default search scope</label>
            <select
              className="field-select"
              style={{ maxWidth: 320 }}
              value={defaultScope}
              onChange={(e) => onScopeChange(e.target.value)}
            >
              {Object.entries(SCOPE_DEFS).map(([id, def]) => (
                <option key={id} value={id}>
                  {def.label}
                </option>
              ))}
            </select>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 8, lineHeight: 1.5 }}>
              Used as the starting scope for Quick Search. Existing searches and links that specify their own
              scope are unaffected.
            </div>
          </div>

          {/* Sign out */}
          <div style={{ paddingTop: 20, borderTop: '1px solid var(--surface2)' }}>
            <a
              href={SIGN_OUT_URL}
              className="btn-outline"
              style={{ color: '#fca5a5', borderColor: 'rgba(244,63,94,0.4)' }}
              onClick={(e) => {
                e.preventDefault();
                window.location.href = SIGN_OUT_URL;
              }}
            >
              Log out
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
