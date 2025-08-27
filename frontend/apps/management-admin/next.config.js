/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    instrumentationHook: true,
  },
  
  // Disable ESLint warnings as errors for production deployment
  eslint: {
    ignoreDuringBuilds: true,
  },
  
  // Performance optimizations
  swcMinify: true,
  compress: true,
  
  // Bundle optimization
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Exclude client-side only modules from server bundle
    if (isServer) {
      config.externals = config.externals || {};
      config.externals['performance'] = 'commonjs performance';
      config.externals['crypto'] = 'commonjs crypto';
      config.externals['localStorage'] = 'commonjs localStorage';
      config.externals['sessionStorage'] = 'commonjs sessionStorage';
      config.externals['window'] = 'commonjs window';
      config.externals['document'] = 'commonjs document';
      config.externals['navigator'] = 'commonjs navigator';
    }

    // Optimize bundle size for client
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
            minChunks: 2,
            priority: 5,
            reuseExistingChunk: true,
          },
        },
      };

      // Remove unused CSS
      config.plugins.push(
        new webpack.IgnorePlugin({
          resourceRegExp: /^\.\/locale$/,
          contextRegExp: /moment$/,
        })
      );
    }

    return config;
  },

  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // API rewrites
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },

  // Headers for performance
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
        ],
      },
      {
        source: '/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_MANAGEMENT_API_URL: process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: 'DotMac Management Platform',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
    NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
    NEXT_PUBLIC_BUILD_VERSION: process.env.BUILD_VERSION || 'dev',
  },

  // Output configuration for production
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  
  // Security headers now handled by middleware for nonce support
};

module.exports = nextConfig;