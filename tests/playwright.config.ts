/**
 * Playwright Configuration for License Enforcement E2E Tests
 * Specialized configuration for cross-app license testing
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const isCI = !!process.env.CI;
const isDev = process.env.NODE_ENV === 'development';

export default defineConfig({
  testDir: './e2e',
  
  // Test execution settings
  fullyParallel: !isCI, // Parallel in local dev, sequential in CI for stability
  forbidOnly: isCI,
  retries: isCI ? 2 : 1,
  workers: isCI ? 1 : 2, // Conservative for license testing
  
  // Timeouts - license tests can take longer due to cross-app coordination
  timeout: 120000, // 2 minutes per test
  
  // Comprehensive reporting for licensing compliance validation
  reporter: [
    ['html', { 
      outputFolder: 'test-results/license-enforcement-report',
      open: isDev ? 'on-failure' : 'never'
    }],
    ['json', { 
      outputFile: 'test-results/license-test-results.json' 
    }],
    ['junit', { 
      outputFile: 'test-results/license-test-results.xml' 
    }],
    // Custom license compliance reporter
    [path.resolve(__dirname, 'reporters/license-compliance-reporter.ts')],
    ...(isCI ? [['github']] : [['list', { printSteps: true }]])
  ],
  
  // Global test configuration
  use: {
    // Base URL for management platform (license server)
    baseURL: 'http://localhost:8000',
    
    // Comprehensive tracing for license flow debugging
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Extended timeouts for cross-app operations
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Security settings
    ignoreHTTPSErrors: false,
    acceptDownloads: true,
    
    // Consistent environment
    locale: 'en-US',
    timezoneId: 'America/New_York',
    
    // Extra headers for license testing
    extraHTTPHeaders: {
      'Accept': 'application/json, text/html',
      'X-Test-Environment': 'license-e2e',
      'X-Enable-License-Testing': 'true'
    }
  },
  
  // Test projects for different license scenarios
  projects: [
    // Setup project - prepares test infrastructure
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] }
    },
    
    // Main license enforcement tests
    {
      name: 'license-enforcement',
      testMatch: /feature-flags\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup']
    },
    
    // Cross-app permission tests
    {
      name: 'cross-app-permissions', 
      testMatch: /cross-app-permissions\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup']
    },
    
    // App subscription lifecycle tests
    {
      name: 'subscription-lifecycle',
      testMatch: /app-subscription-lifecycle\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup']
    },
    
    // Multi-browser testing for license consistency
    {
      name: 'firefox-license-tests',
      testMatch: /feature-flags\.spec\.ts/,
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup']
    },
    
    // Mobile testing for field operations licensing
    {
      name: 'mobile-field-ops',
      testMatch: /cross-app-permissions\.spec\.ts/,
      use: { 
        ...devices['iPhone 13'],
        // Mobile-specific permissions for field ops
        permissions: ['geolocation', 'camera']
      },
      dependencies: ['setup']
    },
    
    // Cleanup project
    {
      name: 'cleanup',
      testMatch: /global\.teardown\.ts/,
      use: { ...devices['Desktop Chrome'] }
    }
  ],
  
  // Global setup and teardown
  globalSetup: require.resolve('./setup/global.setup.ts'),
  globalTeardown: require.resolve('./setup/global.teardown.ts'),
  
  // Multi-app web server configuration
  webServer: [
    // Management Platform (License Server)
    {
      command: 'cd ../src/dotmac_management && poetry run python main.py',
      url: 'http://localhost:8000',
      reuseExistingServer: !isCI,
      timeout: 60000,
      env: {
        ENVIRONMENT: 'test',
        DATABASE_URL: 'sqlite:///test_license.db',
        ENABLE_LICENSE_ENFORCEMENT: 'true',
        LOG_LEVEL: 'INFO'
      }
    },
    
    // ISP Framework Admin (Port 3000)
    {
      command: 'cd ../frontend/apps/admin && npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: {
        NODE_ENV: 'test',
        PORT: '3000',
        MANAGEMENT_PLATFORM_URL: 'http://localhost:8000',
        ENABLE_LICENSE_MIDDLEWARE: 'true'
      }
    },
    
    // Customer Portal (Port 3001) 
    {
      command: 'cd ../frontend/apps/customer && npm run dev',
      url: 'http://localhost:3001',
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: {
        NODE_ENV: 'test',
        PORT: '3001',
        MANAGEMENT_PLATFORM_URL: 'http://localhost:8000',
        ENABLE_LICENSE_MIDDLEWARE: 'true'
      }
    },
    
    // Field Operations (Port 3002)
    {
      command: 'cd ../frontend/apps/technician && npm run dev',
      url: 'http://localhost:3002', 
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: {
        NODE_ENV: 'test',
        PORT: '3002',
        MANAGEMENT_PLATFORM_URL: 'http://localhost:8000',
        ENABLE_LICENSE_MIDDLEWARE: 'true'
      }
    },
    
    // Reseller Portal (Port 3003)
    {
      command: 'cd ../frontend/apps/reseller && npm run dev',
      url: 'http://localhost:3003',
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: {
        NODE_ENV: 'test',
        PORT: '3003',
        MANAGEMENT_PLATFORM_URL: 'http://localhost:8000',
        ENABLE_LICENSE_MIDDLEWARE: 'true'
      }
    },
    
    // Management Admin (Port 3004) - CRM substitute
    {
      command: 'cd ../frontend/apps/management-admin && npm run dev',
      url: 'http://localhost:3004',
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: {
        NODE_ENV: 'test',
        PORT: '3004',
        MANAGEMENT_PLATFORM_URL: 'http://localhost:8000',
        ENABLE_LICENSE_MIDDLEWARE: 'true'
      }
    }
  ],
  
  // Output configuration
  outputDir: 'test-results/artifacts',
  preserveOutput: 'failures-only',
  
  // Expect configuration for license testing
  expect: {
    // Longer timeout for license propagation
    timeout: 15000,
    toHaveScreenshot: { 
      threshold: 0.3,
      animations: 'disabled'
    }
  },
  
  // Test metadata
  metadata: {
    testType: 'license-enforcement',
    environment: process.env.NODE_ENV || 'test',
    timestamp: new Date().toISOString(),
    apps: [
      'management-platform',
      'isp-admin',
      'customer-portal', 
      'field-ops',
      'reseller-portal',
      'management-admin'
    ]
  }
});