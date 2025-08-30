/**
 * Playwright configuration for admin portal
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
    baseURL: 'http://localhost:3000',
    storageState: './tests/e2e/auth-admin.json'
  },

  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Portal-specific projects
  projects: [
    // Setup for admin
    {
      name: 'admin-setup',
      testMatch: /.setup.ts/,
      use: {
        baseURL: 'http://localhost:3000',
      },
    },

    // Desktop tests
    {
      name: 'admin-chromium',
      dependencies: ['admin-setup'],
      use: {
        ...baseConfig.projects[1].use,
        baseURL: 'http://localhost:3000',
        storageState: './tests/e2e/auth-admin.json'
      },
    },


  ],
});
