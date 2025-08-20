import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import type React from 'react';
import { NonceProvider } from '@dotmac/headless/components/NonceProvider';

import { Providers } from './providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Admin Portal',
  description:
    'ISP Administration Portal for network management, customer service, and billing operations',
  keywords: ['ISP', 'network management', 'admin portal', 'telecommunications'],
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
