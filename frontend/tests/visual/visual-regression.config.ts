/**
 * Visual Regression Testing Configuration
 * Following backend testing patterns for comprehensive visual testing
 */

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './visual',

  // Visual testing specific settings
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    // Visual testing options
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Reduce flakiness in visual tests
    actionTimeout: 10000,

    // Wait for fonts to load
    waitForSelector: {
      selector: 'body',
      state: 'visible',
    },
  },

  // Visual test projects for different viewports and themes
  projects: [
    // Desktop viewports
    {
      name: 'Desktop Chrome - Light Theme',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
        colorScheme: 'light',
      },
    },
    {
      name: 'Desktop Chrome - Dark Theme',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
        colorScheme: 'dark',
      },
    },

    // Tablet viewports
    {
      name: 'Tablet - Light Theme',
      use: {
        browserName: 'chromium',
        viewport: { width: 768, height: 1024 },
        colorScheme: 'light',
      },
    },

    // Mobile viewports
    {
      name: 'Mobile - Light Theme',
      use: {
        browserName: 'chromium',
        viewport: { width: 375, height: 667 },
        colorScheme: 'light',
      },
    },

    // Portal-specific configurations
    {
      name: 'Admin Portal - Desktop',
      use: {
        browserName: 'chromium',
        viewport: { width: 1440, height: 900 },
        storageState: 'test-auth/admin-auth.json',
      },
    },
    {
      name: 'Customer Portal - Desktop',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
        storageState: 'test-auth/customer-auth.json',
      },
    },
    {
      name: 'Reseller Portal - Desktop',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
        storageState: 'test-auth/reseller-auth.json',
      },
    },
  ],

  // Visual comparison settings
  expect: {
    // Global visual comparison threshold
    toHaveScreenshot: {
      threshold: 0.2,
      maxDiffPixels: 1000,
    },
    toMatchSnapshot: {
      threshold: 0.2,
      maxDiffPixels: 1000,
    },
  },

  // Retry configuration for visual tests
  retries: process.env.CI ? 2 : 1,

  // Reporter configuration
  reporter: [
    [
      'html',
      {
        outputFolder: 'visual-test-results',
        open: process.env.CI ? 'never' : 'on-failure',
      },
    ],
    ['json', { outputFile: 'visual-test-results/results.json' }],
  ],

  // Output directories
  outputDir: 'visual-test-results/',

  // Global timeout
  timeout: 60 * 1000,
});
