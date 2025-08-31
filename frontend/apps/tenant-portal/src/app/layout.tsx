import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

import { PortalProviderFactory } from '@dotmac/portal-components';
import { setupGlobalErrorHandlers } from '@/lib/error-handling';
import { initializePerformanceMonitoring } from '@/lib/performance-monitoring';
import { initializeAssetOptimization } from '@/lib/asset-optimization';
import { preloadCriticalData } from '@/lib/caching-strategies';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Tenant Portal',
  description: 'Self-service portal for DotMac ISP Platform tenants',
  keywords: ['ISP', 'tenant', 'management', 'self-service', 'portal'],
  authors: [{ name: 'DotMac Team' }],
  robots: 'noindex,nofollow', // Private tenant portal
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#0ea5e9',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Set up global error handlers and performance optimizations
  if (typeof window !== 'undefined') {
    setupGlobalErrorHandlers();
    initializePerformanceMonitoring();
    initializeAssetOptimization();
    preloadCriticalData();
  }

  return (
    <html lang="en">
      <body className={inter.className}>
        <PortalProviderFactory
          config={{
            portal: 'tenant-portal',
            authVariant: 'enterprise',
            density: 'cozy',
            colorScheme: 'system',
            features: {
              notifications: true,
              tenantManagement: true,
              analytics: true,
              errorHandling: true,
              devtools: process.env.NODE_ENV === 'development'
            }
          }}
        >
          {children}
        </PortalProviderFactory>
      </body>
    </html>
  );
}
