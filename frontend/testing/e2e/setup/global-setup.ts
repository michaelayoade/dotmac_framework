/**
 * DRY Global Playwright setup - shared authentication and environment setup
 */

import { chromium, Page, BrowserContext } from '@playwright/test';
import path from 'path';
import fs from 'fs';

async function globalSetup() {
  console.log('🚀 Starting DRY E2E test setup...');

  // Ensure storage directory exists
  const storageDir = path.resolve(__dirname, '../storage');
  if (!fs.existsSync(storageDir)) {
    fs.mkdirSync(storageDir, { recursive: true });
  }

  // Create browser instance
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // DRY authentication setup for all portals
    await setupAuthentication(page, storageDir);

    // DRY environment verification
    await verifyEnvironment(page);
  } finally {
    await context.close();
    await browser.close();
  }

  console.log('✅ DRY E2E test setup completed successfully');
}

/**
 * DRY authentication setup for different user types
 */
async function setupAuthentication(page: Page, storageDir: string): Promise<void> {
  const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

  // Admin authentication
  await page.goto(`${baseURL}/login`);

  // Use DRY login flow
  await page.fill('[data-testid="email-input"]', 'admin@dotmac.io');
  await page.fill('[data-testid="password-input"]', 'admin123');
  await page.click('[data-testid="login-button"]');

  // Wait for successful authentication
  await page.waitForURL(/dashboard/, { timeout: 10000 });

  // Save admin authentication state
  await page.context().storageState({
    path: path.join(storageDir, 'admin-auth.json'),
  });

  // Customer authentication (if needed)
  await page.goto(`${baseURL}/login`);
  await page.fill('[data-testid="email-input"]', 'customer@example.com');
  await page.fill('[data-testid="password-input"]', 'customer123');
  await page.click('[data-testid="login-button"]');

  await page.waitForURL(/dashboard/, { timeout: 10000 });

  // Save customer authentication state
  await page.context().storageState({
    path: path.join(storageDir, 'customer-auth.json'),
  });

  console.log('🔐 Authentication setup completed');
}

/**
 * DRY environment verification
 */
async function verifyEnvironment(page: Page): Promise<void> {
  const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

  // Verify health endpoint
  try {
    await page.goto(`${baseURL}/health`);
    const healthCheck = await page.textContent('body');

    if (!healthCheck.includes('healthy')) {
      throw new Error('Health check failed');
    }

    console.log('🏥 Health check passed');
  } catch (error) {
    console.warn('⚠️ Health check endpoint not available, continuing...');
  }

  // Verify API connectivity
  try {
    const response = await page.request.get(`${baseURL}/api/health`);
    if (response.ok()) {
      console.log('🔗 API connectivity verified');
    }
  } catch (error) {
    console.warn('⚠️ API health check failed, continuing...');
  }
}

export default globalSetup;
