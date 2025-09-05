/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations for integrated websites
  experimental: {
    optimizePackageImports: ['lucide-react', '@headlessui/react'],
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },

  // Image optimization
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 300,
  },

  // Compression and caching
  compress: true,
  poweredByHeader: false,

  // Route optimization for integrated sites
  async rewrites() {
    return [
      // Marketing routes
      {
        source: '/marketing/:path*',
        destination: '/marketing/:path*',
      },
      // Docs routes
      {
        source: '/docs/:path*',
        destination: '/docs/:path*',
      },
    ]
  },

  // Headers for performance
  async headers() {
    return [
      {
        source: '/(.*)',
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
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
      {
        source: '/marketing/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/docs/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=3600, stale-while-revalidate=86400',
          },
        ],
      },
    ]
  },

  // Bundle analysis
  webpack: (config, { buildId, dev, isServer, defaultLoaders, nextRuntime, webpack }) => {
    // Optimize bundle size
    if (!dev) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          marketing: {
            name: 'marketing',
            test: /[\\/]app[\\/]marketing[\\/]/,
            chunks: 'all',
            enforce: true,
          },
          docs: {
            name: 'docs',
            test: /[\\/]app[\\/]docs[\\/]/,
            chunks: 'all',
            enforce: true,
          },
          shared: {
            name: 'shared',
            test: /[\\/]components[\\/]layout[\\/]/,
            chunks: 'all',
            enforce: true,
          },
        },
      }
    }

    return config
  },

  // Environment variables
  env: {
    SITE_URL: process.env.SITE_URL || 'http://localhost:3001',
    MANAGEMENT_API_URL: process.env.MANAGEMENT_API_URL || 'http://localhost:3000',
  },
}

module.exports = nextConfig