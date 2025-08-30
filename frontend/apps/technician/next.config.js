const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@dotmac/headless', '@dotmac/primitives', '@dotmac/styled-components', '@dotmac/providers', '@dotmac/mapping'],
  experimental: {
    optimizeCss: true,
    scrollRestoration: true,
  },

  // Advanced bundle optimization
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Bundle analysis and optimization
    if (!dev && !isServer) {
      // Split vendor chunks more granularly
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...config.optimization.splitChunks.cacheGroups,

          // Separate chunk for React/Next.js core
          framework: {
            chunks: 'all',
            name: 'framework',
            test: /(?<!node_modules.*)[\\\/]node_modules[\\\/](react|react-dom|next)[\\\/]/,
            priority: 40,
            enforce: true,
          },

          // UI libraries chunk
          ui: {
            name: 'ui-libs',
            test: /[\\\/]node_modules[\\\/](framer-motion|lucide-react|@headlessui|@radix-ui)[\\\/]/,
            chunks: 'all',
            priority: 30,
          },

          // PWA and offline libs
          pwa: {
            name: 'pwa-libs',
            test: /[\\\/]node_modules[\\\/](workbox-window|dexie|idb)[\\\/]/,
            chunks: 'all',
            priority: 25,
          },

          // Maps and visualization
          maps: {
            name: 'maps-libs',
            test: /[\\\/]node_modules[\\\/](leaflet|react-leaflet|d3)[\\\/]/,
            chunks: 'all',
            priority: 20,
          },

          // Form handling
          forms: {
            name: 'form-libs',
            test: /[\\\/]node_modules[\\\/](react-hook-form|@hookform|zod)[\\\/]/,
            chunks: 'all',
            priority: 15,
          },

          // Common vendor libraries
          vendor: {
            name: 'vendor',
            test: /[\\\/]node_modules[\\\/]/,
            chunks: 'all',
            priority: 10,
          },
        },
      };

      // Tree shaking optimization for unused code
      config.optimization.usedExports = true;
      config.optimization.providedExports = true;
      config.optimization.sideEffects = false;

      // Module concatenation (scope hoisting)
      config.optimization.concatenateModules = true;

      // Minimize CSS
      config.optimization.minimizer.push(
        new (require('css-minimizer-webpack-plugin'))()
      );
    }

    // Use Next.js SWC for TS/JSX; avoid overriding with Babel here

    return config;
  },
  // PWA Configuration
  async rewrites() {
    return [
      {
        source: '/sw.js',
        destination: '/_next/static/sw.js',
      },
    ];
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
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "connect-src 'self' ws: wss:",
              "media-src 'self'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "upgrade-insecure-requests",
            ].join('; '),
          },
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
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(self), payment=(), usb=()',
          },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
        ],
      },
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
  // Enable static export for PWA
  output: 'standalone',

  // Performance optimizations
  compress: true,
  productionBrowserSourceMaps: false,
  optimizeFonts: true,

  // Image optimization
  images: {
    unoptimized: false,
    domains: [],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 31536000, // 1 year
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Advanced optimizations
  swcMinify: true,
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
      preventFullImport: true,
    },
  },

  // Compiler optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
    reactRemoveProperties: process.env.NODE_ENV === 'production',
  },
};

module.exports = withBundleAnalyzer(nextConfig);
