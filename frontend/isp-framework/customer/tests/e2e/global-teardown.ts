/**
 * Global Teardown for E2E Tests
 * Cleans up test environment and resources
 */

async function globalTeardown() {
  console.log('🧹 Starting E2E test environment cleanup...');

  try {
    // Clean up any test data, sessions, or resources
    // This could involve API calls to clean test databases

    console.log('✅ E2E test environment cleanup complete');
  } catch (error) {
    console.error('❌ Failed to cleanup E2E test environment:', error);
    // Don't throw error in teardown to avoid masking test failures
  }
}

export default globalTeardown;
