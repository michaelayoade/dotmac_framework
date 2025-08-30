/**
 * Playwright configuration for reseller portal
 * Generated configuration - extends base config with portal-specific settings
 */

import { defineConfig } from '@playwright/test';
import baseConfig from '../../testing/e2e/playwright.config.base';

export default defineConfig({
  ...baseConfig,

  // Portal-specific test directory
  testDir: './tests/e2e',

  use: {
    ...baseConfig.use,
    baseURL: 'http://localhost:3002',
    storageState: './tests/e2e/auth-reseller.json'
  },

  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3002',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Portal-specific projects
  projects: [
    // Setup for reseller
    {
      name: 'reseller-setup',
      testMatch: /.setup.ts/,
      use: {
        baseURL: 'http://localhost:3002',
      },
    },

    // Desktop tests
    {
      name: 'reseller-chromium',
      dependencies: ['reseller-setup'],
      use: {
        ...baseConfig.projects[1].use,
        baseURL: 'http://localhost:3002',
        storageState: './tests/e2e/auth-reseller.json'
      },
    },


  ],
});
