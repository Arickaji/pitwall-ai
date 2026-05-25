/**
 * PitWall AI — FastAPI Client
 * Typed API calls to the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface LapRecord {
  driver: string;
  lap_number: number;
  lap_time_seconds: number;
  compound: string;
  tyre_life: number;
  stint: number;
  position: number;
  is_accurate: boolean;
  team: string;
  speed_fl: number;
}

export interface SessionInfo {
  year: number;
  gp: string;
  session_type: string;
  total_laps: number;
  drivers: string[];
  compounds: string[];
}

export interface PaceRecord {
  driver: string;
  median_pace: number;
  best_pace: number;
  consistency: number;
  clean_laps: number;
  gap_to_fastest: number;
}

export interface DegradationRecord {
  driver: string;
  compound: string;
  stint: number;
  laps: number;
  degradation_rate: number;
  base_pace: number;
  r_squared: number;
  cliff_lap: number | null;
}

export interface WinProbability {
  driver: string;
  win_probability: number;
  wins: number;
}

export interface FinalStanding {
  driver: string;
  position: number;
  compound: string;
  tyre_age: number;
  gap_to_leader: number;
}

export interface PitPrediction {
  pit_probability: number;
  recommend_pit: boolean;
  confidence: string;
  threshold: number;
}

export interface PositionResult {
  position: number;
  probability: number;
}

// ── API Helpers ────────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── API Functions ──────────────────────────────────────────────────────────────

export const api = {
  // Data
  getCalendar: (year: number) =>
    get<{ data: { round: number; gp_name: string }[] }>(`/calendar/${year}`),

  getSession: (year: number, gp: string, session: string) =>
    get<{ data: SessionInfo }>(`/sessions/${year}/${encodeURIComponent(gp)}/${session}`),

  getLaps: (year: number, gp: string, session: string, page = 1, pageSize = 200) =>
    get<{ data: LapRecord[]; meta: { total_rows: number; total_pages: number } }>(
      `/laps/${year}/${encodeURIComponent(gp)}/${session}?page=${page}&page_size=${pageSize}`
    ),

  // Analytics
  getPace: (year: number, gp: string, session: string) =>
    post<{ data: PaceRecord[] }>('/analytics/pace', { year, gp, session_type: session }),

  getDegradation: (year: number, gp: string, session: string) =>
    post<{ data: DegradationRecord[] }>('/analytics/degradation', { year, gp, session_type: session }),

  // Simulation
  simulateRace: (year: number, gp: string, session: string, fromLap: number) =>
    post<{ winner: string; final_standings: FinalStanding[] }>('/simulate/race', {
      year, gp, session_type: session, from_lap: fromLap,
    }),

  runMonteCarlo: (year: number, gp: string, session: string, fromLap: number, nSims = 250) =>
    post<{ win_probabilities: WinProbability[]; n_simulations: number }>('/simulate/monte-carlo', {
      year, gp, session_type: session, from_lap: fromLap, n_simulations: nSims,
    }),

  // ML Predictions
  predictPitStop: (params: {
    tyre_life: number; compound: string; position: number;
    gap_ahead: number; gap_behind: number; laps_remaining: number;
    lap_time: number; deg_rate: number;
  }) => post<PitPrediction>('/predict/pit-stop', params),

  predictPosition: (params: {
    current_position: number; laps_remaining: number; tyre_life: number;
    compound: string; gap_ahead: number; gap_behind: number; lap_time: number;
  }) => post<{ most_likely_position: number; top5_positions: PositionResult[] }>('/predict/position', params),
};
