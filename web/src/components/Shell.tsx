/*
 * Global shell — top bar + left rail + scrollable main (layout wrapper for
 * every route), per the handoff README "Global Shell" and the comp's
 * TOP BAR / LEFT RAIL blocks.
 */
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';
import { Link, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { SCOPE_DEFS } from '../lib/fixtures';
import { useTheme } from '../lib/theme';
import { useUser } from '../lib/useUser';
import { useToast } from './Toast';

// ---------------------------------------------------------------------------
// Inline stroke icons (13–16px, currentColor) — paths from the comp
// ---------------------------------------------------------------------------

function Ic({ d, size = 14 }: { d: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ICONS = {
  home: 'M2 8 L8 3 L14 8 M4 7 L4 13 L12 13 L12 7',
  kb: 'M8 3 C6 2 3.5 2 2.5 2.6 L2.5 12.6 C3.5 12 6 12 8 13 C10 12 12.5 12 13.5 12.6 L13.5 2.6 C12.5 2 10 2 8 3 Z M8 3 L8 13',
  research: 'M7 3 A4 4 0 1 0 7.001 11 A4 4 0 0 0 7 3 M10 10 L13.5 13.5',
  proceedings: 'M2 4.5 L6 4.5 L7.2 6.2 L14 6.2 L14 13 L2 13 Z',
  tools: 'M3 13 L3 3 M3 13 L13 13 M5.5 11 L5.5 7 M8 11 L8 5 M10.5 11 L10.5 9',
  upload: 'M8 2 L8 12 M4 8 L8 12 L12 8 M3 14 L13 14',
  advanced: 'M4 3 L4 13 L8 11 L12 13 L12 3 Z',
};

function BellIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
      <path
        d="M3.5 11 L12.5 11 L11 9 L11 6.5 A3 3 0 0 0 5 6.5 L5 9 Z M6.5 11 A1.5 1.5 0 0 0 9.5 11"
        stroke="currentColor"
        strokeWidth={1.3}
        fill="none"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SearchIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden>
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.8} fill="none" />
      <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
    </svg>
  );
}

function ThemeIcon({ theme }: { theme: string }) {
  return theme === 'dark' ? (
    // sun (switch to light)
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
      <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth={1.3} fill="none" />
      <path
        d="M8 1.5 L8 3 M8 13 L8 14.5 M14.5 8 L13 8 M3 8 L1.5 8 M12.6 3.4 L11.5 4.5 M4.5 11.5 L3.4 12.6 M12.6 12.6 L11.5 11.5 M4.5 4.5 L3.4 3.4"
        stroke="currentColor"
        strokeWidth={1.3}
        strokeLinecap="round"
      />
    </svg>
  ) : (
    // moon (switch to dark)
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden>
      <path
        d="M13 9.5 A5.5 5.5 0 1 1 6.5 3 A4.5 4.5 0 0 0 13 9.5 Z"
        stroke="currentColor"
        strokeWidth={1.3}
        fill="none"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Left-rail nav model (groups + children from the comp's NAV_GROUPS)
// ---------------------------------------------------------------------------

interface NavChild {
  id: string;
  label: string;
  to: string;
  count?: string | number;
}

interface NavGroup {
  id: string;
  label: string;
  icon: string;
  to: string;
  children?: NavChild[];
}

const NAV_GROUPS: NavGroup[] = [
  { id: 'home', label: 'Home', icon: ICONS.home, to: '/' },
  {
    id: 'kb',
    label: 'Knowledge Base',
    icon: ICONS.kb,
    to: '/kb',
    children: [
      { id: 'wiki', label: 'CON Wiki', to: '/wiki' },
      { id: 'statutes', label: 'Statutes & Rules', to: '/statutes' },
      { id: 'topics', label: 'Topics & Key Numbers', to: '/topics/iii', count: '142' },
      { id: 'applications', label: 'Active Proceedings', to: '/applications', count: '218' },
    ],
  },
  {
    id: 'research',
    label: 'Research',
    icon: ICONS.research,
    to: '/research',
    children: [
      { id: 'newsearch', label: 'Quick Search', to: '/search/new' },
      { id: 'newproject', label: 'New Research Project', to: '/projects/new' },
      { id: 'library', label: 'Research Library', to: '/library' },
      { id: 'history', label: 'Research History', to: '/history' },
      { id: 'citator', label: 'Trace™ Citator', to: '/citator/riverstone-imaging' },
    ],
  },
  {
    id: 'proceedings',
    label: 'My Proceedings',
    icon: ICONS.proceedings,
    to: '/proceedings',
    children: [
      { id: 'docket', label: 'Docket View', to: '/docket/riverstone-imaging' },
      { id: 'alerts', label: 'Alerts', to: '/alerts', count: 3 },
      { id: 'matterhistory', label: 'History', to: '/proceedings/history' },
    ],
  },
  {
    id: 'tools',
    label: 'Analytics & Tools',
    icon: ICONS.tools,
    to: '/tools',
    children: [
      { id: 'stats', label: 'Outcome Statistics', to: '/stats' },
      { id: 'calculator', label: 'Deadline Calculator', to: '/calculator' },
      { id: 'map', label: 'Service-Area Map', to: '/map' },
      { id: 'reports', label: 'Weekly Reports', to: '/reports' },
    ],
  },
  {
    id: 'upload',
    label: 'Upload',
    icon: ICONS.upload,
    to: '/upload',
    children: [{ id: 'submit', label: 'Submit Document', to: '/submit' }],
  },
];

/** view id per first path segment (the comp's NAV_PARENT, route-keyed). */
function navIdsForPath(pathname: string): { parent: string; child: string | null } {
  const seg = pathname.split('/').filter(Boolean);
  const first = seg[0] ?? '';
  const table: Record<string, [string, string | null]> = {
    '': ['home', null],
    kb: ['kb', null],
    wiki: ['kb', 'wiki'],
    statutes: ['kb', 'statutes'],
    statute: ['kb', 'statutes'],
    topics: ['kb', 'topics'],
    applications: ['kb', 'applications'],
    research: ['research', null],
    results: ['research', null],
    document: ['research', null],
    citator: ['research', 'citator'],
    history: ['research', 'history'],
    library: ['research', 'library'],
    proceedings: ['proceedings', seg[1] === 'history' ? 'matterhistory' : null],
    docket: ['proceedings', 'docket'],
    alerts: ['proceedings', 'alerts'],
    tools: ['tools', null],
    stats: ['tools', 'stats'],
    calculator: ['tools', 'calculator'],
    compare: ['tools', null],
    map: ['tools', 'map'],
    reports: ['tools', 'reports'],
    upload: ['upload', null],
    submit: ['upload', 'submit'],
  };
  if (first === 'search') return { parent: 'research', child: 'newsearch' };
  if (first === 'projects') {
    return { parent: 'research', child: seg[1] === 'new' ? 'newproject' : 'library' };
  }
  const hit = table[first] ?? ['home', null];
  return { parent: hit[0], child: hit[1] };
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 16 16"
      style={{ transition: 'transform .15s', transform: open ? 'rotate(90deg)' : 'none', flexShrink: 0 }}
      aria-hidden
    >
      <path d="M6 3 L11 8 L6 13" stroke="currentColor" strokeWidth={1.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Shell
// ---------------------------------------------------------------------------

export function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();
  const { user, loading: userLoading } = useUser();
  const userName = user?.name ?? (userLoading ? '…' : 'Signed out');
  const userSubtitle = userLoading ? '' : (user?.email ?? '');
  const userInitials = userLoading ? '' : (user?.initials ?? '');

  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('all');
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedNav, setExpandedNav] = useState<Record<string, boolean>>({});
  const mainRef = useRef<HTMLElement>(null);

  const { parent: activeParent, child: activeChild } = useMemo(
    () => navIdsForPath(location.pathname),
    [location.pathname],
  );

  // Keep the top-bar box in sync when landing on /results?q=…&scope=…
  useEffect(() => {
    if (location.pathname === '/results') {
      setQuery(searchParams.get('q') ?? '');
      const s = searchParams.get('scope');
      if (s && SCOPE_DEFS[s]) setScope(s);
    }
  }, [location.pathname, searchParams]);

  // Scroll main content to top on navigation.
  useEffect(() => {
    mainRef.current?.scrollTo(0, 0);
  }, [location.pathname, location.search]);

  const runSearch = (e?: FormEvent) => {
    e?.preventDefault();
    navigate(`/results?q=${encodeURIComponent(query)}&scope=${encodeURIComponent(scope)}`);
  };

  const onScopeChange = (next: string) => {
    setScope(next);
    if (location.pathname === '/results') {
      navigate(`/results?q=${encodeURIComponent(query)}&scope=${encodeURIComponent(next)}`);
    }
  };

  return (
    <div className="app-frame">
      {/* ===== TOP BAR ===== */}
      <header className="topbar">
        <Link to="/" className="topbar-brand" title="Home">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 1, fontFamily: 'var(--font-serif)' }}>
            <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.5px' }}>PH</span>
            <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-text)', letterSpacing: '-0.5px' }}>RD</span>
          </div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              lineHeight: 1.1,
              borderLeft: '1px solid var(--border2)',
              paddingLeft: 10,
            }}
          >
            <span style={{ fontSize: 9, letterSpacing: 1.5, color: 'var(--text3)', textTransform: 'uppercase' }}>
              Research
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', fontFamily: 'var(--font-serif)' }}>
              Georgia CON
            </span>
          </div>
        </Link>

        <div className="topbar-search-wrap">
          <form className="topbar-search" onSubmit={runSearch}>
            <select value={scope} onChange={(e) => onScopeChange(e.target.value)} aria-label="Search scope">
              {Object.entries(SCOPE_DEFS).map(([id, def]) => (
                <option key={id} value={id}>
                  {def.label}
                </option>
              ))}
            </select>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search terms, citation, case name, or section (e.g. O.C.G.A. 31-6-44)"
            />
            <button type="submit" className="btn-search">
              <SearchIcon />
              Search
            </button>
          </form>
          <Link
            to="/search/new"
            style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '7px 10px', color: 'var(--text2)', fontSize: 12 }}
          >
            <Ic d={ICONS.advanced} size={13} />
            Advanced
          </Link>
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <button
            className="topbar-iconbtn"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          >
            <ThemeIcon theme={theme} />
          </button>
          <button className="topbar-iconbtn" onClick={() => navigate('/alerts')} title="Alerts">
            <BellIcon />
            <span
              style={{
                position: 'absolute',
                top: 14,
                right: 8,
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: 'var(--brand-red)',
              }}
            />
          </button>
          <div style={{ position: 'relative', alignSelf: 'stretch' }}>
            <button
              onClick={() => setUserMenuOpen((v) => !v)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 9,
                padding: '0 16px 0 18px',
                height: '100%',
                borderLeft: '1px solid var(--surface2)',
                background: userMenuOpen ? 'var(--surface2)' : 'transparent',
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: 'var(--brand-red)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  fontWeight: 600,
                  fontSize: 11,
                  fontFamily: 'var(--font-serif)',
                  flexShrink: 0,
                }}
              >
                {userInitials}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2, textAlign: 'left' }}>
                <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: 500 }}>{userName}</span>
                <span style={{ fontSize: 10, color: 'var(--text3)' }}>{userSubtitle}</span>
              </div>
              <svg
                width="10"
                height="10"
                viewBox="0 0 16 16"
                style={{
                  color: 'var(--text3)',
                  flexShrink: 0,
                  transform: userMenuOpen ? 'rotate(180deg)' : 'none',
                }}
                aria-hidden
              >
                <path d="M4 6 L8 10 L12 6" stroke="currentColor" strokeWidth={1.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {userMenuOpen && (
              <>
                <button className="menu-overlay" tabIndex={-1} onClick={() => setUserMenuOpen(false)} aria-label="Close menu" />
                <div className="user-menu">
                  <div style={{ padding: '9px 10px 10px', marginBottom: 4, borderBottom: '1px solid var(--surface2)' }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{userName}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{userSubtitle}</div>
                  </div>
                  <button
                    className="user-menu-item"
                    onClick={() => {
                      setUserMenuOpen(false);
                      showToast('Personalization — coming in phase 2');
                    }}
                  >
                    <span style={{ color: 'var(--text2)', display: 'inline-flex' }}>
                      <Ic d="M8 3 A2.5 2.5 0 1 1 7.99 3 M3 14 C3 10.5 5.2 9 8 9 C10.8 9 13 10.5 13 14" />
                    </span>
                    Personalization
                  </button>
                  <button
                    className="user-menu-item"
                    onClick={() => {
                      setUserMenuOpen(false);
                      showToast('Settings — coming in phase 2');
                    }}
                  >
                    <span style={{ color: 'var(--text2)', display: 'inline-flex' }}>
                      <Ic d="M8 5.8 A2.2 2.2 0 1 1 7.99 5.8 M8 2.5 L8 4.2 M8 11.8 L8 13.5 M13.5 8 L11.8 8 M4.2 8 L2.5 8 M11.8 4.2 L10.6 5.4 M5.4 10.6 L4.2 11.8 M11.8 11.8 L10.6 10.6 M5.4 5.4 L4.2 4.2" />
                    </span>
                    Settings
                  </button>
                  <div style={{ height: 1, background: 'var(--surface2)', margin: '5px 2px' }} />
                  <button
                    className="user-menu-item danger"
                    onClick={() => {
                      setUserMenuOpen(false);
                      window.location.href = '/.auth/logout';
                    }}
                  >
                    <Ic d="M6.5 2.5 L3.5 2.5 L3.5 13.5 L6.5 13.5 M10.5 5 L13.5 8 L10.5 11 M13 8 L6.5 8" />
                    Log Out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ===== BODY ===== */}
      <div className="app-body">
        {/* ===== LEFT RAIL ===== */}
        <nav className="left-rail">
          <div style={{ padding: '2px 0 10px' }}>
            {NAV_GROUPS.map((g) => {
              const inGroup = activeParent === g.id;
              const isActiveLanding =
                inGroup && activeChild == null && (g.id === 'home' ? location.pathname === '/' : true);
              const open = g.children ? inGroup || !!expandedNav[g.id] : false;
              return (
                <div key={g.id} style={{ marginBottom: 1 }}>
                  <button
                    className={`nav-group-btn${inGroup ? ' in-group' : ''}${isActiveLanding ? ' active-landing' : ''}`}
                    onClick={() => {
                      if (g.children) setExpandedNav((s) => ({ ...s, [g.id]: true }));
                      navigate(g.to);
                    }}
                  >
                    <span
                      style={{
                        width: 16,
                        height: 16,
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: inGroup ? 'var(--accent-text)' : 'var(--text2)',
                      }}
                    >
                      <Ic d={g.icon} />
                    </span>
                    <span style={{ flex: 1 }}>{g.label}</span>
                    {g.children && (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedNav((s) => ({ ...s, [g.id]: !open }));
                        }}
                        style={{ display: 'inline-flex', padding: 3, margin: -3, color: 'var(--text3)' }}
                      >
                        <Chevron open={open} />
                      </span>
                    )}
                  </button>
                  {g.children && open && (
                    <div style={{ padding: '1px 0 6px' }}>
                      {g.children.map((c) => {
                        const active = inGroup && activeChild === c.id;
                        return (
                          <button
                            key={c.id}
                            className={`nav-child-btn${active ? ' active' : ''}`}
                            onClick={() => navigate(c.to)}
                          >
                            <span
                              style={{
                                width: 5,
                                height: 5,
                                borderRadius: '50%',
                                background: active ? 'currentColor' : 'var(--text3)',
                                flexShrink: 0,
                              }}
                            />
                            <span style={{ flex: 1 }}>{c.label}</span>
                            {c.count != null && (
                              <span style={{ fontSize: 11, color: 'var(--text2)', fontVariantNumeric: 'tabular-nums' }}>
                                {c.count}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </nav>

        {/* ===== MAIN ===== */}
        <main className="app-main" ref={mainRef}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

/** Small helper used across views for section headings. */
export function SectionHead({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <div className="section-head">
      <h2 className="section-title">{title}</h2>
      {right && <span style={{ fontSize: 11, color: 'var(--text3)' }}>{right}</span>}
    </div>
  );
}
