import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/next'
import { ThemeProvider } from 'next-themes'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || 'https://isp.dotmac.platform'),
  title: {
    default: 'ISP Framework by DotMac - Complete ISP Management Platform',
    template: '%s | ISP Framework by DotMac',
  },
  description: 'Transform your ISP operations with our comprehensive management platform. Automate network management, streamline customer operations, and scale your business with enterprise-grade tools.',
  keywords: [
    'ISP management software',
    'network automation',
    'telecommunications platform',
    'WISP management',
    'ISP billing software',
    'network monitoring',
    'customer management',
    'service provider platform',
    'ISP operations',
    'network infrastructure'
  ],
  authors: [{ name: 'DotMac Platform Team' }],
  creator: 'DotMac Platform',
  publisher: 'DotMac Platform',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: process.env.SITE_URL || 'https://isp.dotmac.platform',
    siteName: 'ISP Framework by DotMac',
    title: 'ISP Framework - Complete ISP Management Platform',
    description: 'Transform your ISP operations with our comprehensive management platform. Automate network management, streamline customer operations, and scale your business.',
    images: [
      {
        url: '/images/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'ISP Framework by DotMac - Complete ISP Management Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@dotmacplatform',
    creator: '@dotmacplatform',
    title: 'ISP Framework - Complete ISP Management Platform',
    description: 'Transform your ISP operations with our comprehensive management platform.',
    images: ['/images/twitter-card.jpg'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    google: process.env.GOOGLE_SITE_VERIFICATION,
    yandex: process.env.YANDEX_VERIFICATION,
    yahoo: process.env.YAHOO_VERIFICATION,
  },
  alternates: {
    canonical: process.env.SITE_URL || 'https://isp.dotmac.platform',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preload critical fonts */}
        <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossOrigin="" />
        
        {/* Favicon */}
        <link rel="icon" href="/favicon.ico" />
        <link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16x16.png" />
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        
        {/* Theme color */}
        <meta name="theme-color" content="#2563eb" />
        <meta name="msapplication-TileColor" content="#2563eb" />
        
        {/* Preconnect to external domains */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" />
        
        {/* DNS prefetch for analytics */}
        <link rel="dns-prefetch" href="//www.google-analytics.com" />
        <link rel="dns-prefetch" href="//googletagmanager.com" />
        
        {/* Structured data for organization */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Organization',
              name: 'DotMac Platform',
              url: process.env.SITE_URL || 'https://isp.dotmac.platform',
              logo: `${process.env.SITE_URL || 'https://isp.dotmac.platform'}/images/logo.svg`,
              description: 'Complete ISP Management Platform for service providers',
              address: {
                '@type': 'PostalAddress',
                addressCountry: 'US',
              },
              contactPoint: {
                '@type': 'ContactPoint',
                telephone: '+1-555-DOTMAC',
                contactType: 'customer service',
              },
              sameAs: [
                'https://twitter.com/dotmacplatform',
                'https://linkedin.com/company/dotmac-platform',
                'https://github.com/dotmac',
              ],
            }),
          }}
        />
        
        {/* Product structured data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'ISP Framework',
              applicationCategory: 'BusinessApplication',
              operatingSystem: 'Linux, Windows, macOS',
              offers: {
                '@type': 'Offer',
                price: '0',
                priceCurrency: 'USD',
                availability: 'https://schema.org/InStock',
              },
              aggregateRating: {
                '@type': 'AggregateRating',
                ratingValue: '4.8',
                ratingCount: '127',
              },
            }),
          }}
        />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}