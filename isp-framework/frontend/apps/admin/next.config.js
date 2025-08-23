/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    '@dotmac/headless',
    '@dotmac/primitives',
    '@dotmac/styled-components',
    '@dotmac/registry',
    '@dotmac/mapping',
    '@dotmac/testing',
    '@dotmac/security',
  ],
  experimental: {
    // Partial Prerendering is only available in canary versions
    // ppr: true,
    // Server Actions configuration
    serverActions: {
      bodySizeLimit: '2mb',
    },
    // Instrumentation for monitoring
    instrumentationHook: true,
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
  // Enable React strict mode for better development experience
  reactStrictMode: true,
  // Enable SWC minification for better performance
  swcMinify: true,
  // Disable source maps in production for smaller builds
  productionBrowserSourceMaps: false,
  // Output configuration for deployment
  output: 'standalone',

  // Allow cross-origin requests from the domain
  experimental: {
    allowedDevOrigins: ['marketing.dotmac.ng'],
    // Partial Prerendering is only available in canary versions
    // ppr: true,
    // Server Actions configuration
    serverActions: {
      bodySizeLimit: '2mb',
    },
    // Instrumentation for monitoring
    instrumentationHook: true,
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
  // Optimize CSS
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WEBSOCKET_URL: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:3001',
    NEXT_PUBLIC_APP_NAME: 'DotMac Admin Portal',
    NEXT_PUBLIC_APP_DESCRIPTION: 'ISP Administration Portal',
  },
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.dotmac.com',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
              "img-src 'self' data: https: blob:",
              "font-src 'self' https://fonts.gstatic.com",
              "connect-src 'self' https://api.dotmac.dev wss://api.dotmac.dev http://localhost:* ws://localhost:*",
              "frame-src 'self'",
              "object-src 'none' data:",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
            ].join('; '),
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Permissions-Policy',
            value: 'geolocation=(self), microphone=(), camera=(), payment=()',
          },
        ],
      },
      {
        source: '/:path*.(jpg|jpeg|gif|png|svg|ico|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
