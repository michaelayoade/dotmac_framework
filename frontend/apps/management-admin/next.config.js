/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
    instrumentationHook: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_MANAGEMENT_API_URL}/api/v1/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_MANAGEMENT_API_URL: process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: 'DotMac Management Platform',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
  },
  // Security headers now handled by middleware for nonce support
};

module.exports = nextConfig;