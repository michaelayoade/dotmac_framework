/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@dotmac/headless', '@dotmac/primitives', '@dotmac/styled-components'],
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
  // Optimize CSS
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WEBSOCKET_URL: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:3001',
    NEXT_PUBLIC_APP_NAME: 'DotMac Customer Portal',
    NEXT_PUBLIC_APP_DESCRIPTION: 'ISP Customer Self-Service Portal',
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
  // Security headers are now handled by middleware with CSP nonces
  // Keeping only static file headers that don't need nonces
  async headers() {
    return [
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
