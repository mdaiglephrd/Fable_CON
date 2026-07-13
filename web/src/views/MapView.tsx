/*
 * SERVICE-AREA MAP (/map) — docket activity by county: a stylized tile
 * choropleth of all 159 Georgia counties (metric-bucketed fills, county
 * abbreviations), metric tabs (volume / denial rate), legend, and the
 * top-counties rail. Extends the comp's <!-- SERVICE-AREA MAP --> regional
 * grid to the full county roster; the 24 curated counties keep the comp's
 * figures and the rest are seeded deterministically (docketEngine.seedOf).
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { seedOf } from '../lib/docketEngine';
import { COUNTIES } from '../lib/vocab';

type Metric = 'volume' | 'denial';

/** The comp's curated counties: [name, region, dockets, denialPct]. */
const CURATED: [string, string, number, number][] = [
  ['Fulton', 'Metro Atlanta', 142, 22], ['DeKalb', 'Metro Atlanta', 98, 28], ['Cobb', 'Metro Atlanta', 87, 19],
  ['Gwinnett', 'Metro Atlanta', 81, 24], ['Chatham', 'Coastal', 54, 18], ['Bibb', 'Central', 47, 31],
  ['Richmond', 'CSRA', 44, 26], ['Muscogee', 'West', 41, 23], ['Hall', 'Northeast', 38, 17],
  ['Clarke', 'Northeast', 33, 20], ['Houston', 'Central', 29, 14], ['Lowndes', 'South', 27, 33],
  ['Floyd', 'Northwest', 26, 29], ['Dougherty', 'Southwest', 24, 38], ['Clayton', 'Metro Atlanta', 23, 35],
  ['Bartow', 'Northwest', 21, 41], ['Henry', 'Metro Atlanta', 19, 16], ['Forsyth', 'Metro Atlanta', 18, 44],
  ['Glynn', 'Coastal', 17, 21], ['Whitfield', 'Northwest', 16, 27], ['Troup', 'West', 14, 25],
  ['Cherokee', 'Metro Atlanta', 13, 19], ['Carroll', 'West', 11, 30], ['Tift', 'South', 9, 28],
];

interface CountyDatum {
  name: string;
  region: string;
  volume: number;
  denial: number;
}

/** All 159 counties: curated figures where authored, seeded elsewhere. */
function buildCounties(): CountyDatum[] {
  const curated = new Map(CURATED.map(([name, region, volume, denial]) => [name, { region, volume, denial }]));
  return COUNTIES.map((name) => {
    const hit = curated.get(name);
    if (hit) return { name, ...hit };
    return {
      name,
      region: 'Georgia',
      volume: Math.round(seedOf(name) * 8) + 1,
      denial: Math.round(seedOf(`${name}-denial`) * 40) + 8,
    };
  });
}

function shade(ratio: number): string {
  if (ratio > 0.8) return '#8E1B1F';
  if (ratio > 0.55) return '#A82127';
  if (ratio > 0.32) return '#C97A5A';
  if (ratio > 0.14) return '#E4B9A0';
  return 'var(--surface2)';
}

function shadeText(ratio: number): string {
  return ratio > 0.32 ? '#F8FAFC' : 'var(--text2)';
}

const METRIC_TABS: { id: Metric; label: string }[] = [
  { id: 'volume', label: 'Docket volume' },
  { id: 'denial', label: 'Denial rate' },
];

export default function MapView() {
  const [metric, setMetric] = useState<Metric>('volume');
  const counties = useMemo(buildCounties, []);

  const valueOf = (c: CountyDatum) => (metric === 'volume' ? c.volume : c.denial);
  const max = Math.max(...counties.map(valueOf));
  const top = [...counties].sort((a, b) => valueOf(b) - valueOf(a)).slice(0, 7);

  return (
    <section>
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Service-Area Map' }]}
        title="Docket Activity by County"
        sub="CON activity concentration across Georgia service areas — all 159 counties"
        right={
          <div style={{ display: 'flex', gap: 8 }}>
            {METRIC_TABS.map((t) => (
              <button key={t.id} className={`chip-tab${metric === t.id ? ' active' : ''}`} onClick={() => setMetric(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
        }
      />

      <div style={{ padding: '28px 32px 60px', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 300px', gap: 24, maxWidth: 1320 }}>
        {/* Tile choropleth */}
        <div className="card" style={{ padding: 24 }}>
          <div className="label-upper" style={{ letterSpacing: 1.4, marginBottom: 18 }}>
            Georgia · 159 counties · {metric === 'volume' ? 'dockets on the roll' : 'share of applications denied'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(58px, 1fr))', gap: 6 }}>
            {counties.map((c) => {
              const v = valueOf(c);
              const ratio = v / max;
              return (
                <Link
                  key={c.name}
                  to={`/results?q=${encodeURIComponent(`county:${c.name}`)}&scope=all`}
                  title={`${c.name} County — ${c.volume} dockets, ${c.denial}% denied`}
                  style={{
                    aspectRatio: '1',
                    borderRadius: 2,
                    background: shade(ratio),
                    border: '1px solid rgba(0,0,0,.06)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 4,
                    minWidth: 0,
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, color: shadeText(ratio), lineHeight: 1.1, textAlign: 'center', textTransform: 'uppercase', letterSpacing: 0.4 }}>
                    {c.name.replace(/[^A-Za-z]/g, '').slice(0, 4)}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: shadeText(ratio), fontVariantNumeric: 'tabular-nums' }}>
                    {metric === 'volume' ? v : `${v}%`}
                  </span>
                </Link>
              );
            })}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 20, fontSize: 11, color: 'var(--text2)' }}>
            <span>Fewer</span>
            <div style={{ display: 'flex', gap: 2 }}>
              {['var(--surface2)', '#E4B9A0', '#C97A5A', '#A82127', '#8E1B1F'].map((bg) => (
                <span key={bg} style={{ width: 22, height: 12, background: bg, borderRadius: 1 }} />
              ))}
            </div>
            <span>More</span>
            <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text3)', fontStyle: 'italic' }}>
              Stylized tile map — hover a county for both metrics; click to search its dockets.
            </span>
          </div>
        </div>

        {/* Top counties */}
        <div className="card" style={{ padding: 20, alignSelf: 'start' }}>
          <h2 className="label-upper" style={{ color: 'var(--text)', letterSpacing: 1.4, margin: '0 0 14px', paddingBottom: 10, borderBottom: '2px solid var(--border2)' }}>
            Top counties
          </h2>
          {top.map((c) => (
            <div key={c.name} className="list-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 0' }}>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600 }}>{c.name} County</div>
                <div style={{ fontSize: 11, color: 'var(--text2)' }}>{c.region}</div>
              </div>
              <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent-text)', fontVariantNumeric: 'tabular-nums' }}>
                {metric === 'volume' ? c.volume : `${c.denial}%`}
              </div>
            </div>
          ))}
          <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text3)', lineHeight: 1.5 }}>
            Figures for the 24 highest-activity counties follow the published DCH project lists; remaining counties carry representative
            sample values until the live docket database is connected.
          </div>
        </div>
      </div>
    </section>
  );
}
