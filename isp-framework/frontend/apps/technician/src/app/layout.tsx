import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DotMac Technician Portal',
  description: 'Mobile-first technician portal for field operations',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en'>
      <body>{children}</body>
    </html>
  );
}
