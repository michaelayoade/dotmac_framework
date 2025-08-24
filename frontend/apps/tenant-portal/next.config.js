/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    transpilePackages: ['@dotmac/headless', '@dotmac/primitives', '@dotmac/patterns'],
  },
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
        ],
      },
    ];
  },
};

module.exports = nextConfig;