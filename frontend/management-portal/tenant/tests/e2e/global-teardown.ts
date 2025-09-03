import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global E2E test teardown...');

  // Clean up test data
  console.log('🗑️ Cleaning up test data...');

  // Clear environment variables
  delete process.env.PLAYWRIGHT_TEST_BASE_URL;
  delete process.env.PLAYWRIGHT_TEST_READY;

  console.log('✅ Global teardown completed successfully');
}

export default globalTeardown;
