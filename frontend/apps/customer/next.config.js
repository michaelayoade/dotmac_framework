const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

const { withSentryConfig } = require('@sentry/nextjs');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // TypeScript configuration re-enabled
  typescript: {
    ignoreBuildErrors: false,
  },
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
    // Modern bundling optimizations
    optimizePackageImports: ['@dotmac/primitives', '@dotmac/headless', 'lucide-react'],
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
  // Optimize CSS and JavaScript
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
    // Remove React DevTools in production
    reactRemoveProperties: process.env.NODE_ENV === 'production',
  },
  // Performance optimizations
  poweredByHeader: false,
  compress: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WEBSOCKET_URL: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:3001',
    NEXT_PUBLIC_APP_NAME: 'DotMac Customer Portal',
    NEXT_PUBLIC_APP_DESCRIPTION: 'ISP Customer Self-Service Portal',
  },
  // Image optimization configuration
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.dotmac.com',
      },
    ],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
    dangerouslyAllowSVG: false,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
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
  // PWA configuration
  generateBuildId: async () => {
    // Generate a build ID for cache busting
    return `build-${Date.now()}`;
  },
  // Webpack optimizations
  webpack: (config, { dev, isServer }) => {
    // Production optimizations
    if (!dev) {
      config.optimization = {
        ...config.optimization,
        // Enable aggressive tree shaking
        usedExports: true,
        sideEffects: false,
        // Split chunks optimally
        splitChunks: {
          chunks: 'all',
          minSize: 20000,
          maxSize: 244000,
          cacheGroups: {
            default: {
              minChunks: 2,
              priority: -20,
              reuseExistingChunk: true,
            },
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              priority: -10,
              chunks: 'all',
            },
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              enforce: true,
            },
          },
        },
      };
    }

    // Bundle analyzer in development
    if (dev && process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'server',
          openAnalyzer: true,
        })
      );
    }

    return config;
  },
};

// Sentry configuration
const sentryWebpackPluginOptions = {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
  widenClientFileUpload: true,
  reactComponentAnnotation: {
    enabled: process.env.NODE_ENV === 'development',
  },
  tunnelRoute: '/monitoring',
  hideSourceMaps: true,
  disableLogger: process.env.NODE_ENV === 'production',
  automaticVercelMonitors: false,
};

module.exports = withSentryConfig(
  withBundleAnalyzer(nextConfig), 
  sentryWebpackPluginOptions
);
