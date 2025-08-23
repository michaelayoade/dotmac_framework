import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import type React from 'react';

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
    <html lang='en'>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
