/**
 * Unified Playwright Configuration for DotMac Platform
 * Eliminates config duplication and standardizes E2E testing
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// Environment detection
const isCI = !!process.env.CI;
const isDev = process.env.NODE_ENV === 'development';

// Portal configuration mapping
const PORTAL_CONFIGS = {
  admin: { port: 3000, path: 'isp-framework/admin' },
  customer: { port: 3001, path: 'isp-framework/customer' },
  'field-ops': { port: 3002, path: 'isp-framework/field-ops' },
  reseller: { port: 3003, path: 'isp-framework/reseller' },
  'management-admin': { port: 3004, path: 'management-portal/admin' },
  'management-reseller': { port: 3005, path: 'management-portal/reseller' },
  'tenant-portal': { port: 3006, path: 'management-portal/tenant' },
} as const;

type PortalType = keyof typeof PORTAL_CONFIGS;

interface UnifiedPlaywrightConfig {
  portal?: PortalType;
  testType?: 'smoke' | 'full' | 'integration';
  apiMocking?: boolean;
}

export function createUnifiedConfig(options: UnifiedPlaywrightConfig = {}) {
  const { portal, testType = 'full', apiMocking = true } = options;

  const portalConfig = portal ? PORTAL_CONFIGS[portal] : null;
  const baseURL = portalConfig ? `http://localhost:${portalConfig.port}` : 'http://localhost:3000';

  return defineConfig({
    testDir: portal ? `./${portalConfig?.path}/tests/e2e` : './tests/e2e',

    // Parallelization strategy
    fullyParallel: testType === 'smoke' ? true : !isCI,
    forbidOnly: isCI,
    retries: isCI ? 2 : testType === 'smoke' ? 0 : 1,
    workers: isCI ? 1 : testType === 'smoke' ? 4 : 2,

    // Unified reporting
    reporter: [
      [
        'html',
        {
          outputFolder: `test-results/${portal || 'platform'}-e2e-report`,
          open: isDev ? 'on-failure' : 'never',
        },
      ],
      [
        'json',
        {
          outputFile: `test-results/${portal || 'platform'}-results.json`,
        },
      ],
      [
        'junit',
        {
          outputFile: `test-results/${portal || 'platform'}-results.xml`,
        },
      ],
      ...(isCI ? [['github']] : [['list']]),
    ],

    // Standardized test configuration
    use: {
      baseURL,

      // Tracing and debugging
      trace: testType === 'smoke' ? 'off' : 'on-first-retry',
      screenshot: 'only-on-failure',
      video: testType === 'full' ? 'retain-on-failure' : 'off',

      // Timeouts
      actionTimeout: testType === 'smoke' ? 5000 : 15000,
      navigationTimeout: testType === 'smoke' ? 15000 : 30000,

      // Security and reliability
      ignoreHTTPSErrors: false,
      acceptDownloads: testType === 'full',

      // Consistent browser settings
      locale: 'en-US',
      timezoneId: 'America/New_York',

      // Authentication state
      storageState: portal ? `tests/auth/${portal}-auth.json` : 'tests/auth/default-auth.json',

      // Extra headers for API testing
      extraHTTPHeaders: {
        Accept: 'application/json, text/html',
        'X-Test-Environment': 'e2e',
        ...(apiMocking && { 'X-Enable-API-Mocking': 'true' }),
      },
    },

    // Browser matrix based on test type
    projects: [
      // Authentication setup project
      {
        name: 'auth-setup',
        testMatch: /.*\.auth\.setup\.ts/,
        use: { ...devices['Desktop Chrome'] },
        teardown: 'auth-cleanup',
      },

      // Auth cleanup project
      {
        name: 'auth-cleanup',
        testMatch: /.*\.auth\.cleanup\.ts/,
        use: { ...devices['Desktop Chrome'] },
      },

      // Primary browser for all test types
      {
        name: 'chromium',
        use: {
          ...devices['Desktop Chrome'],
          viewport: { width: 1920, height: 1080 },
        },
        dependencies: ['auth-setup'],
      },

      // Additional browsers for full testing only
      ...(testType === 'full'
        ? [
            {
              name: 'firefox',
              use: { ...devices['Desktop Firefox'] },
              dependencies: ['auth-setup'],
            },
            {
              name: 'webkit',
              use: { ...devices['Desktop Safari'] },
              dependencies: ['auth-setup'],
            },
            {
              name: 'mobile-chrome',
              use: { ...devices['Pixel 5'] },
              dependencies: ['auth-setup'],
            },
            {
              name: 'mobile-safari',
              use: { ...devices['iPhone 12'] },
              dependencies: ['auth-setup'],
            },
          ]
        : []),

      // Portal-specific testing projects
      ...(portal === 'field-ops'
        ? [
            {
              name: 'technician-pwa',
              testMatch: /.*\.pwa\.e2e\.ts/,
              use: {
                ...devices['Pixel 5'],
                permissions: ['geolocation', 'camera'],
                serviceWorkers: 'allow',
              },
              dependencies: ['auth-setup'],
            },
          ]
        : []),

      // Accessibility testing for admin portals
      ...(portal?.includes('admin')
        ? [
            {
              name: 'accessibility',
              testMatch: /.*\.a11y\.e2e\.ts/,
              use: {
                ...devices['Desktop Chrome'],
                reducedMotion: 'reduce',
                forcedColors: 'active',
              },
              dependencies: ['auth-setup'],
            },
          ]
        : []),
    ],

    // Global setup and teardown
    globalSetup: require.resolve('./tests/setup/unified-global-setup.ts'),
    globalTeardown: require.resolve('./tests/setup/unified-global-teardown.ts'),

    // Unified web server strategy
    webServer: portal
      ? {
          command: `pnpm --filter ./${PORTAL_CONFIGS[portal].path} dev`,
          url: baseURL,
          reuseExistingServer: !isCI,
          timeout: 120000,
          env: {
            NODE_ENV: 'test',
            PORT: String(portalConfig!.port),
            ...(apiMocking && { ENABLE_API_MOCKING: 'true' }),
          },
        }
      : [
          // Multi-portal setup for integration tests
          {
            command: 'pnpm --filter ./isp-framework/admin dev',
            port: 3000,
            reuseExistingServer: !isCI,
            timeout: 120000,
          },
          {
            command: 'pnpm --filter ./isp-framework/customer dev',
            port: 3001,
            reuseExistingServer: !isCI,
            timeout: 120000,
          },
        ],

    // Test timeouts based on type
    timeout: testType === 'smoke' ? 30000 : 60000,

    // Expect configuration
    expect: {
      timeout: testType === 'smoke' ? 5000 : 10000,
      toHaveScreenshot: {
        threshold: 0.2,
        animations: 'disabled',
      },
    },

    // Output configuration
    outputDir: `test-results/${portal || 'platform'}-artifacts`,
    preserveOutput: 'failures-only',

    // Test metadata
    metadata: {
      portal: portal || 'platform',
      testType,
      apiMocking: String(apiMocking),
      environment: process.env.NODE_ENV || 'test',
      timestamp: new Date().toISOString(),
    },
  });
}

// Default export for platform-wide testing
export default createUnifiedConfig();

// Named exports for portal-specific configs
export const adminConfig = () => createUnifiedConfig({ portal: 'admin' });
export const customerConfig = () => createUnifiedConfig({ portal: 'customer' });
export const fieldOpsConfig = () => createUnifiedConfig({ portal: 'field-ops' });
export const resellerConfig = () => createUnifiedConfig({ portal: 'reseller' });
export const smokeConfig = () => createUnifiedConfig({ testType: 'smoke' });
