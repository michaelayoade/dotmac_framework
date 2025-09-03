/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Transpile packages (moved out of experimental in Next.js 13.4+)
  transpilePackages: ['@dotmac/headless', '@dotmac/primitives', '@dotmac/patterns'],

  experimental: {
    // Enable modern bundling optimizations
    esmExternals: 'loose',
    // Enable SWC minification for better performance
    swcMinify: true,
  },

  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 31536000, // 1 year
    dangerouslyAllowSVG: false,
    contentDispositionType: 'inline',
  },

  // Bundle analyzer (only in development)
  ...(process.env.ANALYZE === 'true' && {
    webpack: (config, { isServer }) => {
      if (!isServer) {
        const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'server',
            openAnalyzer: false,
          })
        );
      }

      // Optimize chunks
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              priority: 20,
              chunks: 'all',
            },
            common: {
              name: 'common',
              minChunks: 2,
              priority: 10,
              reuseExistingChunk: true,
            },
            accessibility: {
              test: /[\\/](accessibility|a11y)[\\/]/,
              name: 'accessibility',
              priority: 30,
              chunks: 'all',
            },
          },
        },
      };

      return config;
    },
  }),
  env: {
    NEXT_PUBLIC_APP_NAME: 'DotMac Tenant Portal',
    NEXT_PUBLIC_APP_VERSION: process.env.npm_package_version,
    NEXT_PUBLIC_MANAGEMENT_API_URL: process.env.MANAGEMENT_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_PORTAL_TYPE: 'tenant',
  },
  async redirects() {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: false,
      },
    ];
  },
  async headers() {
    const isProduction = process.env.NODE_ENV === 'production';
    const managementApiUrl = process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000';
    const apiDomain = new URL(managementApiUrl).hostname;

    return [
      {
        source: '/(.*)',
        headers: [
          // Content Security Policy
          {
            key: 'Content-Security-Policy',
            value: [
              // Default source - only allow self
              "default-src 'self'",

              // Scripts - allow self, inline for Next.js, and specific domains
              isProduction
                ? "script-src 'self' 'unsafe-eval'"
                : "script-src 'self' 'unsafe-eval' 'unsafe-inline'",

              // Styles - allow self, inline, and Google Fonts
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",

              // Images - allow self, data URLs, and tenant domains
              "img-src 'self' data: https:",

              // Fonts - allow self and Google Fonts
              "font-src 'self' https://fonts.gstatic.com",

              // Connect - allow self and API domains
              `connect-src 'self' ${managementApiUrl} wss://${apiDomain} ws://${apiDomain}`,

              // Frames - deny all
              "frame-src 'none'",

              // Objects - deny all
              "object-src 'none'",

              // Base URI - restrict to self
              "base-uri 'self'",

              // Form actions - only allow self
              "form-action 'self'",

              // Upgrade insecure requests in production
              ...(isProduction ? ['upgrade-insecure-requests'] : []),

              // Report violations
              process.env.CSP_REPORT_URI ? `report-uri ${process.env.CSP_REPORT_URI}` : '',
            ]
              .filter(Boolean)
              .join('; '),
          },

          // Prevent clickjacking attacks
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },

          // Prevent MIME type sniffing
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },

          // Control referrer information
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },

          // XSS Protection (legacy, but still useful)
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },

          // HTTPS enforcement in production
          ...(isProduction
            ? [
                {
                  key: 'Strict-Transport-Security',
                  value: 'max-age=31536000; includeSubDomains; preload',
                },
              ]
            : []),

          // Permissions Policy (formerly Feature Policy)
          {
            key: 'Permissions-Policy',
            value: [
              'camera=()',
              'microphone=()',
              'geolocation=()',
              'interest-cohort=()',
              'payment=()',
              'usb=()',
              'accelerometer=()',
              'gyroscope=()',
              'magnetometer=()',
            ].join(', '),
          },

          // Prevent DNS prefetching for privacy
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'off',
          },

          // Server information hiding
          {
            key: 'Server',
            value: 'TenantPortal',
          },

          // Cache control for sensitive pages
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate',
          },

          // Prevent page caching
          {
            key: 'Pragma',
            value: 'no-cache',
          },

          // Cross-Origin policies
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'require-corp',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
          {
            key: 'Cross-Origin-Resource-Policy',
            value: 'same-origin',
          },
        ],
      },

      // API routes - more permissive headers
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'Cache-Control',
            value: 'no-store',
          },
        ],
      },

      // Static assets - allow caching
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },

      // Favicon and manifest - allow caching
      {
        source: '/(favicon.ico|manifest.json|robots.txt)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=86400',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
