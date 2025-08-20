import { ErrorBoundary } from '@dotmac/primitives/error';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import type React from 'react';
import { NonceProvider } from '@dotmac/headless/components/NonceProvider';

import { Providers } from './providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Customer Portal',
  description:
    'Self-service portal for DotMac ISP customers - manage your account, view bills, and get support',
  keywords: ['ISP', 'customer portal', 'internet service', 'billing', 'support'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body className={inter.className}>
        <NonceProvider>
          <ErrorBoundary
            level='page'
            onError={(_error, _errorInfo, _errorId) => {
              // Implementation pending
            }}
          >
            <Providers>{children}</Providers>
          </ErrorBoundary>
        </NonceProvider>
      </body>
    </html>
  );
}
