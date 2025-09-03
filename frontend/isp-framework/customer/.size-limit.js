/**
 * Size Limit Configuration for Customer App
 * Performance budgets and bundle size monitoring
 */

module.exports = [
  // Main application bundle
  {
    name: 'Client Bundle (JS)',
    path: '.next/static/js/**/*.js',
    limit: '250 KB',
    webpack: false,
  },
  // CSS bundle
  {
    name: 'Client Bundle (CSS)',
    path: '.next/static/css/**/*.css',
    limit: '50 KB',
    webpack: false,
  },
  // Initial page load
  {
    name: 'Initial Page Load',
    path: '.next/static/chunks/pages/_app*.js',
    limit: '150 KB',
    webpack: false,
  },
  // First Load JS shared by all
  {
    name: 'First Load JS (Shared)',
    path: '.next/static/chunks/framework*.js',
    limit: '100 KB',
    webpack: false,
  },
  // Individual page bundles
  {
    name: 'Login Page',
    path: '.next/static/chunks/pages/index*.js',
    limit: '80 KB',
    webpack: false,
  },
  {
    name: 'Dashboard Page',
    path: '.next/static/chunks/pages/dashboard*.js',
    limit: '120 KB',
    webpack: false,
  },
  // Dynamic imports and code splitting
  {
    name: 'Authentication Components',
    path: '.next/static/chunks/*auth*.js',
    limit: '60 KB',
    webpack: false,
  },
  {
    name: 'Chart Components',
    path: '.next/static/chunks/*chart*.js',
    limit: '80 KB',
    webpack: false,
  },
  // Third-party libraries
  {
    name: 'Vendor Bundle',
    path: '.next/static/chunks/vendors*.js',
    limit: '200 KB',
    webpack: false,
  },
];
