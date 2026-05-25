'use client';

import Link from 'next/link';

const STATS = [
  { value: '180K+', label: 'LAPS ANALYZED' },
  { value: '95+',   label: 'RACES INGESTED' },
  { value: '86%',   label: 'POSITION ACCURACY' },
  { value: '1000',  label: 'MC SIMULATIONS' },
];

const FEATURES = [
  {
    icon: '01',
    title: 'RACE ANALYTICS',
    desc: 'Lap time progression, compound-normalized pace comparison, stint analysis and gap evolution across any F1 session.',
    href: '/race',
  },
  {
    icon: '02',
    title: 'SIMULATION ENGINE',
    desc: 'Monte Carlo race simulation running 1000 scenarios in under 1 second. Pit stop optimization and safety car modeling.',
    href: '/simulation',
  },
  {
    icon: '03',
    title: 'ML PREDICTIONS',
    desc: 'Three production ML models — pit stop probability (ROC-AUC 0.827), degradation delta (RMSE 1.40s), position distribution (86% top-3).',
    href: '/predict',
  },
  {
    icon: '04',
    title: 'TELEMETRY',
    desc: 'Speed, throttle and brake trace comparison between any two drivers. Racing line X/Y visualization with speed gradient map.',
    href: '/telemetry',
  },
];

const TECH = ['Python', 'FastF1', 'XGBoost', 'scikit-learn', 'FastAPI', 'Next.js 16', 'PostgreSQL', 'Parquet', 'Plotly'];

export default function LandingPage() {
  return (
    <div style={{ background: '#0A0A0F', minHeight: '100vh', color: '#FFFFFF' }}>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section style={{
        borderBottom: '1px solid #1E1E2E',
        padding: '120px 80px 80px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '80px',
        alignItems: 'center',
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        <div>
          <div style={{
            fontFamily: 'monospace',
            fontSize: '11px',
            letterSpacing: '4px',
            color: '#00D2BE',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span style={{
              width: '6px', height: '6px',
              borderRadius: '50%',
              background: '#00D2BE',
              display: 'inline-block',
              animation: 'pulse 2s infinite',
            }} />
            SYSTEM ONLINE — v0.1.0
          </div>

          <h1 style={{
            fontFamily: 'monospace',
            fontSize: '72px',
            fontWeight: '900',
            lineHeight: '1',
            letterSpacing: '-2px',
            marginBottom: '24px',
          }}>
            PIT<br />
            <span style={{ color: '#00D2BE' }}>WALL</span><br />
            AI
          </h1>

          <p style={{
            fontSize: '18px',
            lineHeight: '1.7',
            color: '#8B8B9E',
            marginBottom: '40px',
            maxWidth: '480px',
          }}>
            Formula 1 race strategy intelligence platform.
            Simulating the software used by F1 teams during race weekends
            to make real-time pit stop and strategy decisions.
          </p>

          <div style={{ display: 'flex', gap: '16px' }}>
            <Link href="/race" style={{
              fontFamily: 'monospace',
              fontSize: '13px',
              fontWeight: '700',
              letterSpacing: '2px',
              padding: '14px 32px',
              background: '#00D2BE',
              color: '#0A0A0F',
              textDecoration: 'none',
              display: 'inline-block',
            }}>
              OPEN DASHBOARD →
            </Link>
            <a href="https://github.com/Arickaji/pitwall-ai"
              target="_blank"
              style={{
                fontFamily: 'monospace',
                fontSize: '13px',
                letterSpacing: '2px',
                padding: '14px 32px',
                border: '1px solid #1E1E2E',
                color: '#8B8B9E',
                textDecoration: 'none',
                display: 'inline-block',
              }}>
              GITHUB ↗
            </a>
          </div>
        </div>

        {/* Right side — live stats panel */}
        <div style={{
          background: '#12121A',
          border: '1px solid #1E1E2E',
          padding: '32px',
          fontFamily: 'monospace',
        }}>
          <div style={{
            fontSize: '10px',
            letterSpacing: '3px',
            color: '#8B8B9E',
            marginBottom: '24px',
            paddingBottom: '16px',
            borderBottom: '1px solid #1E1E2E',
          }}>
            SYSTEM STATUS
          </div>

          {[
            { label: 'DATA PIPELINE',     status: 'OPERATIONAL', color: '#00FF87' },
            { label: 'ANALYTICS ENGINE',  status: 'OPERATIONAL', color: '#00FF87' },
            { label: 'SIMULATION ENGINE', status: 'OPERATIONAL', color: '#00FF87' },
            { label: 'ML MODELS',         status: 'OPERATIONAL', color: '#00FF87' },
            { label: 'FASTAPI BACKEND',   status: 'OPERATIONAL', color: '#00FF87' },
            { label: 'REACT FRONTEND',    status: 'IN PROGRESS', color: '#FFB800' },
          ].map(({ label, status, color }) => (
            <div key={label} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 0',
              borderBottom: '1px solid #1E1E2E',
              fontSize: '12px',
            }}>
              <span style={{ color: '#8B8B9E', letterSpacing: '1px' }}>{label}</span>
              <span style={{ color, letterSpacing: '1px' }}>● {status}</span>
            </div>
          ))}

          <div style={{ marginTop: '24px', fontSize: '11px', color: '#8B8B9E' }}>
            <span>PHASE 7 OF 8 COMPLETE</span>
            <div style={{
              marginTop: '8px',
              height: '4px',
              background: '#1E1E2E',
              borderRadius: '2px',
            }}>
              <div style={{
                height: '100%',
                width: '87.5%',
                background: '#00D2BE',
                borderRadius: '2px',
              }} />
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats ─────────────────────────────────────────────────────────── */}
      <section style={{
        borderBottom: '1px solid #1E1E2E',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
      }}>
        {STATS.map(({ value, label }, i) => (
          <div key={label} style={{
            padding: '48px 40px',
            borderRight: i < 3 ? '1px solid #1E1E2E' : 'none',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'monospace',
              fontSize: '52px',
              fontWeight: '900',
              color: '#00D2BE',
              lineHeight: '1',
              marginBottom: '12px',
            }}>
              {value}
            </div>
            <div style={{
              fontFamily: 'monospace',
              fontSize: '10px',
              letterSpacing: '3px',
              color: '#8B8B9E',
            }}>
              {label}
            </div>
          </div>
        ))}
      </section>

      {/* ── Features ──────────────────────────────────────────────────────── */}
      <section style={{
        borderBottom: '1px solid #1E1E2E',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        maxWidth: '100%',
      }}>
        {FEATURES.map(({ icon, title, desc, href }, i) => (
          <Link key={title} href={href} style={{
            padding: '48px 40px',
            borderRight: i < 3 ? '1px solid #1E1E2E' : 'none',
            textDecoration: 'none',
            display: 'block',
            transition: 'background 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#12121A')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <div style={{
              fontFamily: 'monospace',
              fontSize: '32px',
              fontWeight: '900',
              color: '#1E1E2E',
              marginBottom: '20px',
              lineHeight: '1',
            }}>
              {icon}
            </div>
            <div style={{
              fontFamily: 'monospace',
              fontSize: '11px',
              fontWeight: '700',
              letterSpacing: '3px',
              color: '#00D2BE',
              marginBottom: '16px',
            }}>
              {title}
            </div>
            <p style={{
              fontSize: '14px',
              lineHeight: '1.7',
              color: '#8B8B9E',
            }}>
              {desc}
            </p>
          </Link>
        ))}
      </section>

      {/* ── Tech Stack ────────────────────────────────────────────────────── */}
      <section style={{
        padding: '48px 80px',
        display: 'flex',
        alignItems: 'center',
        gap: '40px',
        borderBottom: '1px solid #1E1E2E',
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        <div style={{
          fontFamily: 'monospace',
          fontSize: '10px',
          letterSpacing: '3px',
          color: '#8B8B9E',
          whiteSpace: 'nowrap',
          minWidth: '80px',
        }}>
          BUILT WITH
        </div>
        <div style={{ width: '1px', height: '24px', background: '#1E1E2E' }} />
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {TECH.map(t => (
            <span key={t} style={{
              fontFamily: 'monospace',
              fontSize: '11px',
              letterSpacing: '1px',
              padding: '6px 14px',
              border: '1px solid #1E1E2E',
              color: '#8B8B9E',
            }}>
              {t}
            </span>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer style={{
        padding: '32px 80px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
          © 2026 PITWALL AI — ARIC KAJI
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#8B8B9E' }}>
          PHASE 7/8 COMPLETE
        </span>
      </footer>

    </div>
  );
}
