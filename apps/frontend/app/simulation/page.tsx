'use client';

import { useState } from 'react';
import { useRace } from '@/context/RaceContext';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const PLOTLY_LAYOUT = {
  paper_bgcolor: '#0A0A0F', plot_bgcolor: '#12121A',
  font: { color: '#FFFFFF', family: 'monospace', size: 11 },
  xaxis: { gridcolor: '#1E1E2E', linecolor: '#1E1E2E' },
  yaxis: { gridcolor: '#1E1E2E', linecolor: '#1E1E2E' },
  legend: { bgcolor: '#12121A', bordercolor: '#1E1E2E', borderwidth: 1 },
  margin: { l: 50, r: 20, t: 40, b: 50 },
};

function SectionHeader({ title }: { title: string }) {
  return (
    <div style={{
      fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px',
      color: '#8B8B9E', padding: '12px 20px',
      borderBottom: '1px solid #1E1E2E',
    }}>
      {title}
    </div>
  );
}

function MetricCard({ label, value, color = '#00D2BE' }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ background: '#12121A', border: '1px solid #1E1E2E', padding: '20px 24px' }}>
      <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '8px' }}>{label}</div>
      <div style={{ fontFamily: 'monospace', fontSize: '22px', fontWeight: '700', color }}>{value}</div>
    </div>
  );
}

export default function SimulationPage() {
  const { session } = useRace();

  // Monte Carlo state
  const [fromLap, setFromLap]     = useState(20);
  const [nSims, setNSims]         = useState(250);
  const [mcLoading, setMcLoading] = useState(false);
  const [mcResult, setMcResult]   = useState<any>(null);

  // Race sim state
  const [simFromLap, setSimFromLap]   = useState(20);
  const [simLoading, setSimLoading]   = useState(false);
  const [simResult, setSimResult]     = useState<any>(null);

  // Pit optimizer state
  const [optDriver, setOptDriver]     = useState('VER');
  const [optFromLap, setOptFromLap]   = useState(20);
  const [optCompound, setOptCompound] = useState('HARD');
  const [optLoading, setOptLoading]   = useState(false);
  const [optResult, setOptResult]     = useState<any>(null);

  if (!session.loaded) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '70vh' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '12px', letterSpacing: '3px', color: '#8B8B9E' }}>
          SELECT A SESSION AND CLICK LOAD
        </div>
      </div>
    );
  }

  async function runMonteCarlo() {
    setMcLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulate/monte-carlo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: session.year, gp: session.gp,
          session_type: session.session,
          from_lap: fromLap, n_simulations: nSims,
        }),
      });
      setMcResult(await res.json());
    } catch (e) { console.error(e); }
    finally { setMcLoading(false); }
  }

  async function runSimulation() {
    setSimLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulate/race', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: session.year, gp: session.gp,
          session_type: session.session, from_lap: simFromLap,
        }),
      });
      setSimResult(await res.json());
    } catch (e) { console.error(e); }
    finally { setSimLoading(false); }
  }

  async function runOptimizer() {
    setOptLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/simulate/pit-optimizer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: session.year, gp: session.gp,
          session_type: session.session,
          driver: optDriver, from_lap: optFromLap,
          new_compound: optCompound,
        }),
      });
      setOptResult(await res.json());
    } catch (e) { console.error(e); }
    finally { setOptLoading(false); }
  }

  const mcDrivers = mcResult?.win_probabilities?.filter((d: any) => d.win_probability > 0) || [];

  return (
    <div style={{ padding: '24px 40px', maxWidth: '1600px', margin: '0 auto' }}>

      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '4px' }}>
          SIMULATION ENGINE
        </div>
        <h1 style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#FFFFFF' }}>
          {session.year} {session.gp}
          <span style={{ color: '#00D2BE', marginLeft: '12px', fontSize: '16px' }}>— SIMULATION</span>
        </h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>

        {/* Monte Carlo */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="MONTE CARLO SIMULATION" />

          <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E', display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>FROM LAP</label>
              <input type="number" min={1} max={55} value={fromLap}
                onChange={e => setFromLap(+e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '14px', fontWeight: '700', width: '70px', padding: '6px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#00D2BE' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>SIMULATIONS</label>
              <select value={nSims} onChange={e => setNSims(+e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '12px', padding: '6px 12px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#FFFFFF' }}>
                {[100, 250, 500, 1000].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <button onClick={runMonteCarlo} disabled={mcLoading}
              style={{
                fontFamily: 'monospace', fontSize: '11px', fontWeight: '700',
                letterSpacing: '2px', padding: '10px 24px', marginTop: '16px',
                background: mcLoading ? '#1E1E2E' : '#00D2BE',
                color: mcLoading ? '#8B8B9E' : '#0A0A0F',
                border: 'none', cursor: mcLoading ? 'not-allowed' : 'pointer',
              }}>
              {mcLoading ? 'RUNNING...' : '🎲 RUN'}
            </button>
          </div>

          {mcResult ? (
            <>
              <Plot
                data={[{
                  type: 'bar',
                  x: mcDrivers.map((d: any) => d.driver),
                  y: mcDrivers.map((d: any) => d.win_probability),
                  marker: {
                    color: mcDrivers.map((d: any) =>
                      d.win_probability > 50 ? '#FFD700' :
                      d.win_probability > 20 ? '#00D2BE' : '#1E1E2E'
                    ),
                  },
                  text: mcDrivers.map((d: any) => `${d.win_probability.toFixed(1)}%`),
                  textposition: 'outside',
                  textfont: { color: '#FFFFFF', family: 'monospace', size: 10 },
                  hovertemplate: '<b>%{x}</b><br>Win: %{y:.1f}%<extra></extra>',
                }]}
                layout={{
                  ...PLOTLY_LAYOUT,
                  height: 280,
                  yaxis: { ...PLOTLY_LAYOUT.yaxis, range: [0, 100], title: { text: 'WIN %', font: { color: '#8B8B9E', size: 10 } } },
                  xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'DRIVER', font: { color: '#8B8B9E', size: 10 } } },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
              <div style={{ padding: '12px 20px', borderTop: '1px solid #1E1E2E', fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E' }}>
                {mcResult.n_simulations} simulations from lap {fromLap} — winner: <span style={{ color: '#FFD700' }}>{mcDrivers[0]?.driver}</span> ({mcDrivers[0]?.win_probability.toFixed(1)}%)
              </div>
            </>
          ) : (
            <div style={{ padding: '60px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
              SET LAP AND RUN SIMULATION
            </div>
          )}
        </div>

        {/* Pit Optimizer */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="PIT STOP OPTIMIZER" />

          <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E', display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>DRIVER</label>
              <input value={optDriver} onChange={e => setOptDriver(e.target.value.toUpperCase())}
                maxLength={3}
                style={{ fontFamily: 'monospace', fontSize: '14px', fontWeight: '700', width: '70px', padding: '6px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#00D2BE' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>FROM LAP</label>
              <input type="number" min={1} max={50} value={optFromLap}
                onChange={e => setOptFromLap(+e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '14px', fontWeight: '700', width: '70px', padding: '6px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#00D2BE' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>NEW COMPOUND</label>
              <select value={optCompound} onChange={e => setOptCompound(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '12px', padding: '6px 12px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#FFFFFF' }}>
                {['SOFT', 'MEDIUM', 'HARD'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <button onClick={runOptimizer} disabled={optLoading}
              style={{
                fontFamily: 'monospace', fontSize: '11px', fontWeight: '700',
                letterSpacing: '2px', padding: '10px 24px',
                background: optLoading ? '#1E1E2E' : '#FFD700',
                color: optLoading ? '#8B8B9E' : '#0A0A0F',
                border: 'none', cursor: optLoading ? 'not-allowed' : 'pointer',
              }}>
              {optLoading ? 'OPTIMIZING...' : '⚡ OPTIMIZE'}
            </button>
          </div>

          {optResult ? (
            <>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '8px' }}>OPTIMAL PIT LAP</div>
                <div style={{ fontFamily: 'monospace', fontSize: '36px', fontWeight: '900', color: '#FFD700' }}>
                  LAP {optResult.optimal_lap}
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E', marginTop: '4px' }}>
                  {optResult.recommendation}
                </div>
              </div>
              <div style={{ overflowY: 'auto', maxHeight: '220px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1E1E2E' }}>
                      {['PIT LAP', 'PROJ POS', 'GAP AHEAD', 'COMPOUND', 'SCORE'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#8B8B9E', fontSize: '9px', letterSpacing: '1px' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {optResult.all_options?.map((row: any, i: number) => (
                      <tr key={i} style={{ borderBottom: '1px solid #1E1E2E', background: row.pit_lap === optResult.optimal_lap ? '#FFD70010' : 'transparent' }}>
                        <td style={{ padding: '8px 12px', color: row.pit_lap === optResult.optimal_lap ? '#FFD700' : '#FFFFFF', fontWeight: row.pit_lap === optResult.optimal_lap ? '700' : '400' }}>
                          {row.pit_lap === optResult.optimal_lap ? '★ ' : ''}{row.pit_lap}
                        </td>
                        <td style={{ padding: '8px 12px', color: '#00D2BE' }}>P{row.projected_position}</td>
                        <td style={{ padding: '8px 12px', color: '#8B8B9E' }}>{row.gap_to_ahead?.toFixed(1)}s</td>
                        <td style={{ padding: '8px 12px', color: '#8B8B9E' }}>{row.compound}</td>
                        <td style={{ padding: '8px 12px', color: '#8B8B9E' }}>{row.score?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div style={{ padding: '60px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
              SELECT DRIVER AND RUN OPTIMIZER
            </div>
          )}
        </div>
      </div>

      {/* Race Simulator */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
        <SectionHeader title="RACE SIMULATOR" />
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E', display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>SIMULATE FROM LAP</label>
            <input type="number" min={1} max={55} value={simFromLap}
              onChange={e => setSimFromLap(+e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: '14px', fontWeight: '700', width: '80px', padding: '6px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#00D2BE' }} />
          </div>
          <button onClick={runSimulation} disabled={simLoading}
            style={{
              fontFamily: 'monospace', fontSize: '11px', fontWeight: '700',
              letterSpacing: '2px', padding: '10px 24px',
              background: simLoading ? '#1E1E2E' : '#00D2BE',
              color: simLoading ? '#8B8B9E' : '#0A0A0F',
              border: 'none', cursor: simLoading ? 'not-allowed' : 'pointer',
            }}>
            {simLoading ? 'SIMULATING...' : '▶ SIMULATE RACE'}
          </button>
        </div>

        {simResult ? (
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '0' }}>
            {/* Standings */}
            <div style={{ borderRight: '1px solid #1E1E2E' }}>
              <div style={{ padding: '10px 16px', borderBottom: '1px solid #1E1E2E', fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>
                FINAL STANDINGS
              </div>
              {simResult.final_standings?.map((row: any, i: number) => (
                <div key={i} style={{
                  padding: '10px 16px',
                  borderBottom: '1px solid #1E1E2E',
                  display: 'flex', alignItems: 'center', gap: '12px',
                  background: i === 0 ? '#FFD70008' : 'transparent',
                }}>
                  <span style={{
                    fontFamily: 'monospace', fontSize: '12px', fontWeight: '700', minWidth: '24px',
                    color: i === 0 ? '#FFD700' : i === 1 ? '#C0C0C0' : i === 2 ? '#CD7F32' : '#8B8B9E',
                  }}>
                    P{row.position}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '12px', fontWeight: '700', color: '#FFFFFF', flex: 1 }}>
                    {row.driver}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E' }}>
                    {row.gap_to_leader === 0 ? 'WINNER' : `+${row.gap_to_leader.toFixed(1)}s`}
                  </span>
                </div>
              ))}
            </div>

            {/* Winner callout */}
            <div style={{ padding: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '12px' }}>
                🏁 SIMULATED WINNER
              </div>
              <div style={{ fontFamily: 'monospace', fontSize: '80px', fontWeight: '900', color: '#FFD700', lineHeight: '1' }}>
                {simResult.winner}
              </div>
              <div style={{ fontFamily: 'monospace', fontSize: '12px', color: '#8B8B9E', marginTop: '16px' }}>
                Simulated from lap {simFromLap} — {simResult.final_standings?.length} drivers
              </div>
            </div>
          </div>
        ) : (
          <div style={{ padding: '60px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
            SET LAP AND RUN RACE SIMULATION
          </div>
        )}
      </div>

    </div>
  );
}
