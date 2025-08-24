import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

import { TenantAuthProvider } from '@/components/auth/TenantAuthProvider';
import { ToastProvider } from '@dotmac/primitives';

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
  return (
    <html lang="en">
      <body className={inter.className}>
        <TenantAuthProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </TenantAuthProvider>
      </body>
    </html>
  );
}