import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Builder · Evaluator Console',
  description: 'AI Asset Builder Intelligence Query Console',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
