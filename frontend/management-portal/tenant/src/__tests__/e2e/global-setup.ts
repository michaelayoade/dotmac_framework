/**
 * Playwright Global Setup
 * Runs once before all E2E tests
 */

import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🎭 Setting up Playwright E2E environment...');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Wait for the application to be ready
    console.log('⏳ Waiting for application to be ready...');

    // Try to access the application with retries
    let retries = 0;
    const maxRetries = 30;

    while (retries < maxRetries) {
      try {
        const response = await page.goto('http://localhost:3003', {
          waitUntil: 'networkidle',
          timeout: 5000,
        });

        if (response?.ok()) {
          console.log('✅ Application is ready');
          break;
        }
      } catch (error) {
        retries++;
        if (retries >= maxRetries) {
          throw new Error(`Application failed to start after ${maxRetries} attempts`);
        }
        console.log(`⏳ Waiting for application... (attempt ${retries}/${maxRetries})`);
        await page.waitForTimeout(2000);
      }
    }

    // Set up test data if needed
    console.log('📝 Setting up test data...');

    // You can add code here to:
    // - Create test users
    // - Set up database with test data
    // - Configure external services
    // - Generate test files

    console.log('✅ Playwright E2E environment setup complete');
  } catch (error) {
    console.error('❌ Failed to set up E2E environment:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;
