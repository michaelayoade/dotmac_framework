/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  transpilePackages: [
    '@dotmac/headless',
    '@dotmac/primitives',
    '@dotmac/patterns',
    '@dotmac/mapping',
  ],
  env: {
    NEXT_PUBLIC_APP_NAME: 'DotMac Reseller Management',
    NEXT_PUBLIC_APP_VERSION: process.env.npm_package_version,
    NEXT_PUBLIC_MANAGEMENT_API_URL: process.env.MANAGEMENT_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_PORTAL_TYPE: 'management-reseller',
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
    return [
      {
        source: '/(.*)',
        headers: [
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
            key: 'Content-Security-Policy',
            value:
              "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' http://localhost:8000;",
          },
        ],
      },
    ];
  },

  // Webpack configuration
  webpack: (config, { dev, isServer }) => {
    // Bundle analysis
    if (process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          openAnalyzer: false,
          reportFilename: isServer ? '../analyze/server.html' : './analyze/client.html',
        })
      );
    }

    // Production optimizations
    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: 10,
            reuseExistingChunk: true,
          },
          common: {
            name: 'common',
            minChunks: 2,
            priority: 5,
            reuseExistingChunk: true,
          },
          charts: {
            test: /[\\/]node_modules[\\/](recharts|d3)[\\/]/,
            name: 'charts',
            priority: 20,
            reuseExistingChunk: true,
          },
        },
      };
    }

    // Security: Remove source maps in production
    if (isProd) {
      config.devtool = false;
    }

    return config;
  },

  // Output configuration
  output: isProd ? 'standalone' : undefined,

  // Image optimization
  images: {
    domains: ['localhost'],
    ...(isProd && {
      loader: 'custom',
      loaderFile: './src/lib/image-loader.js',
    }),
  },

  // PoweredBy header removal
  poweredByHeader: false,

  // Generate build ID
  generateBuildId: async () => {
    return `build-${Date.now()}`;
  },
};

module.exports = nextConfig;
