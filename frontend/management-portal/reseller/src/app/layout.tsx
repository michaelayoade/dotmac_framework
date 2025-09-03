import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

import { Providers } from '@/components/providers/Providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Reseller Management Portal',
  description: 'Management platform for DotMac reseller network operations',
  keywords: ['reseller', 'management', 'partner', 'commission', 'channel', 'ISP'],
  authors: [{ name: 'DotMac Team' }],
  robots: 'noindex,nofollow', // Internal management portal
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#4f46e5',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en'>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
