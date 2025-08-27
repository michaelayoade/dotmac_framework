import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DotMac Management Platform',
  description: 'Master Admin Portal for DotMac SaaS Platform',
  keywords: ['ISP', 'Management', 'SaaS', 'Telecom', 'Admin'],
  authors: [{ name: 'DotMac Framework Team' }],
  robots: {
    index: false,
    follow: false,
  },
  manifest: '/manifest.json',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#2563eb" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>
          <div id="root">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}