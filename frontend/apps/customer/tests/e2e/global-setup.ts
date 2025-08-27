/**
 * Global Setup for E2E Tests
 * Initializes test environment and creates test data
 */

import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test environment setup...');
  
  // Start with a clean slate
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Wait for dev server to be ready
    await page.goto(config.webServer?.url || 'http://localhost:3001');
    
    // Verify app is loaded
    await page.waitForSelector('[data-testid="app-ready"]', { 
      timeout: 30000,
      state: 'attached' 
    }).catch(() => {
      // If no app-ready testid, just check for basic page elements
      return page.waitForSelector('body', { timeout: 10000 });
    });

    console.log('✅ Customer portal is ready for testing');

    // Optional: Set up test user account or mock API responses
    // This could involve calling setup APIs or seeding test data
    
  } catch (error) {
    console.error('❌ Failed to setup E2E test environment:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }

  console.log('🎯 E2E test environment setup complete');
}

export default globalSetup;