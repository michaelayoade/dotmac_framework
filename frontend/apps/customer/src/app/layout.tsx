import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import type React from 'react';

import './globals.css';
import { RootErrorBoundary } from '../components/common/RootErrorBoundary';
import { ServiceWorkerProvider } from '../components/providers/ServiceWorkerProvider';
import { CustomerPortalAudit } from '@dotmac/headless';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Customer Portal',
  description:
    'Self-service portal for DotMac ISP customers - manage your account, view bills, and get support',
  keywords: ['ISP', 'customer portal', 'internet service', 'billing', 'support'],
  manifest: '/manifest.json',
  themeColor: '#3b82f6',
  viewport: {
    width: 'device-width',
    initialScale: 1,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'DotMac Portal',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="mobile-web-app-capable" content="yes" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={inter.className}>
        <RootErrorBoundary>
          <CustomerPortalAudit>
            <ServiceWorkerProvider>{children}</ServiceWorkerProvider>
          </CustomerPortalAudit>
        </RootErrorBoundary>
      </body>
    </html>
  );
}
