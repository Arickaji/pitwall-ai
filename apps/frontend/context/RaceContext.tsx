'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface RaceSession {
  year: number;
  gp: string;
  session: string;
  loaded: boolean;
}

interface RaceContextType {
  session: RaceSession;
  setSession: (s: RaceSession) => void;
}

const RaceContext = createContext<RaceContextType>({
  session: { year: 2024, gp: 'Bahrain Grand Prix', session: 'R', loaded: false },
  setSession: () => {},
});

export function RaceProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<RaceSession>({
    year: 2024,
    gp: 'Bahrain Grand Prix',
    session: 'R',
    loaded: false,
  });

  return (
    <RaceContext.Provider value={{ session, setSession }}>
      {children}
    </RaceContext.Provider>
  );
}

export const useRace = () => useContext(RaceContext);
