'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRace } from '@/context/RaceContext';

const GPS = [
  'Bahrain Grand Prix', 'Saudi Arabian Grand Prix', 'Australian Grand Prix',
  'Japanese Grand Prix', 'Chinese Grand Prix', 'Miami Grand Prix',
  'Emilia Romagna Grand Prix', 'Monaco Grand Prix', 'Canadian Grand Prix',
  'Spanish Grand Prix', 'Austrian Grand Prix', 'British Grand Prix',
  'Hungarian Grand Prix', 'Belgian Grand Prix', 'Dutch Grand Prix',
  'Italian Grand Prix', 'Azerbaijan Grand Prix', 'Singapore Grand Prix',
  'United States Grand Prix', 'Mexico City Grand Prix', 'São Paulo Grand Prix',
  'Las Vegas Grand Prix', 'Qatar Grand Prix', 'Abu Dhabi Grand Prix',
];

const NAV_LINKS = [
  { href: '/race',       label: 'RACE OVERVIEW' },
  { href: '/strategy',   label: 'STRATEGY' },
  { href: '/simulation', label: 'SIMULATION' },
  { href: '/telemetry',  label: 'TELEMETRY' },
  { href: '/predict',    label: 'ML PREDICT' },
];

export default function Header() {
  const { session, setSession } = useRace();
  const [loading, setLoading] = useState(false);

  const handleLoad = () => {
    setLoading(true);
    setTimeout(() => {
      setSession({ ...session, loaded: true });
      setLoading(false);
    }, 500);
  };

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: '#12121A',
      borderBottom: '1px solid #00D2BE40',
      boxShadow: '0 0 40px rgba(0, 210, 190, 0.05)',
    }}>

      {/* Top bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 40px',
        height: '60px',
        borderBottom: '1px solid #1E1E2E',
      }}>

        {/* Logo */}
        <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px', height: '32px',
            background: '#00D2BE',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'monospace', fontWeight: '900', fontSize: '14px',
            color: '#0A0A0F',
          }}>
            PW
          </div>
          <div>
            <div style={{
              fontFamily: 'monospace', fontWeight: '700',
              fontSize: '14px', letterSpacing: '4px', color: '#FFFFFF',
            }}>
              PITWALL <span style={{ color: '#00D2BE' }}>AI</span>
            </div>
          </div>
        </Link>

        {/* Session Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

          <select
            value={session.year}
            onChange={e => setSession({ ...session, year: +e.target.value, loaded: false })}
            style={{
              fontFamily: 'monospace', fontSize: '12px', letterSpacing: '1px',
              padding: '6px 12px', background: '#0A0A0F',
              border: '1px solid #1E1E2E', color: '#FFFFFF', cursor: 'pointer',
            }}
          >
            {[2024, 2023, 2022].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          <select
            value={session.gp}
            onChange={e => setSession({ ...session, gp: e.target.value, loaded: false })}
            style={{
              fontFamily: 'monospace', fontSize: '12px', letterSpacing: '1px',
              padding: '6px 12px', background: '#0A0A0F',
              border: '1px solid #1E1E2E', color: '#FFFFFF',
              cursor: 'pointer', minWidth: '200px',
            }}
          >
            {GPS.map(gp => (
              <option key={gp} value={gp}>{gp.replace(' Grand Prix', ' GP')}</option>
            ))}
          </select>

          <select
            value={session.session}
            onChange={e => setSession({ ...session, session: e.target.value, loaded: false })}
            style={{
              fontFamily: 'monospace', fontSize: '12px', letterSpacing: '1px',
              padding: '6px 12px', background: '#0A0A0F',
              border: '1px solid #1E1E2E', color: '#FFFFFF', cursor: 'pointer',
            }}
          >
            {[['R','RACE'],['Q','QUALI'],['FP1','FP1'],['FP2','FP2'],['FP3','FP3']].map(([v,l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>

          <button
            onClick={handleLoad}
            disabled={loading}
            style={{
              fontFamily: 'monospace', fontSize: '12px', fontWeight: '700',
              letterSpacing: '2px', padding: '6px 20px',
              background: loading ? '#1E1E2E' : '#00D2BE',
              color: loading ? '#8B8B9E' : '#0A0A0F',
              border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '...' : '▶ LOAD'}
          </button>

          {session.loaded && (
            <div style={{
              fontFamily: 'monospace', fontSize: '10px', letterSpacing: '2px',
              padding: '4px 10px', color: '#00FF87',
              border: '1px solid #00FF8740', background: '#00FF8710',
            }}>
              ● LIVE
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 40px',
        height: '40px',
        gap: '0',
      }}>
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            style={{
              fontFamily: 'monospace',
              fontSize: '10px',
              letterSpacing: '2px',
              padding: '0 20px',
              height: '40px',
              display: 'flex',
              alignItems: 'center',
              color: '#8B8B9E',
              textDecoration: 'none',
              borderRight: '1px solid #1E1E2E',
              transition: 'color 0.2s, background 0.2s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.color = '#00D2BE';
              e.currentTarget.style.background = '#00D2BE10';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color = '#8B8B9E';
              e.currentTarget.style.background = 'transparent';
            }}
          >
            {label}
          </Link>
        ))}

        {/* Right side info */}
        <div style={{
          marginLeft: 'auto',
          fontFamily: 'monospace',
          fontSize: '10px',
          letterSpacing: '2px',
          color: '#1E1E2E',
        }}>
          {session.loaded
            ? `${session.year} ${session.gp.replace(' Grand Prix', ' GP')} — ${session.session}`
            : 'SELECT SESSION TO BEGIN'
          }
        </div>
      </nav>
    </header>
  );
}
