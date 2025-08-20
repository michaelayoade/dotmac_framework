/**
 * Global setup for E2E tests
 * Following backend testing patterns
 */

import { chromium, type FullConfig } from '@playwright/test';

async function globalSetup(_config: FullConfig) {
  console.log('🚀 Setting up E2E test environment...');

  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Wait for the app to be ready
    console.log('⏳ Waiting for application to be ready...');
    await page.goto(process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000');

    // Wait for the app to load
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

    console.log('✅ Application is ready');

    // Setup test data if needed
    await setupTestData(page);

    console.log('✅ E2E test environment setup complete');
  } finally {
    await browser.close();
  }
}

async function setupTestData(page: unknown) {
  // Setup test users, customers, etc.
  console.log('📋 Setting up test data...');
  // Create test admin user
  await page.evaluate(() => {
    localStorage.setItem('test-admin-token', 'admin-test-token');
    localStorage.setItem(
      'test-admin-user',
      JSON.stringify({
        id: 'admin-test',
        name: 'Test Admin',
        email: 'admin@test.com',
        role: 'admin',
        tenant: 'test-tenant',
      })
    );
  });

  // Create test customer user
  await page.evaluate(() => {
    localStorage.setItem('test-customer-token', 'customer-test-token');
    localStorage.setItem(
      'test-customer-user',
      JSON.stringify({
        id: 'customer-test',
        name: 'Test Customer',
        email: 'customer@test.com',
        role: 'customer',
        tenant: 'test-tenant',
      })
    );
  });

  // Create test reseller user
  await page.evaluate(() => {
    localStorage.setItem('test-reseller-token', 'reseller-test-token');
    localStorage.setItem(
      'test-reseller-user',
      JSON.stringify({
        id: 'reseller-test',
        name: 'Test Reseller',
        email: 'reseller@test.com',
        role: 'reseller',
        tenant: 'test-tenant',
      })
    );
  });

  console.log('✅ Test data setup complete');
}

export default globalSetup;
