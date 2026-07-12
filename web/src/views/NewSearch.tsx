/*
 * NEW SEARCH (/search/new) — the advanced structured query builder: term
 * fields (all words / exact phrase / any / none), filter selects (docket
 * type, forum, outcome, county, dates), and the connectors sidebar. Running
 * the search navigates to /results with the composed query + facet
 * preselection (?f=dim|val,…). From the comp's <!-- NEW SEARCH --> section.
 */
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { DOCKET_FAMILIES } from '../lib/vocab';

const FORUMS = ['DCH Planning', 'OSAH', 'DCH Commissioner', 'Superior Court', 'Ga. Ct. App.', 'Ga. Sup. Ct.'];
const OUTCOMES = ['Granted', 'Denied', 'Reversed', 'Affirmed', 'Dismissed'];
const COUNTIES_SHORT = ['Bartow', 'Fulton', 'DeKalb', 'Cobb', 'Forsyth', 'Chatham', 'Hall'];

export default function NewSearch() {
  const navigate = useNavigate();
  const [allWords, setAllWords] = useState('');
  const [phrase, setPhrase] = useState('');
  const [anyWords, setAnyWords] = useState('');
  const [noneWords, setNoneWords] = useState('');
  const [dktType, setDktType] = useState('');
  const [forum, setForum] = useState('');
  const [outcome, setOutcome] = useState('');
  const [county, setCounty] = useState('');

  const run = (e?: FormEvent) => {
    e?.preventDefault();
    const q = [allWords.trim(), phrase.trim() && `"${phrase.trim()}"`, anyWords.trim(), county.trim()]
      .filter(Boolean)
      .join(' ');
    const facets = [
      dktType && `dkt|${dktType}`,
      forum && `forum|${forum}`,
      outcome && `outcome|${outcome}`,
    ].filter(Boolean);
    const params = new URLSearchParams({ q, scope: 'all' });
    if (facets.length) params.set('f', facets.join(','));
    navigate(`/results?${params.toString()}`);
  };

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Research', to: '/research' }, { label: 'Quick Search' }]}
        title="Quick Search"
        titleSize={26}
        sub="Build a precise query across determinations, orders, briefs, statutes, and rules."
      />
      <div style={{ padding: '28px 32px 60px' }}>
        <div style={{ maxWidth: 1080, display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24, alignItems: 'start' }}>
          <form className="card" onSubmit={run} style={{ padding: '26px 28px' }}>
            <div className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, marginBottom: 16 }}>Terms</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>All of these words</label>
                <input className="field-input" value={allWords} onChange={(e) => setAllWords(e.target.value)} placeholder="substantial evidence" />
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>This exact phrase</label>
                <input className="field-input" value={phrase} onChange={(e) => setPhrase(e.target.value)} placeholder="need methodology" />
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Any of these words</label>
                <input className="field-input" value={anyWords} onChange={(e) => setAnyWords(e.target.value)} placeholder="MRI CT PET" />
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>None of these words</label>
                <input className="field-input" value={noneWords} onChange={(e) => setNoneWords(e.target.value)} placeholder="dismissed withdrawn" />
              </div>
            </div>

            <div className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, marginBottom: 16, paddingTop: 20, borderTop: '1px solid var(--surface2)' }}>
              Filters
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Docket type</label>
                <select className="field-select" style={{ fontSize: 13 }} value={dktType} onChange={(e) => setDktType(e.target.value)}>
                  <option value="">Any</option>
                  {DOCKET_FAMILIES.map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Forum / Court</label>
                <select className="field-select" style={{ fontSize: 13 }} value={forum} onChange={(e) => setForum(e.target.value)}>
                  <option value="">Any</option>
                  {FORUMS.map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Outcome</label>
                <select className="field-select" style={{ fontSize: 13 }} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                  <option value="">Any</option>
                  {OUTCOMES.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>County</label>
                <select className="field-select" style={{ fontSize: 13 }} value={county} onChange={(e) => setCounty(e.target.value)}>
                  <option value="">Any</option>
                  {COUNTIES_SHORT.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Decided — from</label>
                <input className="field-input" type="date" style={{ fontSize: 13, padding: '9px 12px' }} />
              </div>
              <div>
                <label className="field-label" style={{ textTransform: 'none', letterSpacing: 0 }}>Decided — to</label>
                <input className="field-input" type="date" style={{ fontSize: 13, padding: '9px 12px' }} />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 18, borderTop: '1px solid var(--surface2)' }}>
              <Link to="/results?q=&scope=all" style={{ fontSize: 13, color: 'var(--text2)' }}>
                Browse all sources instead
              </Link>
              <button type="submit" className="btn-primary" style={{ padding: '11px 28px', fontSize: 14, gap: 8 }}>
                <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden>
                  <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth={1.8} fill="none" />
                  <path d="M11 11 L14 14" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
                </svg>
                Run search
              </button>
            </div>
          </form>

          <aside style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card" style={{ padding: '18px 20px' }}>
              <div className="label-upper" style={{ letterSpacing: 1.4, marginBottom: 12 }}>Search connectors</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12.5, lineHeight: 1.5 }}>
                {(
                  [
                    ['"…"', 'exact phrase'],
                    ['& / OR', 'both / either term'],
                    ['/s /p', 'same sentence / paragraph'],
                    ['!', 'root expander (deni!)'],
                  ] as const
                ).map(([code, hint]) => (
                  <div key={code} style={{ display: 'flex', gap: 10 }}>
                    <code className="mono" style={{ flexShrink: 0, color: '#F59E0B', fontSize: 11.5 }}>{code}</code>
                    <span style={{ color: 'var(--text2)' }}>{hint}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card" style={{ padding: '16px 18px' }}>
              <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.4, marginBottom: 10 }}>Field prefixes</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: 'var(--text2)', lineHeight: 1.4 }}>
                <code className="mono" style={{ color: 'var(--accent-text)' }}>docket-type:CON</code>
                <code className="mono" style={{ color: 'var(--accent-text)' }}>county:Bartow</code>
                <code className="mono" style={{ color: 'var(--accent-text)' }}>cite:31-6-44</code>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
