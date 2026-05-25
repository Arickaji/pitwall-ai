'use client';

import { useState, useEffect } from 'react';
import { useRace } from '@/context/RaceContext';
import { api, LapRecord, PaceRecord } from '@/lib/api';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// ── Constants ──────────────────────────────────────────────────────────────────

const COMPOUND_COLORS: Record<string, string> = {
  SOFT:    '#FF3333',
  MEDIUM:  '#FFD700',
  HARD:    '#CCCCCC',
  INTER:   '#39B54A',
  WET:     '#0067FF',
  UNKNOWN: '#888888',
};

const DRIVER_COLORS = [
  '#00D2BE', '#FF1E00', '#FFD700', '#FF8000', '#00FF87',
  '#0090FF', '#DC0000', '#006F62', '#B6BABD', '#1E41FF',
  '#FF3333', '#39B54A', '#FFB800', '#6692FF', '#52E252',
];

const PLOTLY_LAYOUT = {
  paper_bgcolor: '#0A0A0F',
  plot_bgcolor:  '#12121A',
  font:          { color: '#FFFFFF', family: 'monospace', size: 11 },
  xaxis:         { gridcolor: '#1E1E2E', linecolor: '#1E1E2E', zerolinecolor: '#1E1E2E' },
  yaxis:         { gridcolor: '#1E1E2E', linecolor: '#1E1E2E', zerolinecolor: '#1E1E2E' },
  legend:        { bgcolor: '#12121A', bordercolor: '#1E1E2E', borderwidth: 1 },
  margin:        { l: 50, r: 20, t: 40, b: 50 },
};

// ── Components ─────────────────────────────────────────────────────────────────

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{
      background: '#12121A',
      border: '1px solid #1E1E2E',
      padding: '20px 24px',
    }}>
      <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#00D2BE' }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E', marginTop: '4px' }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function formatLapTime(seconds: number): string {
  if (!seconds) return 'N/A';
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(3).padStart(6, '0');
  return `${m}:${s}`;
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function RacePage() {
  const { session } = useRace();

  const [laps, setLaps] = useState<LapRecord[]>([]);
  const [pace, setPace] = useState<PaceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDrivers, setSelectedDrivers] = useState<string[]>([]);
  const [chartMode, setChartMode] = useState<'laptime' | 'position'>('laptime');

  useEffect(() => {
    if (!session.loaded) return;
    loadData();
  }, [session.loaded, session.year, session.gp, session.session]);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const [lapsRes, paceRes] = await Promise.all([
        api.getLaps(session.year, session.gp, session.session, 1, 200),
        api.getPace(session.year, session.gp, session.session),
      ]);

      // Load all pages
      const allLaps = [...lapsRes.data];
      const totalPages = lapsRes.meta.total_pages;

      for (let p = 2; p <= Math.min(totalPages, 10); p++) {
        const res = await api.getLaps(session.year, session.gp, session.session, p, 200);
        allLaps.push(...res.data);
      }

      setLaps(allLaps);
      setPace(paceRes.data);

      const drivers = [...new Set(allLaps.map(l => l.driver))];
      setSelectedDrivers(drivers.slice(0, 5));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Not loaded state ─────────────────────────────────────────────────────────

  if (!session.loaded) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        height: '70vh', gap: '16px',
      }}>
        <div style={{ fontFamily: 'monospace', fontSize: '48px', color: '#1E1E2E' }}>⬡</div>
        <div style={{ fontFamily: 'monospace', fontSize: '12px', letterSpacing: '3px', color: '#8B8B9E' }}>
          SELECT A SESSION AND CLICK LOAD
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        height: '70vh', gap: '16px',
      }}>
        <div style={{ fontFamily: 'monospace', fontSize: '12px', letterSpacing: '3px', color: '#00D2BE' }}>
          ● LOADING DATA...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', fontFamily: 'monospace', color: '#FF1E00' }}>
        ERROR: {error}
      </div>
    );
  }

  // ── Compute metrics ──────────────────────────────────────────────────────────

  const allDrivers = [...new Set(laps.map(l => l.driver))].sort();
  const totalLaps  = Math.max(...laps.map(l => l.lap_number));
  const fastestLap = laps.reduce((a, b) =>
    (a.lap_time_seconds || 999) < (b.lap_time_seconds || 999) ? a : b, laps[0]);
  const compounds  = [...new Set(laps.map(l => l.compound).filter(Boolean))];

  // ── Chart data ───────────────────────────────────────────────────────────────

  const lapTimeTraces = selectedDrivers.map((driver, i) => {
    const driverLaps = laps
      .filter(l => l.driver === driver && l.is_accurate && l.lap_time_seconds)
      .sort((a, b) => a.lap_number - b.lap_number);

    return {
      x: driverLaps.map(l => l.lap_number),
      y: driverLaps.map(l => l.lap_time_seconds),
      mode: 'lines',
      name: driver,
      line: { color: DRIVER_COLORS[i % DRIVER_COLORS.length], width: 2 },
      hovertemplate: `<b>${driver}</b><br>Lap %{x}<br>%{y:.3f}s<extra></extra>`,
    };
  });

  const positionTraces = selectedDrivers.map((driver, i) => {
    const driverLaps = laps
      .filter(l => l.driver === driver && l.position)
      .sort((a, b) => a.lap_number - b.lap_number);

    return {
      x: driverLaps.map(l => l.lap_number),
      y: driverLaps.map(l => l.position),
      mode: 'lines',
      name: driver,
      line: { color: DRIVER_COLORS[i % DRIVER_COLORS.length], width: 2 },
      hovertemplate: `<b>${driver}</b><br>Lap %{x}<br>P%{y}<extra></extra>`,
    };
  });

  // Stint strategy bars
  const stintTraces: any[] = [];
  const stintDrivers = selectedDrivers.slice(0, 8);

  stintDrivers.forEach(driver => {
    const driverLaps = laps.filter(l => l.driver === driver).sort((a, b) => a.lap_number - b.lap_number);
    let currentStint = 0;
    let stintStart   = 0;
    let currentComp  = '';

    driverLaps.forEach((lap, idx) => {
      if (lap.stint !== currentStint || idx === 0) {
        if (currentStint > 0) {
          stintTraces.push({
            type: 'bar',
            orientation: 'h',
            y: [driver],
            x: [lap.lap_number - stintStart],
            base: stintStart,
            marker: { color: COMPOUND_COLORS[currentComp] || '#888' },
            name: currentComp,
            showlegend: false,
            hovertemplate: `<b>${driver}</b><br>${currentComp}<br>Laps ${stintStart}–${lap.lap_number - 1}<extra></extra>`,
          });
        }
        currentStint = lap.stint;
        stintStart   = lap.lap_number;
        currentComp  = lap.compound;
      }
    });

    // Final stint
    const lastLap = driverLaps[driverLaps.length - 1];
    if (lastLap) {
      stintTraces.push({
        type: 'bar',
        orientation: 'h',
        y: [driver],
        x: [lastLap.lap_number - stintStart + 1],
        base: stintStart,
        marker: { color: COMPOUND_COLORS[currentComp] || '#888' },
        name: currentComp,
        showlegend: false,
        hovertemplate: `<b>${driver}</b><br>${currentComp}<br>Laps ${stintStart}–${lastLap.lap_number}<extra></extra>`,
      });
    }
  });

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: '24px 40px', maxWidth: '1600px', margin: '0 auto' }}>

      {/* Page title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '4px' }}>
          RACE OVERVIEW
        </div>
        <h1 style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#FFFFFF' }}>
          {session.year} {session.gp}
          <span style={{ color: '#00D2BE', marginLeft: '12px', fontSize: '16px' }}>
            — {session.session === 'R' ? 'RACE' : session.session}
          </span>
        </h1>
      </div>

      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <MetricCard label="TOTAL LAPS"    value={String(totalLaps)}  />
        <MetricCard label="DRIVERS"       value={String(allDrivers.length)} />
        <MetricCard
          label="FASTEST LAP"
          value={formatLapTime(fastestLap?.lap_time_seconds)}
          sub={fastestLap?.driver}
        />
        <MetricCard label="COMPOUNDS"     value={compounds.join(' · ')} />
      </div>

      {/* Driver selector + chart toggle */}
      <div style={{
        background: '#12121A',
        border: '1px solid #1E1E2E',
        padding: '16px 20px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '24px',
        flexWrap: 'wrap',
      }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E' }}>
          DRIVERS
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', flex: 1 }}>
          {allDrivers.map((driver, i) => (
            <button
              key={driver}
              onClick={() => {
                setSelectedDrivers(prev =>
                  prev.includes(driver)
                    ? prev.filter(d => d !== driver)
                    : [...prev, driver]
                );
              }}
              style={{
                fontFamily: 'monospace',
                fontSize: '11px',
                letterSpacing: '1px',
                padding: '4px 12px',
                border: `1px solid ${selectedDrivers.includes(driver) ? DRIVER_COLORS[i % DRIVER_COLORS.length] : '#1E1E2E'}`,
                background: selectedDrivers.includes(driver) ? `${DRIVER_COLORS[i % DRIVER_COLORS.length]}20` : 'transparent',
                color: selectedDrivers.includes(driver) ? DRIVER_COLORS[i % DRIVER_COLORS.length] : '#8B8B9E',
                cursor: 'pointer',
              }}
            >
              {driver}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '0' }}>
          {(['laptime', 'position'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setChartMode(mode)}
              style={{
                fontFamily: 'monospace',
                fontSize: '10px',
                letterSpacing: '2px',
                padding: '6px 16px',
                background: chartMode === mode ? '#00D2BE' : 'transparent',
                color: chartMode === mode ? '#0A0A0F' : '#8B8B9E',
                border: '1px solid #1E1E2E',
                cursor: 'pointer',
              }}
            >
              {mode === 'laptime' ? 'LAP TIME' : 'POSITION'}
            </button>
          ))}
        </div>
      </div>

      {/* Main chart */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E', marginBottom: '16px' }}>
        <Plot
          data={chartMode === 'laptime' ? lapTimeTraces : positionTraces}
          layout={{
            ...PLOTLY_LAYOUT,
            title: {
              text: chartMode === 'laptime' ? 'LAP TIME PROGRESSION' : 'POSITION CHANGES',
              font: { color: '#8B8B9E', family: 'monospace', size: 11 },
            },
            xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'LAP', font: { color: '#8B8B9E', size: 10 } } },
            yaxis: {
              ...PLOTLY_LAYOUT.yaxis,
              title: { text: chartMode === 'laptime' ? 'SECONDS' : 'POSITION', font: { color: '#8B8B9E', size: 10 } },
              autorange: chartMode === 'position' ? 'reversed' : true,
            },
            hovermode: 'x unified',
            height: 420,
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Stint strategy */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E', marginBottom: '24px' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid #1E1E2E', fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E' }}>
          STINT STRATEGY
        </div>
        <Plot
          data={stintTraces}
          layout={{
            ...PLOTLY_LAYOUT,
            barmode: 'stack',
            xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'LAP', font: { color: '#8B8B9E', size: 10 } } },
            yaxis: { ...PLOTLY_LAYOUT.yaxis, automargin: true },
            height: Math.max(200, stintDrivers.length * 45 + 60),
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />

        {/* Compound legend */}
        <div style={{ padding: '12px 20px', display: 'flex', gap: '16px', borderTop: '1px solid #1E1E2E' }}>
          {Object.entries(COMPOUND_COLORS).filter(([k]) => compounds.includes(k)).map(([compound, color]) => (
            <div key={compound} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '10px', height: '10px', background: color, borderRadius: '2px' }} />
              <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E' }}>{compound}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Race pace table */}
      <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
        <div style={{ padding: '12px 20px', borderBottom: '1px solid #1E1E2E', fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E' }}>
          RACE PACE SUMMARY
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1E1E2E' }}>
              {['POS', 'DRIVER', 'MEDIAN PACE', 'BEST LAP', 'CONSISTENCY', 'LAPS', 'GAP'].map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#8B8B9E', fontSize: '10px', letterSpacing: '1px' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pace.map((row, i) => (
              <tr key={row.driver} style={{ borderBottom: '1px solid #1E1E2E' }}
                onMouseEnter={e => (e.currentTarget.style.background = '#1E1E2E')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '10px 16px', color: i < 3 ? '#FFD700' : '#8B8B9E' }}>{i + 1}</td>
                <td style={{ padding: '10px 16px', color: '#FFFFFF', fontWeight: '700' }}>{row.driver}</td>
                <td style={{ padding: '10px 16px', color: '#00D2BE' }}>{formatLapTime(row.median_pace)}</td>
                <td style={{ padding: '10px 16px', color: '#00FF87' }}>{formatLapTime(row.best_pace)}</td>
                <td style={{ padding: '10px 16px', color: '#8B8B9E' }}>±{row.consistency.toFixed(3)}s</td>
                <td style={{ padding: '10px 16px', color: '#8B8B9E' }}>{row.clean_laps}</td>
                <td style={{ padding: '10px 16px', color: row.gap_to_fastest === 0 ? '#FFD700' : '#8B8B9E' }}>
                  {row.gap_to_fastest === 0 ? 'LEADER' : `+${row.gap_to_fastest.toFixed(3)}s`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}
