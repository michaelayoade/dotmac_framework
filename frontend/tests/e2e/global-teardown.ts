/**
 * Global teardown for E2E tests
 */

import type { FullConfig } from '@playwright/test';

async function globalTeardown(_config: FullConfig) {
  console.log('🧹 Cleaning up E2E test environment...');

  // Cleanup test data, close connections, etc.
  // This runs after all tests complete

  console.log('✅ E2E test cleanup complete');
}

export default globalTeardown;
