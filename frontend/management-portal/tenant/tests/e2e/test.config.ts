/**
 * Shared test configuration and constants
 * Centralized configuration for all E2E tests
 */

export const TEST_CONFIG = {
  // Base URLs for different environments
  baseUrls: {
    development: 'http://localhost:3003',
    staging: 'https://staging-tenant.dotmac.com',
    production: 'https://tenant.dotmac.com',
  },

  // Test timeouts (in milliseconds)
  timeouts: {
    navigation: 30000,
    api: 15000,
    element: 10000,
    assertion: 5000,
  },

  // Performance thresholds
  performance: {
    pageLoad: 3000, // Maximum page load time
    domReady: 1500, // Maximum DOM content loaded time
    apiResponse: 2000, // Maximum API response time
    interaction: 1000, // Maximum interaction response time
  },

  // Test data limits
  testData: {
    maxUsers: 100,
    maxSubscriptions: 20,
    maxLicenses: 500,
    batchSize: 10,
  },

  // Test categories and tags
  tags: {
    smoke: '@smoke',
    regression: '@regression',
    performance: '@performance',
    accessibility: '@accessibility',
    security: '@security',
    critical: '@critical',
    slow: '@slow',
  },

  // Browser configurations
  browsers: {
    desktop: ['chromium', 'firefox', 'webkit'],
    mobile: ['Mobile Chrome', 'Mobile Safari'],
    tablet: ['iPad Pro'],
  },

  // Viewport configurations
  viewports: {
    mobile: { width: 375, height: 667 },
    tablet: { width: 768, height: 1024 },
    desktop: { width: 1280, height: 720 },
    wide: { width: 1920, height: 1080 },
  },

  // Test environment variables
  env: {
    CI: process.env.CI === 'true',
    DEBUG: process.env.DEBUG === 'true',
    HEADLESS: process.env.HEADLESS !== 'false',
    SLOW_MO: parseInt(process.env.SLOW_MO || '0'),
    PARALLEL: process.env.PARALLEL !== 'false',
    RETRIES: parseInt(process.env.RETRIES || '0'),
  },

  // API mock configurations
  mocks: {
    enabled: process.env.USE_MOCKS !== 'false',
    delay: parseInt(process.env.MOCK_DELAY || '100'),
    errorRate: parseFloat(process.env.MOCK_ERROR_RATE || '0'),
  },

  // Screenshot and video configurations
  media: {
    screenshots: {
      mode: 'only-on-failure',
      quality: 80,
      fullPage: true,
    },
    videos: {
      mode: 'retain-on-failure',
      size: { width: 1280, height: 720 },
    },
    traces: {
      mode: 'retain-on-failure',
      screenshots: true,
      snapshots: true,
    },
  },

  // Authentication configurations
  auth: {
    storageState: '.auth/tenant-state.json',
    timeout: 30000,
    retries: 3,
  },

  // Database and API configurations
  api: {
    retries: 3,
    timeout: 15000,
    rateLimit: {
      requests: 100,
      per: 60000, // 1 minute
    },
  },
} as const;

// Test suite configurations
export const TEST_SUITES = {
  smoke: {
    description: 'Critical path smoke tests',
    timeout: 60000,
    retries: 2,
    tests: [
      'login and dashboard access',
      'subscription overview display',
      'license usage display',
      'navigation functionality',
    ],
  },

  subscription: {
    description: 'Comprehensive subscription management tests',
    timeout: 120000,
    retries: 1,
    tests: [
      'app catalog browsing',
      'subscription creation',
      'subscription upgrades',
      'subscription cancellation',
      'subscription history',
    ],
  },

  license: {
    description: 'Multi-app license management tests',
    timeout: 90000,
    retries: 1,
    tests: [
      'license overview',
      'feature access validation',
      'license upgrade requests',
      'usage monitoring',
      'license assignment',
    ],
  },

  dashboard: {
    description: 'Tenant admin dashboard tests',
    timeout: 180000,
    retries: 1,
    tests: [
      'dashboard overview',
      'user management',
      'permissions configuration',
      'organization settings',
      'billing analytics',
    ],
  },

  performance: {
    description: 'Performance and load tests',
    timeout: 300000,
    retries: 0,
    tests: [
      'page load performance',
      'large dataset handling',
      'concurrent user simulation',
      'memory usage monitoring',
    ],
  },

  accessibility: {
    description: 'Accessibility and usability tests',
    timeout: 90000,
    retries: 1,
    tests: [
      'screen reader compatibility',
      'keyboard navigation',
      'color contrast compliance',
      'ARIA attributes validation',
    ],
  },
} as const;

// Test environment detection
export function getEnvironment(): keyof typeof TEST_CONFIG.baseUrls {
  if (process.env.TEST_ENV) {
    return process.env.TEST_ENV as keyof typeof TEST_CONFIG.baseUrls;
  }

  if (process.env.CI) {
    return 'staging';
  }

  return 'development';
}

// Get base URL for current environment
export function getBaseUrl(): string {
  const env = getEnvironment();
  return process.env.BASE_URL || TEST_CONFIG.baseUrls[env];
}

// Test utilities
export const TEST_UTILS = {
  // Generate unique test identifiers
  generateTestId: (prefix: string = 'test') => {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `${prefix}-${timestamp}-${random}`;
  },

  // Format test durations
  formatDuration: (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  },

  // Parse test results
  parseTestResults: (results: any) => ({
    total: results.stats?.total || 0,
    passed: results.stats?.expected || 0,
    failed: results.stats?.failed || 0,
    skipped: results.stats?.skipped || 0,
    duration: results.stats?.duration || 0,
    success: (results.stats?.failed || 0) === 0,
  }),

  // Environment checks
  isCI: () => TEST_CONFIG.env.CI,
  isDebug: () => TEST_CONFIG.env.DEBUG,
  isHeadless: () => TEST_CONFIG.env.HEADLESS,

  // Browser detection
  getCurrentBrowser: () => process.env.PLAYWRIGHT_BROWSER || 'chromium',

  // Test data generators
  generateEmail: () => `test-${Date.now()}@example.com`,
  generateTenantName: () => `Test Tenant ${Date.now()}`,
  generatePassword: () => `TestPass${Date.now()}!`,
} as const;

// Export default configuration
export default TEST_CONFIG;
