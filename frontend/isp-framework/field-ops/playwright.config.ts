/**
 * Playwright configuration for technician portal
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
    baseURL: 'http://localhost:3005',
    storageState: './tests/e2e/auth-technician.json',
  },

  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3005',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Portal-specific projects
  projects: [
    // Setup for technician
    {
      name: 'technician-setup',
      testMatch: /.setup.ts/,
      use: {
        baseURL: 'http://localhost:3005',
      },
    },

    // Desktop tests
    {
      name: 'technician-chromium',
      dependencies: ['technician-setup'],
      use: {
        ...baseConfig.projects[1].use,
        baseURL: 'http://localhost:3005',
        storageState: './tests/e2e/auth-technician.json',
      },
    },

    // Mobile-optimized for technician portal
    {
      name: 'technician-mobile',
      dependencies: ['technician-setup'],
      use: {
        ...baseConfig.projects[4].use,
        baseURL: 'http://localhost:3005',
        storageState: './tests/e2e/auth-technician.json',
      },
    },
  ],
});
