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

function MetricCard({ label, value, sub, color = '#00D2BE' }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div style={{ background: '#12121A', border: '1px solid #1E1E2E', padding: '16px 20px' }}>
      <div style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontFamily: 'monospace', fontSize: '20px', fontWeight: '700', color }}>{value}</div>
      {sub && <div style={{ fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E', marginTop: '2px' }}>{sub}</div>}
    </div>
  );
}

export default function TelemetryPage() {
  const { session } = useRace();

  const [driver1, setDriver1]     = useState('VER');
  const [driver2, setDriver2]     = useState('HAM');
  const [lapNum, setLapNum]       = useState<number | ''>('');
  const [loading, setLoading]     = useState(false);
  const [tel1, setTel1]           = useState<any[]>([]);
  const [tel2, setTel2]           = useState<any[]>([]);
  const [error, setError]         = useState('');

  if (!session.loaded) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '70vh' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '12px', letterSpacing: '3px', color: '#8B8B9E' }}>
          SELECT A SESSION AND CLICK LOAD
        </div>
      </div>
    );
  }

  async function loadTelemetry() {
    setLoading(true);
    setError('');
    try {
      const lapParam = lapNum ? `?lap_number=${lapNum}&page_size=1000` : '?page_size=1000';

      const [res1, res2] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/telemetry/${session.year}/${encodeURIComponent(session.gp)}/${session.session}/${driver1}${lapParam}`),
        fetch(`http://localhost:8000/api/v1/telemetry/${session.year}/${encodeURIComponent(session.gp)}/${session.session}/${driver2}${lapParam}`),
      ]);

      const [d1, d2] = await Promise.all([res1.json(), res2.json()]);
      setTel1(d1.data || []);
      setTel2(d2.data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Computed metrics
  const maxSpeed1 = tel1.length ? Math.max(...tel1.map((t: any) => t.speed || 0)).toFixed(1) : '—';
  const maxSpeed2 = tel2.length ? Math.max(...tel2.map((t: any) => t.speed || 0)).toFixed(1) : '—';
  const throttle1 = tel1.length ? ((tel1.filter((t: any) => t.throttle > 95).length / tel1.length) * 100).toFixed(1) : '—';
  const throttle2 = tel2.length ? ((tel2.filter((t: any) => t.throttle > 95).length / tel2.length) * 100).toFixed(1) : '—';

  return (
    <div style={{ padding: '24px 40px', maxWidth: '1600px', margin: '0 auto' }}>

      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '4px' }}>
          TELEMETRY ANALYSIS
        </div>
        <h1 style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#FFFFFF' }}>
          {session.year} {session.gp}
          <span style={{ color: '#00D2BE', marginLeft: '12px', fontSize: '16px' }}>— TELEMETRY</span>
        </h1>
      </div>

      {/* Controls */}
      <div style={{
        background: '#12121A', border: '1px solid #1E1E2E',
        padding: '16px 20px', marginBottom: '16px',
        display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#00D2BE' }}>DRIVER 1</label>
          <input value={driver1} onChange={e => setDriver1(e.target.value.toUpperCase())} maxLength={3}
            style={{ fontFamily: 'monospace', fontSize: '16px', fontWeight: '700', width: '80px', padding: '8px', background: '#0A0A0F', border: '1px solid #00D2BE', color: '#00D2BE' }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#FF1E00' }}>DRIVER 2</label>
          <input value={driver2} onChange={e => setDriver2(e.target.value.toUpperCase())} maxLength={3}
            style={{ fontFamily: 'monospace', fontSize: '16px', fontWeight: '700', width: '80px', padding: '8px', background: '#0A0A0F', border: '1px solid #FF1E00', color: '#FF1E00' }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>LAP NUMBER</label>
          <input type="number" value={lapNum} onChange={e => setLapNum(e.target.value ? +e.target.value : '')}
            placeholder="FASTEST"
            style={{ fontFamily: 'monospace', fontSize: '14px', width: '100px', padding: '8px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#FFFFFF' }} />
        </div>

        <button onClick={loadTelemetry} disabled={loading}
          style={{
            fontFamily: 'monospace', fontSize: '11px', fontWeight: '700',
            letterSpacing: '2px', padding: '10px 28px',
            background: loading ? '#1E1E2E' : '#00D2BE',
            color: loading ? '#8B8B9E' : '#0A0A0F',
            border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
          }}>
          {loading ? 'LOADING...' : '📡 LOAD TELEMETRY'}
        </button>

        <div style={{ fontFamily: 'monospace', fontSize: '10px', color: '#8B8B9E', marginLeft: 'auto' }}>
          Leave lap blank for fastest lap
        </div>
      </div>

      {error && (
        <div style={{ padding: '16px 20px', background: '#FF1E0010', border: '1px solid #FF1E00', marginBottom: '16px', fontFamily: 'monospace', fontSize: '11px', color: '#FF1E00' }}>
          ERROR: {error}
        </div>
      )}

      {tel1.length > 0 && tel2.length > 0 && (
        <>
          {/* Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
            <MetricCard label={`${driver1} MAX SPEED`} value={`${maxSpeed1} km/h`} color="#00D2BE" />
            <MetricCard label={`${driver2} MAX SPEED`} value={`${maxSpeed2} km/h`} color="#FF1E00" />
            <MetricCard label={`${driver1} FULL THROTTLE`} value={`${throttle1}%`} color="#00D2BE" />
            <MetricCard label={`${driver2} FULL THROTTLE`} value={`${throttle2}%`} color="#FF1E00" />
          </div>

          {/* Speed trace */}
          <div style={{ background: '#12121A', border: '1px solid #1E1E2E', marginBottom: '16px' }}>
            <SectionHeader title={`SPEED TRACE — ${driver1} VS ${driver2}`} />
            <Plot
              data={[
                {
                  x: tel1.map((t: any) => t.distance),
                  y: tel1.map((t: any) => t.speed),
                  mode: 'lines', name: driver1,
                  line: { color: '#00D2BE', width: 2 },
                  hovertemplate: `<b>${driver1}</b><br>%{x:.0f}m<br>%{y:.0f} km/h<extra></extra>`,
                },
                {
                  x: tel2.map((t: any) => t.distance),
                  y: tel2.map((t: any) => t.speed),
                  mode: 'lines', name: driver2,
                  line: { color: '#FF1E00', width: 2 },
                  hovertemplate: `<b>${driver2}</b><br>%{x:.0f}m<br>%{y:.0f} km/h<extra></extra>`,
                },
              ]}
              layout={{
                ...PLOTLY_LAYOUT,
                height: 250,
                xaxis: { ...PLOTLY_LAYOUT.xaxis, title: { text: 'DISTANCE (m)', font: { color: '#8B8B9E', size: 10 } } },
                yaxis: { ...PLOTLY_LAYOUT.yaxis, title: { text: 'SPEED (km/h)', font: { color: '#8B8B9E', size: 10 } } },
                hovermode: 'x unified',
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          </div>

          {/* Throttle + Brake */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
              <SectionHeader title="THROTTLE (%)" />
              <Plot
                data={[
                  { x: tel1.map((t: any) => t.distance), y: tel1.map((t: any) => t.throttle), mode: 'lines', name: driver1, line: { color: '#00D2BE', width: 1.5 } },
                  { x: tel2.map((t: any) => t.distance), y: tel2.map((t: any) => t.throttle), mode: 'lines', name: driver2, line: { color: '#FF1E00', width: 1.5 } },
                ]}
                layout={{
                  ...PLOTLY_LAYOUT, height: 200,
                  yaxis: { ...PLOTLY_LAYOUT.yaxis, range: [0, 105] },
                  hovermode: 'x unified',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
              <SectionHeader title="BRAKE" />
              <Plot
                data={[
                  { x: tel1.map((t: any) => t.distance), y: tel1.map((t: any) => t.brake), mode: 'lines', name: driver1, line: { color: '#00D2BE', width: 1.5 } },
                  { x: tel2.map((t: any) => t.distance), y: tel2.map((t: any) => t.brake), mode: 'lines', name: driver2, line: { color: '#FF1E00', width: 1.5 } },
                ]}
                layout={{
                  ...PLOTLY_LAYOUT, height: 200,
                  hovermode: 'x unified',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Racing line */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
              <SectionHeader title="RACING LINE COMPARISON" />
              <Plot
                data={[
                  { x: tel1.map((t: any) => t.x), y: tel1.map((t: any) => t.y), mode: 'lines', name: driver1, line: { color: '#00D2BE', width: 2 } },
                  { x: tel2.map((t: any) => t.x), y: tel2.map((t: any) => t.y), mode: 'lines', name: driver2, line: { color: '#FF1E00', width: 2 } },
                ]}
                layout={{
                  ...PLOTLY_LAYOUT, height: 350,
                  yaxis: { ...PLOTLY_LAYOUT.yaxis, scaleanchor: 'x', scaleratio: 1 },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>

            {/* Speed map */}
            <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
              <SectionHeader title={`${driver1} — SPEED MAP`} />
              <Plot
                data={[{
                  x: tel1.map((t: any) => t.x),
                  y: tel1.map((t: any) => t.y),
                  mode: 'markers',
                  marker: {
                    size: 3,
                    color: tel1.map((t: any) => t.speed),
                    colorscale: 'RdYlGn',
                    showscale: true,
                    colorbar: { title: { text: 'km/h', font: { color: '#8B8B9E', size: 10 } }, tickfont: { color: '#8B8B9E', size: 9 } },
                  },
                  hovertemplate: `<b>${driver1}</b><br>Speed: %{marker.color:.0f} km/h<extra></extra>`,
                }]}
                layout={{
                  ...PLOTLY_LAYOUT, height: 350,
                  yaxis: { ...PLOTLY_LAYOUT.yaxis, scaleanchor: 'x', scaleratio: 1 },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </>
      )}

      {tel1.length === 0 && !loading && (
        <div style={{ padding: '80px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E', border: '1px solid #1E1E2E' }}>
          ENTER TWO DRIVER CODES AND CLICK LOAD TELEMETRY
        </div>
      )}

    </div>
  );
}
