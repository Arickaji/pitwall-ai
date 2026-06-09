'use client';

import { useState, useEffect } from 'react';
import { useRace } from '@/context/RaceContext';
import { api, LapRecord, DegradationRecord } from '@/lib/api';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const COMPOUND_COLORS: Record<string, string> = {
  SOFT: '#FF3333', MEDIUM: '#FFD700', HARD: '#CCCCCC',
  INTER: '#39B54A', WET: '#0067FF', UNKNOWN: '#888888',
};

const DRIVER_COLORS = [
  '#00D2BE', '#FF1E00', '#FFD700', '#FF8000', '#00FF87',
  '#0090FF', '#DC0000', '#006F62', '#B6BABD', '#1E41FF',
];

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

export default function StrategyPage() {
  const { session } = useRace();
  const [laps, setLaps] = useState<LapRecord[]>([]);
  const [degradation, setDegradation] = useState<DegradationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [driver1, setDriver1] = useState('VER');
  const [driver2, setDriver2] = useState('HAM');
  const [scanLap, setScanLap] = useState(20);
  const [scanning, setScanning] = useState(false);
  const [undercutData, setUndercutData] = useState<any[]>([]);

  useEffect(() => {
    if (!session.loaded) return;
    loadData();
  }, [session.loaded, session.year, session.gp, session.session]);

  async function loadData() {
    setLoading(true);
    try {
      const [lapsRes, degRes] = await Promise.all([
        api.getLaps(session.year, session.gp, session.session, 1, 200),
        api.getDegradation(session.year, session.gp, session.session),
      ]);

      const allLaps = [...lapsRes.data];
      for (let p = 2; p <= Math.min(lapsRes.meta.total_pages, 10); p++) {
        const res = await api.getLaps(session.year, session.gp, session.session, p, 200);
        allLaps.push(...res.data);
      }

      setLaps(allLaps);
      setDegradation(degRes.data);

      const drivers = [...new Set(allLaps.map(l => l.driver))].sort();
      if (drivers.length >= 2) {
        setDriver1(drivers.includes('VER') ? 'VER' : drivers[0]);
        setDriver2(drivers.includes('HAM') ? 'HAM' : drivers[1]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function runUndercutScan() {
    setScanning(true);
    try {
      const totalLaps = Math.max(...laps.map(l => l.lap_number));
      const data = await api.scanUndercut(
        session.year,
        session.gp,
        session.session,
        scanLap,
        totalLaps - scanLap,
      );
      setUndercutData(data.data);
    } catch (e) {
      console.error(e);
    } finally {
      setScanning(false);
    }
  }

  if (!session.loaded) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '70vh' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '12px', letterSpacing: '3px', color: '#8B8B9E' }}>
          SELECT A SESSION AND CLICK LOAD
        </div>
      </div>
    );
  }

  const allDrivers = [...new Set(laps.map(l => l.driver))].sort();
  const totalLaps  = Math.max(...laps.map(l => l.lap_number), 57);

  // Gap evolution
  const d1Laps = laps.filter(l => l.driver === driver1 && l.is_accurate).sort((a, b) => a.lap_number - b.lap_number);
  const d2Laps = laps.filter(l => l.driver === driver2 && l.is_accurate).sort((a, b) => a.lap_number - b.lap_number);

  const commonLaps = d1Laps
    .map(l1 => {
      const l2 = d2Laps.find(l => l.lap_number === l1.lap_number);
      return l2 ? { lap: l1.lap_number, delta: l1.lap_time_seconds - l2.lap_time_seconds } : null;
    })
    .filter(Boolean) as { lap: number; delta: number }[];

  let cumGap = 0;
  const gapData = commonLaps.map(({ lap, delta }) => {
    cumGap += delta;
    return { lap, gap: cumGap };
  });

  // Stint bars
  const stintTraces: any[] = [];
  allDrivers.slice(0, 10).forEach(driver => {
    const driverLaps = laps.filter(l => l.driver === driver).sort((a, b) => a.lap_number - b.lap_number);
    let currentStint = 0, stintStart = 0, currentComp = '';

    driverLaps.forEach((lap, idx) => {
      if (lap.stint !== currentStint || idx === 0) {
        if (currentStint > 0) {
          stintTraces.push({
            type: 'bar', orientation: 'h',
            y: [driver], x: [lap.lap_number - stintStart],
            base: stintStart,
            marker: { color: COMPOUND_COLORS[currentComp] || '#888' },
            showlegend: false,
            hovertemplate: `<b>${driver}</b><br>${currentComp}<br>Laps ${stintStart}–${lap.lap_number - 1}<extra></extra>`,
          });
        }
        currentStint = lap.stint; stintStart = lap.lap_number; currentComp = lap.compound;
      }
    });
    const last = driverLaps[driverLaps.length - 1];
    if (last) {
      stintTraces.push({
        type: 'bar', orientation: 'h',
        y: [driver], x: [last.lap_number - stintStart + 1],
        base: stintStart,
        marker: { color: COMPOUND_COLORS[currentComp] || '#888' },
        showlegend: false,
        hovertemplate: `<b>${driver}</b><br>${currentComp}<br>Laps ${stintStart}–${last.lap_number}<extra></extra>`,
      });
    }
  });

  return (
    <div style={{ padding: '24px 40px', maxWidth: '1600px', margin: '0 auto' }}>

      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '4px' }}>
          STRATEGY ANALYSIS
        </div>
        <h1 style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#FFFFFF' }}>
          {session.year} {session.gp}
          <span style={{ color: '#00D2BE', marginLeft: '12px', fontSize: '16px' }}>— STRATEGY</span>
        </h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>

        {/* Gap Evolution */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="GAP EVOLUTION" />
          <div style={{ padding: '16px 20px', display: 'flex', gap: '12px', alignItems: 'center', borderBottom: '1px solid #1E1E2E' }}>
            <select value={driver1} onChange={e => setDriver1(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: '12px', padding: '6px 12px', background: '#0A0A0F', border: '1px solid #00D2BE', color: '#00D2BE' }}>
              {allDrivers.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <span style={{ color: '#8B8B9E', fontFamily: 'monospace', fontSize: '11px' }}>VS</span>
            <select value={driver2} onChange={e => setDriver2(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: '12px', padding: '6px 12px', background: '#0A0A0F', border: '1px solid #FF1E00', color: '#FF1E00' }}>
              {allDrivers.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <Plot
            data={[{
              x: gapData.map(g => g.lap),
              y: gapData.map(g => g.gap),
              mode: 'lines',
              fill: 'tozeroy',
              fillcolor: 'rgba(0,210,190,0.1)',
              line: { color: '#00D2BE', width: 2 },
              hovertemplate: 'Lap %{x}<br>Gap: %{y:.3f}s<extra></extra>',
            }]}
            layout={{
              ...PLOTLY_LAYOUT,
              height: 300,
              shapes: [{ type: 'line', x0: 0, x1: totalLaps, y0: 0, y1: 0, line: { color: '#FF1E00', dash: 'dash', width: 1 } }],
              annotations: [{ x: totalLaps * 0.1, y: 0, text: 'OVERTAKE LINE', font: { color: '#FF1E00', size: 9, family: 'monospace' }, showarrow: false, yshift: 10 }],
              xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'LAP', font: { color: '#8B8B9E', size: 10 } } },
              yaxis: { ...PLOTLY_LAYOUT.yaxis, title: { text: 'GAP (s)', font: { color: '#8B8B9E', size: 10 } } },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
        </div>

        {/* Degradation Rates */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="DEGRADATION RATES" />
          <div style={{ overflowY: 'auto', maxHeight: '360px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '11px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1E1E2E' }}>
                  {['DRIVER', 'COMPOUND', 'STINT', 'DEG RATE', 'R²', 'CLIFF'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#8B8B9E', fontSize: '9px', letterSpacing: '1px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {degradation.slice(0, 20).map((row, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #1E1E2E' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#1E1E2E')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                    <td style={{ padding: '8px 12px', color: '#FFFFFF', fontWeight: '700' }}>{row.driver}</td>
                    <td style={{ padding: '8px 12px', color: COMPOUND_COLORS[row.compound] || '#888' }}>{row.compound}</td>
                    <td style={{ padding: '8px 12px', color: '#8B8B9E' }}>{row.stint}</td>
                    <td style={{ padding: '8px 12px', color: row.degradation_rate > 0.05 ? '#FF1E00' : '#00FF87' }}>
                      {row.degradation_rate.toFixed(4)}s/lap
                    </td>
                    <td style={{ padding: '8px 12px', color: '#8B8B9E' }}>{row.r_squared.toFixed(3)}</td>
                    <td style={{ padding: '8px 12px', color: '#FFB800' }}>{row.cliff_lap ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Stint Strategy */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E', marginBottom: '16px' }}>
        <SectionHeader title="STINT STRATEGY — FULL FIELD" />
        <Plot
          data={stintTraces}
          layout={{
            ...PLOTLY_LAYOUT,
            barmode: 'stack',
            height: Math.max(300, allDrivers.slice(0, 10).length * 45 + 60),
            xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'LAP', font: { color: '#8B8B9E', size: 10 } } },
            yaxis: { ...PLOTLY_LAYOUT.yaxis, automargin: true },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
        <div style={{ padding: '12px 20px', display: 'flex', gap: '16px', borderTop: '1px solid #1E1E2E' }}>
          {Object.entries(COMPOUND_COLORS).slice(0, 3).map(([compound, color]) => (
            <div key={compound} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '10px', height: '10px', background: color }} />
              <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E' }}>{compound}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Undercut Scanner */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
        <SectionHeader title="UNDERCUT OPPORTUNITY SCANNER" />
        <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid #1E1E2E' }}>
          <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>SCAN AT LAP</div>
          <input
            type="range"
            min={5} max={totalLaps - 5} value={scanLap}
            onChange={e => setScanLap(+e.target.value)}
            style={{ flex: 1, accentColor: '#00D2BE' }}
          />
          <div style={{ fontFamily: 'monospace', fontSize: '16px', fontWeight: '700', color: '#00D2BE', minWidth: '40px' }}>
            {scanLap}
          </div>
          <button onClick={runUndercutScan} disabled={scanning}
            style={{
              fontFamily: 'monospace', fontSize: '11px', fontWeight: '700',
              letterSpacing: '2px', padding: '8px 24px',
              background: scanning ? '#1E1E2E' : '#00D2BE',
              color: scanning ? '#8B8B9E' : '#0A0A0F',
              border: 'none', cursor: scanning ? 'not-allowed' : 'pointer',
            }}>
            {scanning ? 'SCANNING...' : '⚡ SCAN'}
          </button>
        </div>

        {undercutData.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '11px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1E1E2E' }}>
                {['DRIVER', 'RIVAL', 'CURRENT GAP', 'PACE DELTA', 'LAPS TO COMPLETE', 'GAP AFTER STOP'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#8B8B9E', fontSize: '9px', letterSpacing: '1px' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {undercutData.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1E1E2E', background: i === 0 ? '#00D2BE10' : 'transparent' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#1E1E2E')}
                  onMouseLeave={e => (e.currentTarget.style.background = i === 0 ? '#00D2BE10' : 'transparent')}>
                  <td style={{ padding: '10px 16px', color: '#FFFFFF', fontWeight: '700' }}>{row.driver}</td>
                  <td style={{ padding: '10px 16px', color: '#8B8B9E' }}>{row.rival}</td>
                  <td style={{ padding: '10px 16px', color: '#FFB800' }}>{row.gap.toFixed(3)}s</td>
                  <td style={{ padding: '10px 16px', color: row.pace_delta < 0 ? '#00FF87' : '#FF1E00' }}>
                    {row.pace_delta > 0 ? '+' : ''}{row.pace_delta.toFixed(3)}s/lap
                  </td>
                  <td style={{ padding: '10px 16px', color: '#00D2BE' }}>{row.laps_to_complete.toFixed(1)} laps</td>
                  <td style={{ padding: '10px 16px', color: '#00FF87' }}>+{row.gap_after_stop.toFixed(1)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
            SELECT A LAP AND CLICK SCAN TO FIND UNDERCUT OPPORTUNITIES
          </div>
        )}
      </div>

    </div>
  );
}
