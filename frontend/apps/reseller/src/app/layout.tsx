import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import type React from 'react';
import { NonceProvider } from '@dotmac/headless/components/NonceProvider';

import { Providers } from './providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Reseller Portal',
  description:
    'Partner portal for DotMac ISP resellers - manage customers, track commissions, and grow your business',
  keywords: ['ISP', 'reseller portal', 'partner program', 'telecommunications', 'sales'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body className={inter.className}>
        <NonceProvider>
          <Providers>{children}</Providers>
        </NonceProvider>
      </body>
    </html>
  );
}
