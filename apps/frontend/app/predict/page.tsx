'use client';

import { useState } from 'react';
import { useRace } from '@/context/RaceContext';
import { api } from '@/lib/api';
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

function InputField({ label, value, onChange, type = 'number', min, max, step }: {
  label: string; value: any; onChange: (v: any) => void;
  type?: string; min?: number; max?: number; step?: number;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>
        {label}
      </label>
      <input
        type={type} value={value} min={min} max={max} step={step}
        onChange={e => onChange(type === 'number' ? +e.target.value : e.target.value)}
        style={{
          fontFamily: 'monospace', fontSize: '13px', fontWeight: '700',
          padding: '8px', background: '#0A0A0F',
          border: '1px solid #1E1E2E', color: '#FFFFFF', width: '100%',
        }}
      />
    </div>
  );
}

function CompoundSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E' }}>
        COMPOUND
      </label>
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ fontFamily: 'monospace', fontSize: '13px', padding: '8px', background: '#0A0A0F', border: '1px solid #1E1E2E', color: '#FFFFFF' }}>
        {['SOFT', 'MEDIUM', 'HARD'].map(c => <option key={c} value={c}>{c}</option>)}
      </select>
    </div>
  );
}

export default function PredictPage() {
  const { session } = useRace();

  // Pit prediction state
  const [pitParams, setPitParams] = useState({
    tyre_life: 25, compound: 'SOFT', position: 3,
    gap_ahead: 8.5, gap_behind: 5.2, laps_remaining: 20,
    lap_time: 97.5, deg_rate: 0.065,
  });
  const [pitResult, setPitResult]   = useState<any>(null);
  const [pitLoading, setPitLoading] = useState(false);

  // Degradation state
  const [degParams, setDegParams] = useState({
    tyre_life: 20, compound: 'HARD', stint: 2,
    laps_remaining: 25, deg_rate: 0.05,
  });
  const [degResult, setDegResult]   = useState<any>(null);
  const [degLoading, setDegLoading] = useState(false);

  // Position state
  const [posParams, setPosParams] = useState({
    current_position: 1, laps_remaining: 20, tyre_life: 15,
    compound: 'HARD', gap_ahead: 0, gap_behind: 12.0, lap_time: 95.5,
  });
  const [posResult, setPosResult]   = useState<any>(null);
  const [posLoading, setPosLoading] = useState(false);

  async function predictPit() {
    setPitLoading(true);
    try {
      setPitResult(await api.predictPitStop(pitParams));
    } catch (e) { console.error(e); }
    finally { setPitLoading(false); }
  }

  async function predictDeg() {
    setDegLoading(true);
    try {
      setDegResult(await api.predictLapDelta(degParams));
    } catch (e) { console.error(e); }
    finally { setDegLoading(false); }
  }

  async function predictPos() {
    setPosLoading(true);
    try {
      setPosResult(await api.predictPosition(posParams));
    } catch (e) { console.error(e); }
    finally { setPosLoading(false); }
  }

  const pitColor = pitResult
    ? pitResult.pit_probability > 0.6 ? '#FF1E00'
      : pitResult.pit_probability > 0.3 ? '#FFB800' : '#00FF87'
    : '#00D2BE';

  const degColor = degResult
    ? degResult.predicted_delta > 3.0 ? '#FF1E00'
      : degResult.predicted_delta > 1.5 ? '#FFB800'
      : degResult.predicted_delta > 0.5 ? '#FFD700' : '#00FF87'
    : '#00D2BE';

  return (
    <div style={{ padding: '24px 40px', maxWidth: '1600px', margin: '0 auto' }}>

      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '3px', color: '#8B8B9E', marginBottom: '4px' }}>
          ML PREDICTIONS
        </div>
        <h1 style={{ fontFamily: 'monospace', fontSize: '24px', fontWeight: '700', color: '#FFFFFF' }}>
          Real-time Race Predictions
          <span style={{ color: '#00D2BE', marginLeft: '12px', fontSize: '16px' }}>— 3 MODELS</span>
        </h1>
        <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E', marginTop: '8px' }}>
          GradientBoosting · XGBoost Regressor · XGBoost Multiclass — trained on 2022-2024 seasons
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>

        {/* ── Pit Stop Prediction ──────────────────────────────────────── */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="PIT STOP PREDICTION" />

          <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <div style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '12px' }}>
              MODEL PERFORMANCE: ROC-AUC 0.827 · RECALL 83.3%
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <InputField label="TYRE LIFE (laps)" value={pitParams.tyre_life}
                onChange={v => setPitParams(p => ({ ...p, tyre_life: v }))} min={1} max={60} />
              <CompoundSelect value={pitParams.compound}
                onChange={v => setPitParams(p => ({ ...p, compound: v }))} />
              <InputField label="POSITION" value={pitParams.position}
                onChange={v => setPitParams(p => ({ ...p, position: v }))} min={1} max={20} />
              <InputField label="LAPS REMAINING" value={pitParams.laps_remaining}
                onChange={v => setPitParams(p => ({ ...p, laps_remaining: v }))} min={1} max={60} />
              <InputField label="GAP AHEAD (s)" value={pitParams.gap_ahead}
                onChange={v => setPitParams(p => ({ ...p, gap_ahead: v }))} step={0.1} />
              <InputField label="DEG RATE" value={pitParams.deg_rate}
                onChange={v => setPitParams(p => ({ ...p, deg_rate: v }))} step={0.005} />
            </div>
          </div>

          <div style={{ padding: '12px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <button onClick={predictPit} disabled={pitLoading}
              style={{
                width: '100%', fontFamily: 'monospace', fontSize: '11px',
                fontWeight: '700', letterSpacing: '2px', padding: '10px',
                background: pitLoading ? '#1E1E2E' : '#00D2BE',
                color: pitLoading ? '#8B8B9E' : '#0A0A0F',
                border: 'none', cursor: pitLoading ? 'not-allowed' : 'pointer',
              }}>
              {pitLoading ? 'PREDICTING...' : '🤖 PREDICT PIT STOP'}
            </button>
          </div>

          {pitResult && (
            <div style={{ padding: '20px' }}>
              <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '60px', fontWeight: '900', color: pitColor, lineHeight: '1' }}>
                  {(pitResult.pit_probability * 100).toFixed(1)}%
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginTop: '4px' }}>
                  PIT PROBABILITY
                </div>
              </div>

              <div style={{
                padding: '12px 16px', marginBottom: '12px',
                background: pitResult.recommend_pit ? '#FF1E0010' : '#00FF8710',
                border: `1px solid ${pitResult.recommend_pit ? '#FF1E00' : '#00FF87'}`,
                fontFamily: 'monospace', fontSize: '12px', fontWeight: '700',
                color: pitResult.recommend_pit ? '#FF1E00' : '#00FF87',
                textAlign: 'center',
              }}>
                {pitResult.recommend_pit ? '⚠ PIT RECOMMENDED' : '✓ STAY OUT'}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '11px' }}>
                <span style={{ color: '#8B8B9E' }}>CONFIDENCE</span>
                <span style={{ color: pitColor }}>{pitResult.confidence}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '11px', marginTop: '4px' }}>
                <span style={{ color: '#8B8B9E' }}>THRESHOLD</span>
                <span style={{ color: '#8B8B9E' }}>{pitResult.threshold}</span>
              </div>
            </div>
          )}

          {!pitResult && (
            <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
              SET PARAMETERS AND PREDICT
            </div>
          )}
        </div>

        {/* ── Degradation Prediction ───────────────────────────────────── */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="TYRE DEGRADATION" />

          <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <div style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '12px' }}>
              MODEL PERFORMANCE: RMSE 1.40s · HARD RMSE 0.988s
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <InputField label="TYRE LIFE (laps)" value={degParams.tyre_life}
                onChange={v => setDegParams(p => ({ ...p, tyre_life: v }))} min={1} max={60} />
              <CompoundSelect value={degParams.compound}
                onChange={v => setDegParams(p => ({ ...p, compound: v }))} />
              <InputField label="STINT" value={degParams.stint}
                onChange={v => setDegParams(p => ({ ...p, stint: v }))} min={1} max={4} />
              <InputField label="LAPS REMAINING" value={degParams.laps_remaining}
                onChange={v => setDegParams(p => ({ ...p, laps_remaining: v }))} min={1} max={60} />
              <InputField label="DEG RATE (s/lap)" value={degParams.deg_rate}
                onChange={v => setDegParams(p => ({ ...p, deg_rate: v }))} step={0.005} />
            </div>
          </div>

          <div style={{ padding: '12px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <button onClick={predictDeg} disabled={degLoading}
              style={{
                width: '100%', fontFamily: 'monospace', fontSize: '11px',
                fontWeight: '700', letterSpacing: '2px', padding: '10px',
                background: degLoading ? '#1E1E2E' : '#FFD700',
                color: degLoading ? '#8B8B9E' : '#0A0A0F',
                border: 'none', cursor: degLoading ? 'not-allowed' : 'pointer',
              }}>
              {degLoading ? 'PREDICTING...' : '📉 PREDICT DEGRADATION'}
            </button>
          </div>

          {degResult && (
            <div style={{ padding: '20px' }}>
              <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '60px', fontWeight: '900', color: degColor, lineHeight: '1' }}>
                  +{degResult.predicted_delta.toFixed(3)}s
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginTop: '4px' }}>
                  ABOVE FRESH TYRE PACE
                </div>
              </div>

              <div style={{
                padding: '12px 16px', marginBottom: '12px',
                background: '#12121A', border: `1px solid ${degColor}`,
                fontFamily: 'monospace', fontSize: '11px',
                color: degColor, textAlign: 'center',
              }}>
                {degResult.interpretation}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '11px' }}>
                <span style={{ color: '#8B8B9E' }}>COMPOUND</span>
                <span style={{ color: '#FFFFFF' }}>{degResult.compound}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '11px', marginTop: '4px' }}>
                <span style={{ color: '#8B8B9E' }}>TYRE AGE</span>
                <span style={{ color: '#FFFFFF' }}>{degResult.tyre_life} laps</span>
              </div>
            </div>
          )}

          {!degResult && (
            <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
              SET PARAMETERS AND PREDICT
            </div>
          )}
        </div>

        {/* ── Position Prediction ──────────────────────────────────────── */}
        <div style={{ background: '#12121A', border: '1px solid #1E1E2E' }}>
          <SectionHeader title="FINISHING POSITION" />

          <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <div style={{ fontFamily: 'monospace', fontSize: '9px', letterSpacing: '2px', color: '#8B8B9E', marginBottom: '12px' }}>
              MODEL PERFORMANCE: TOP-3 ACC 86% · WITHIN ±1: 62%
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <InputField label="CURRENT POSITION" value={posParams.current_position}
                onChange={v => setPosParams(p => ({ ...p, current_position: v }))} min={1} max={20} />
              <InputField label="LAPS REMAINING" value={posParams.laps_remaining}
                onChange={v => setPosParams(p => ({ ...p, laps_remaining: v }))} min={1} max={60} />
              <InputField label="TYRE LIFE (laps)" value={posParams.tyre_life}
                onChange={v => setPosParams(p => ({ ...p, tyre_life: v }))} min={1} max={60} />
              <CompoundSelect value={posParams.compound}
                onChange={v => setPosParams(p => ({ ...p, compound: v }))} />
              <InputField label="GAP AHEAD (s)" value={posParams.gap_ahead}
                onChange={v => setPosParams(p => ({ ...p, gap_ahead: v }))} step={0.1} />
              <InputField label="GAP BEHIND (s)" value={posParams.gap_behind}
                onChange={v => setPosParams(p => ({ ...p, gap_behind: v }))} step={0.1} />
            </div>
          </div>

          <div style={{ padding: '12px 20px', borderBottom: '1px solid #1E1E2E' }}>
            <button onClick={predictPos} disabled={posLoading}
              style={{
                width: '100%', fontFamily: 'monospace', fontSize: '11px',
                fontWeight: '700', letterSpacing: '2px', padding: '10px',
                background: posLoading ? '#1E1E2E' : '#FF8000',
                color: posLoading ? '#8B8B9E' : '#0A0A0F',
                border: 'none', cursor: posLoading ? 'not-allowed' : 'pointer',
              }}>
              {posLoading ? 'PREDICTING...' : '🏁 PREDICT POSITION'}
            </button>
          </div>

          {posResult && (
            <div style={{ padding: '20px' }}>
              <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '60px', fontWeight: '900', color: '#FF8000', lineHeight: '1' }}>
                  P{posResult.most_likely_position}
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px', color: '#8B8B9E', marginTop: '4px' }}>
                  MOST LIKELY FINISH
                </div>
              </div>

              <Plot
                data={[{
                  type: 'bar',
                  x: posResult.top5_positions.map((p: any) => `P${p.position}`),
                  y: posResult.top5_positions.map((p: any) => (p.probability * 100).toFixed(1)),
                  marker: {
                    color: posResult.top5_positions.map((_: any, i: number) =>
                      i === 0 ? '#FF8000' : '#1E1E2E'
                    ),
                  },
                  text: posResult.top5_positions.map((p: any) => `${(p.probability * 100).toFixed(1)}%`),
                  textposition: 'outside',
                  textfont: { color: '#FFFFFF', family: 'monospace', size: 9 },
                }]}
                layout={{
                  ...PLOTLY_LAYOUT,
                  height: 200,
                  yaxis: { ...PLOTLY_LAYOUT.yaxis, range: [0, 100], title: { text: '%', font: { color: '#8B8B9E', size: 10 } } },
                  xaxis: { ...PLOTLY_LAYOUT.xaxis },
                  margin: { l: 40, r: 10, t: 20, b: 30 },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {!posResult && (
            <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
              SET PARAMETERS AND PREDICT
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
