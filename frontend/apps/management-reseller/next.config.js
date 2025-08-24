/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@dotmac/headless', '@dotmac/primitives', '@dotmac/patterns', '@dotmac/mapping'],
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
            value: "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' http://localhost:8000;",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;