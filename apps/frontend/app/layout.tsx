import type { Metadata } from 'next';
import './globals.css';
import { RaceProvider } from '@/context/RaceContext';
import Header from '@/components/layout/Header';

export const metadata: Metadata = {
  title: 'PitWall AI — F1 Race Strategy Intelligence',
  description: 'Real-world Formula 1 race strategy intelligence platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0, background: '#0A0A0F' }}>
        <RaceProvider>
          <Header />
          <main style={{ background: '#0A0A0F', minHeight: '100vh' }}>
            {children}
          </main>
        </RaceProvider>
      </body>
    </html>
  );
}
